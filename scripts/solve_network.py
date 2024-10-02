# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
"""
Solves linear optimal power flow for a network iteratively while updating
reactances.

Relevant Settings
-----------------

.. code:: yaml

    solving:
        tmpdir:
        options:
            formulation:
            clip_p_max_pu:
            load_shedding:
            noisy_costs:
            nhours:
            min_iterations:
            max_iterations:
            skip_iterations:
            track_iterations:
        solver:
            name:

.. seealso::
    Documentation of the configuration file ``config.yaml`` at
    :ref:`electricity_cf`, :ref:`solving_cf`, :ref:`plotting_cf`

Inputs
------

- ``networks/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}.nc``: confer :ref:`prepare`

Outputs
-------

- ``results/networks/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}.nc``: Solved PyPSA network including optimisation results

    .. image:: /img/results.png
        :width: 40 %

Description
-----------

Total annual system costs are minimised with PyPSA. The full formulation of the
linear optimal power flow (plus investment planning)
is provided in the
`documentation of PyPSA <https://pypsa.readthedocs.io/en/latest/optimal_power_flow.html#linear-optimal-power-flow>`_.
The optimisation is based on the :func:`network.optimize` function.
Additionally, some extra constraints specified in :mod:`prepare_network` and :mod:`solve_network` are added.

Solving the network in multiple iterations is motivated through the dependence of transmission line capacities and impedances on values of corresponding flows.
As lines are expanded their electrical parameters change, which renders the optimisation bilinear even if the power flow
equations are linearized.
To retain the computational advantage of continuous linear programming, a sequential linear programming technique
is used, where in between iterations the line impedances are updated.
Details (and errors made through this heuristic) are discussed in the paper

- Fabian Neumann and Tom Brown. `Heuristics for Transmission Expansion Planning in Low-Carbon Energy System Models <https://arxiv.org/abs/1907.10548>`_), *16th International Conference on the European Energy Market*, 2019. `arXiv:1907.10548 <https://arxiv.org/abs/1907.10548>`_.

.. warning::
    Capital costs of existing network components are not included in the objective function,
    since for the optimisation problem they are just a constant term (no influence on optimal result).

    Therefore, these capital costs are not included in ``network.objective``!

    If you want to calculate the full total annual system costs add these to the objective value.

.. tip::
    The rule :mod:`solve_all_networks` runs
    for all ``scenario`` s in the configuration file
    the rule :mod:`solve_network`.
"""
import logging
import re

import numpy as np
import pandas as pd
import pypsa
import xarray as xr
from _helpers import (
    build_directory,
    configure_logging,
    create_logger,
    mock_snakemake,
    override_component_attrs,
)
from linopy import merge
from pypsa.descriptors import get_switchable_as_dense as get_as_dense
from pypsa.optimization.compat import define_constraints, get_var, join_exprs, linexpr
from vresutils.benchmark import memory_logger

logger = create_logger(__name__)
pypsa.pf.logger.setLevel(logging.WARNING)


def prepare_network(n, solve_opts):
    if "clip_p_max_pu" in solve_opts:
        for df in (
            n.generators_t.p_max_pu,
            n.generators_t.p_min_pu,
            n.storage_units_t.inflow,
        ):
            df.where(df > solve_opts["clip_p_max_pu"], other=0.0, inplace=True)

    if "lv_limit" in n.global_constraints.index:
        n.line_volume_limit = n.global_constraints.at["lv_limit", "constant"]
        n.line_volume_limit_dual = n.global_constraints.at["lv_limit", "mu"]

    if solve_opts.get("load_shedding"):
        n.add("Carrier", "Load")
        n.madd(
            "Generator",
            n.buses.index,
            " load",
            bus=n.buses.index,
            carrier="load",
            sign=1e-3,  # Adjust sign to measure p and p_nom in kW instead of MW
            marginal_cost=1e2,  # Eur/kWh
            # intersect between macroeconomic and surveybased
            # willingness to pay
            # http://journal.frontiersin.org/article/10.3389/fenrg.2015.00055/full
            p_nom=1e9,  # kW
        )

    if solve_opts.get("noisy_costs"):
        for t in n.iterate_components():
            # if 'capital_cost' in t.df:
            #    t.df['capital_cost'] += 1e1 + 2.*(np.random.random(len(t.df)) - 0.5)
            if "marginal_cost" in t.df:
                np.random.seed(174)
                t.df["marginal_cost"] += 1e-2 + 2e-3 * (
                    np.random.random(len(t.df)) - 0.5
                )

        for t in n.iterate_components(["Line", "Link"]):
            np.random.seed(123)
            t.df["capital_cost"] += (
                1e-1 + 2e-2 * (np.random.random(len(t.df)) - 0.5)
            ) * t.df["length"]

    if solve_opts.get("nhours"):
        nhours = solve_opts["nhours"]
        n.set_snapshots(n.snapshots[:nhours])
        n.snapshot_weightings[:] = 8760.0 / nhours

    if snakemake.config["foresight"] == "myopic":
        add_land_use_constraint(n)

    return n


def add_ccl_constraints(n, config):
    """
    Add CCL (country & carrier limit) constraint to the network. Add minimum
    and maximum levels of generator nominal capacity per carrier for individual
    countries. Opts and path for agg_p_nom_minmax.csv must be defined in
    config.yaml. Default file is available at data/agg_p_nom_minmax.csv.

    Parameters
    ----------
    n : pypsa.Network
    config : dict
    Example
    -------
    scenario:
        opts: [Co2L-CCL-24H]
    electricity:
        agg_p_nom_limits: data/agg_p_nom_minmax.csv
    """
    agg_p_nom_limits = config["electricity"].get("agg_p_nom_limits")

    try:
        agg_p_nom_minmax = pd.read_csv(agg_p_nom_limits, index_col=list(range(2)))
    except IOError:
        logger.exception(
            "Need to specify the path to a .csv file containing "
            "aggregate capacity limits per country in "
            "config['electricity']['agg_p_nom_limit']."
        )
    logger.info(
        "Adding per carrier generation capacity constraints for " "individual countries"
    )

    gen_country = n.generators.bus.map(n.buses.country)
    capacity_variable = n.model["Generator-p_nom"]

    lhs = []
    ext_carriers = n.generators.query("p_nom_extendable").carrier.unique()
    for c in ext_carriers:
        ext_carrier = n.generators.query("p_nom_extendable and carrier == @c")
        country_grouper = (
            ext_carrier.bus.map(n.buses.country)
            .rename_axis("Generator-ext")
            .rename("country")
        )
        ext_carrier_per_country = capacity_variable.loc[
            country_grouper.index
        ].groupby_sum(country_grouper)
        lhs.append(ext_carrier_per_country)
    lhs = merge(lhs, dim=pd.Index(ext_carriers, name="carrier"))

    min_matrix = agg_p_nom_minmax["min"].to_xarray().unstack().reindex_like(lhs)
    max_matrix = agg_p_nom_minmax["max"].to_xarray().unstack().reindex_like(lhs)

    n.model.add_constraints(
        lhs >= min_matrix, name="agg_p_nom_min", mask=min_matrix.notnull()
    )
    n.model.add_constraints(
        lhs <= max_matrix, name="agg_p_nom_max", mask=max_matrix.notnull()
    )


def add_eq_constraints(n, o, scaling=1e-1):
    """
    Add equity constraints to the network.

    Currently, this is only implemented for the electricity sector only.

    Opts must be specified in the config.yaml.

    Parameters
    ----------
    n : pypsa.Network
    o : str

    Example
    -------
    scenario:
        opts: [Co2L-EQ0.7-24h]

    Require each country or node to on average produce a minimal share
    of its total electricity consumption itself. Example: EQ0.7c demands each country
    to produce on average at least 70% of its consumption; EQ0.7 demands
    each node to produce on average at least 70% of its consumption.
    """
    float_regex = "[0-9]*\.?[0-9]+"
    level = float(re.findall(float_regex, o)[0])
    if o[-1] == "c":
        ggrouper = n.generators.bus.map(n.buses.country)
        lgrouper = n.loads.bus.map(n.buses.country)
        sgrouper = n.storage_units.bus.map(n.buses.country)
    else:
        ggrouper = n.generators.bus
        lgrouper = n.loads.bus
        sgrouper = n.storage_units.bus
    load = (
        n.snapshot_weightings.generators
        @ n.loads_t.p_set.groupby(lgrouper, axis=1).sum()
    )
    inflow = (
        n.snapshot_weightings.stores
        @ n.storage_units_t.inflow.groupby(sgrouper, axis=1).sum()
    )
    inflow = inflow.reindex(load.index).fillna(0.0)
    rhs = scaling * (level * load - inflow)
    dispatch_variable = n.model["Generator-p"]
    lhs_gen = (
        (dispatch_variable * (n.snapshot_weightings.generators * scaling))
        .groupby(ggrouper.to_xarray())
        .sum()
        .sum("snapshot")
    )
    # TODO: double check that this is really needed, why do have to subtract the spillage
    if not n.storage_units_t.inflow.empty:
        spillage_variable = n.model["StorageUnit-spill"]
        lhs_spill = (
            (spillage_variable * (-n.snapshot_weightings.stores * scaling))
            .groupby_sum(sgrouper)
            .groupby(sgrouper.to_xarray())
            .sum()
            .sum("snapshot")
        )
        lhs = lhs_gen + lhs_spill
    else:
        lhs = lhs_gen
    n.model.add_constraints(lhs >= rhs, name="equity_min")


def add_bau_constraints(n, config):
    """
    Add a per-carrier minimal overall capacity. BAU_mincapacities and opts must
    be adjusted in the config.yaml.

    Parameters
    ----------
    n : pypsa.Network
    config : dict
    Example
    -------
    scenario:
        opts: [Co2L-BAU-24h]
    electricity:
        BAU_mincapacities:
            solar: 0
            onwind: 0
            OCGT: 100000
            offwind-ac: 0
            offwind-dc: 0
    Which sets minimum expansion across all nodes e.g. in Europe to 100GW.
    OCGT bus 1 + OCGT bus 2 + ... > 100000
    """
    mincaps = pd.Series(config["electricity"]["BAU_mincapacities"])
    p_nom = n.model["Generator-p_nom"]
    ext_i = n.generators.query("p_nom_extendable")
    ext_carrier_i = xr.DataArray(ext_i.carrier.rename_axis("Generator-ext"))
    lhs = p_nom.groupby(ext_carrier_i).sum()
    rhs = mincaps[lhs.indexes["carrier"]].rename_axis("carrier")
    n.model.add_constraints(lhs >= rhs, name="bau_mincaps")


def add_safe_constraints(n, config):
    """
    Add a capacity reserve margin of a certain fraction above the peak demand.
    Renewable generators and storage do not contribute. Ignores network.

    Parameters
    ----------
        n : pypsa.Network
        config : dict

    Example
    -------
    config.yaml requires to specify opts:

    scenario:
        opts: [Co2L-SAFE-24h]
    electricity:
        SAFE_reservemargin: 0.1
    Which sets a reserve margin of 10% above the peak demand.
    """
    peakdemand = n.loads_t.p_set.sum(axis=1).max()
    margin = 1.0 + config["electricity"]["SAFE_reservemargin"]
    reserve_margin = peakdemand * margin
    conventional_carriers = config["electricity"]["conventional_carriers"]
    ext_gens_i = n.generators.query(
        "carrier in @conventional_carriers & p_nom_extendable"
    ).index
    p_nom = n.model["Generator-p_nom"].loc[ext_gens_i]
    lhs = p_nom.sum()
    exist_conv_caps = n.generators.query(
        "~p_nom_extendable & carrier in @conventional_carriers"
    ).p_nom.sum()
    rhs = reserve_margin - exist_conv_caps
    n.model.add_constraints(lhs >= rhs, name="safe_mintotalcap")


def add_operational_reserve_margin_constraint(n, sns, config):
    """
    Build reserve margin constraints based on the formulation
    as suggested in GenX
    https://energy.mit.edu/wp-content/uploads/2017/10/Enhanced-Decision-Support-for-a-Changing-Electricity-Landscape.pdf
    It implies that the reserve margin also accounts for optimal
    dispatch of distributed energy resources (DERs) and demand response
    which is a novel feature of GenX.
    """
    reserve_config = config["electricity"]["operational_reserve"]
    EPSILON_LOAD = reserve_config["epsilon_load"]
    EPSILON_VRES = reserve_config["epsilon_vres"]
    CONTINGENCY = reserve_config["contingency"]

    # Reserve Variables
    n.model.add_variables(
        0, np.inf, coords=[sns, n.generators.index], name="Generator-r"
    )
    reserve = n.model["Generator-r"]
    lhs = reserve.sum("Generator")

    # Share of extendable renewable capacities
    ext_i = n.generators.query("p_nom_extendable").index
    vres_i = n.generators_t.p_max_pu.columns
    if not ext_i.empty and not vres_i.empty:
        capacity_factor = n.generators_t.p_max_pu[vres_i.intersection(ext_i)]
        renewable_capacity_variables = (
            n.model["Generator-p_nom"]
            .loc[vres_i.intersection(ext_i)]
            .rename({"Generator-ext": "Generator"})
        )
        lhs = merge(
            lhs,
            (renewable_capacity_variables * (-EPSILON_VRES * capacity_factor)).sum(
                ["Generator"]
            ),
        )

    # Total demand per t
    demand = get_as_dense(n, "Load", "p_set").sum(axis=1)

    # VRES potential of non-extendable generators
    capacity_factor = n.generators_t.p_max_pu[vres_i.difference(ext_i)]
    renewable_capacity = n.generators.p_nom[vres_i.difference(ext_i)]
    potential = (capacity_factor * renewable_capacity).sum(axis=1)

    # Right-hand-side
    rhs = EPSILON_LOAD * demand + EPSILON_VRES * potential + CONTINGENCY

    n.model.add_constraints(lhs >= rhs, name="reserve_margin")


def update_capacity_constraint(n):
    gen_i = n.generators.index
    ext_i = n.generators.query("p_nom_extendable").index
    fix_i = n.generators.query("not p_nom_extendable").index

    dispatch = n.model["Generator-p"]
    reserve = n.model["Generator-r"]

    capacity_fixed = n.generators.p_nom[fix_i]

    p_max_pu = get_as_dense(n, "Generator", "p_max_pu")

    lhs = merge(
        dispatch * 1,
        reserve * 1,
    )

    if not ext_i.empty:
        capacity_variable = n.model["Generator-p_nom"]
        lhs = dispatch + reserve - capacity_variable * xr.DataArray(p_max_pu[ext_i])

    rhs = (p_max_pu[fix_i] * capacity_fixed).reindex(columns=gen_i, fill_value=0)
    n.model.add_constraints(
        lhs <= rhs, name="gen_updated_capacity_constraint", mask=rhs.notnull()
    )


def add_operational_reserve_margin(n, sns, config):
    """
        Build reserve margin constraints based on the formulation given in
        https://genxproject.github.io/GenX/dev/core/#Reserves.
    Parameters
        ----------
            n : pypsa.Network
            sns: pd.DatetimeIndex
            config : dict
        Example:
        --------
        config.yaml requires to specify operational_reserve:
        operational_reserve: # like https://genxproject.github.io/GenX/dev/core/#Reserves
            activate: true
            epsilon_load: 0.02 # percentage of load at each snapshot
            epsilon_vres: 0.02 # percentage of VRES at each snapshot
            contingency: 400000 # MW
    """
    add_operational_reserve_margin_constraint(n, sns, config)
    update_capacity_constraint(n)


def add_battery_constraints(n):
    """
    Add constraint ensuring that charger = discharger, i.e.
    1 * charger_size - efficiency * discharger_size = 0
    """
    nodes = n.buses.index[n.buses.carrier == "battery"]
    # if nodes.empty or ("Link", "p_nom") not in n.variables.index:
    if nodes.empty:
        return
    vars_link = n.model["Link-p_nom"]
    eff = n.links.loc[nodes + " discharger", "efficiency"]
    lhs = merge(
        vars_link.sel({"Link-ext": nodes + " charger"}) * 1,
        # for some reason, eff is one element longer as compared with vars_link
        vars_link.sel({"Link-ext": nodes + " discharger"}) * -eff[0],
    )
    n.model.add_constraints(lhs == 0, name="link_charger_ratio")


def add_res_constraints(n, res_share):
    lgrouper = n.loads.bus.map(n.buses.country)

    logger.warning(
        "The add_RES_constraints() is still work in progress. "
        "Unexpected results might be incurred, particularly if "
        "temporal clustering is applied or if an unexpected change of technologies "
        "is subject to the optimisation."
    )

    load = (
        n.snapshot_weightings.generators
        @ n.loads_t.p_set.groupby(lgrouper, axis=1).sum()
    )

    rhs = res_share * load

    gens_i = n.generators.query("carrier in @res_techs").index
    stores_i = n.storage_units.query("carrier in @res_techs").index
    charger_i = n.links.query("carrier in @charger").index
    discharger_i = n.links.query("carrier in @discharger").index

    stores_t_weights = n.snapshot_weightings.stores

    # Generators
    lhs_gen = (
        n.model["Generator-p"].loc[:, gens_i] * n.snapshot_weightings.generators
    ).sum()

    # StorageUnits
    store_disp_expr = (
        n.model["StorageUnit-p_dispatch"].loc[:, stores_i] * stores_t_weights
    )
    store_expr = n.model["StorageUnit-p_store"].loc[:, stores_i] * stores_t_weights
    charge_expr = n.model["Link-p"].loc[:, charger_i] * stores_t_weights.apply(
        lambda r: r * n.links.loc[charger_i].efficiency
    )
    discharge_expr = n.model["Link-p"].loc[:, discharger_i] * stores_t_weights.apply(
        lambda r: r * n.links.loc[discharger_i].efficiency
    )

    lhs_dispatch = store_disp_expr.sum()

    lhs_store = store_expr.sum()

    # Stores (or their resp. Link components)
    # Note that the variables "p0" and "p1" currently do not exist.
    # Thus, p0 and p1 must be derived from "p" (which exists), taking into account the link efficiency.
    lhs_charge = charge_expr.sum()

    lhs_discharge = discharge_expr.sum()

    lhs = lhs_gen + lhs_dispatch - lhs_store - lhs_charge + lhs_discharge
    n.model.add_constraints(lhs == rhs, name="res_share")


def add_land_use_constraint(n):
    if "m" in snakemake.wildcards.clusters:
        _add_land_use_constraint_m(n)
    else:
        _add_land_use_constraint(n)


def _add_land_use_constraint(n):
    # warning: this will miss existing offwind which is not classed AC-DC and has carrier 'offwind'

    for carrier in ["solar", "onwind", "offwind-ac", "offwind-dc"]:
        existing = (
            n.generators.loc[n.generators.carrier == carrier, "p_nom"]
            .groupby(n.generators.bus.map(n.buses.location))
            .sum()
        )
        existing.index += " " + carrier + "-" + snakemake.wildcards.planning_horizons
        n.generators.loc[existing.index, "p_nom_max"] -= existing

    n.generators.p_nom_max.clip(lower=0, inplace=True)


def _add_land_use_constraint_m(n):
    # if generators clustering is lower than network clustering, land_use accounting is at generators clusters

    planning_horizons = snakemake.config["scenario"]["planning_horizons"]
    grouping_years = snakemake.config["existing_capacities"]["grouping_years"]
    current_horizon = snakemake.wildcards.planning_horizons

    for carrier in ["solar", "onwind", "offwind-ac", "offwind-dc"]:
        existing = n.generators.loc[n.generators.carrier == carrier, "p_nom"]
        ind = list(
            set(
                [
                    i.split(sep=" ")[0] + " " + i.split(sep=" ")[1]
                    for i in existing.index
                ]
            )
        )

        previous_years = [
            str(y)
            for y in planning_horizons + grouping_years
            if y < int(snakemake.wildcards.planning_horizons)
        ]

        for p_year in previous_years:
            ind2 = [
                i for i in ind if i + " " + carrier + "-" + p_year in existing.index
            ]
            sel_current = [i + " " + carrier + "-" + current_horizon for i in ind2]
            sel_p_year = [i + " " + carrier + "-" + p_year for i in ind2]
            n.generators.loc[sel_current, "p_nom_max"] -= existing.loc[
                sel_p_year
            ].rename(lambda x: x[:-4] + current_horizon)

    n.generators.p_nom_max.clip(lower=0, inplace=True)


def add_h2_network_cap(n, cap):
    h2_network = n.links.loc[n.links.carrier == "H2 pipeline"]
    if h2_network.index.empty or ("Link", "p_nom") not in n.variables.index:
        return
    h2_network_cap = get_var(n, "Link", "p_nom")
    subset_index = h2_network.index.intersection(h2_network_cap.index)
    lhs = linexpr(
        (h2_network.loc[subset_index, "length"], h2_network_cap[subset_index])
    ).sum()
    # lhs = linexpr((1, h2_network_cap[h2_network.index])).sum()
    rhs = cap * 1000
    define_constraints(n, lhs, "<=", rhs, "h2_network_cap")


def h2_export_yearly_constraint(n):
    res = [
        "csp",
        "rooftop-solar",
        "solar",
        "onwind",
        "onwind2",
        "offwind",
        "offwind2",
        "ror",
    ]
    res_index = n.generators.loc[n.generators.carrier.isin(res)].index

    weightings = pd.DataFrame(
        np.outer(n.snapshot_weightings["generators"], [1.0] * len(res_index)),
        index=n.snapshots,
        columns=res_index,
    )
    res = join_exprs(
        linexpr((weightings, get_var(n, "Generator", "p")[res_index]))
    )  # single line sum

    load_ind = n.loads[n.loads.carrier == "AC"].index.intersection(
        n.loads_t.p_set.columns
    )

    load = (
        n.loads_t.p_set[load_ind].sum(axis=1) * n.snapshot_weightings["generators"]
    ).sum()

    h2_export = n.loads.loc["H2 export load"].p_set * 8760

    lhs = res

    include_country_load = snakemake.config["policy_config"]["yearly"][
        "re_country_load"
    ]

    if include_country_load:
        elec_efficiency = (
            n.links.filter(like="Electrolysis", axis=0).loc[:, "efficiency"].mean()
        )
        rhs = (
            h2_export * (1 / elec_efficiency) + load
        )  # 0.7 is approximation of electrloyzer efficiency # TODO obtain value from network
    else:
        rhs = h2_export * (1 / 0.7)

    con = define_constraints(n, lhs, ">=", rhs, "H2ExportConstraint", "RESproduction")


def monthly_constraints(n, n_ref):
    res_techs = [
        "csp",
        "rooftop-solar",
        "solar",
        "onwind",
        "onwind2",
        "offwind",
        "offwind2",
        "ror",
    ]
    allowed_excess = snakemake.config["policy_config"]["hydrogen"]["allowed_excess"]

    res_index = n.generators.loc[n.generators.carrier.isin(res_techs)].index

    weightings = pd.DataFrame(
        np.outer(n.snapshot_weightings["generators"], [1.0] * len(res_index)),
        index=n.snapshots,
        columns=res_index,
    )

    res = linexpr((weightings, get_var(n, "Generator", "p")[res_index])).sum(
        axis=1
    )  # single line sum
    res = res.groupby(res.index.month).sum()

    electrolysis = get_var(n, "Link", "p")[
        n.links.index[n.links.index.str.contains("H2 Electrolysis")]
    ]
    weightings_electrolysis = pd.DataFrame(
        np.outer(
            n.snapshot_weightings["generators"], [1.0] * len(electrolysis.columns)
        ),
        index=n.snapshots,
        columns=electrolysis.columns,
    )

    elec_input = linexpr((-allowed_excess * weightings_electrolysis, electrolysis)).sum(
        axis=1
    )

    elec_input = elec_input.groupby(elec_input.index.month).sum()

    if snakemake.config["policy_config"]["hydrogen"]["additionality"]:
        res_ref = n_ref.generators_t.p[res_index] * weightings
        res_ref = res_ref.groupby(n_ref.generators_t.p.index.month).sum().sum(axis=1)

        elec_input_ref = (
            n_ref.links_t.p0.loc[
                :, n_ref.links_t.p0.columns.str.contains("H2 Electrolysis")
            ]
            * weightings_electrolysis
        )
        elec_input_ref = (
            -elec_input_ref.groupby(elec_input_ref.index.month).sum().sum(axis=1)
        )

        for i in range(len(res.index)):
            lhs = res.iloc[i] + "\n" + elec_input.iloc[i]
            rhs = res_ref.iloc[i] + elec_input_ref.iloc[i]
            con = define_constraints(
                n, lhs, ">=", rhs, f"RESconstraints_{i}", f"REStarget_{i}"
            )

    else:
        for i in range(len(res.index)):
            lhs = res.iloc[i] + "\n" + elec_input.iloc[i]

            con = define_constraints(
                n, lhs, ">=", 0.0, f"RESconstraints_{i}", f"REStarget_{i}"
            )
    # else:
    #     logger.info("ignoring H2 export constraint as wildcard is set to 0")


def add_chp_constraints(n):
    electric_bool = (
        n.links.index.str.contains("urban central")
        & n.links.index.str.contains("CHP")
        & n.links.index.str.contains("electric")
    )
    heat_bool = (
        n.links.index.str.contains("urban central")
        & n.links.index.str.contains("CHP")
        & n.links.index.str.contains("heat")
    )

    electric = n.links.index[electric_bool]
    heat = n.links.index[heat_bool]

    electric_ext = n.links.index[electric_bool & n.links.p_nom_extendable]
    heat_ext = n.links.index[heat_bool & n.links.p_nom_extendable]

    electric_fix = n.links.index[electric_bool & ~n.links.p_nom_extendable]
    heat_fix = n.links.index[heat_bool & ~n.links.p_nom_extendable]

    link_p = get_var(n, "Link", "p")

    if not electric_ext.empty:
        link_p_nom = get_var(n, "Link", "p_nom")

        # ratio of output heat to electricity set by p_nom_ratio
        lhs = linexpr(
            (
                n.links.loc[electric_ext, "efficiency"]
                * n.links.loc[electric_ext, "p_nom_ratio"],
                link_p_nom[electric_ext],
            ),
            (-n.links.loc[heat_ext, "efficiency"].values, link_p_nom[heat_ext].values),
        )

        define_constraints(n, lhs, "=", 0, "chplink", "fix_p_nom_ratio")

        # top_iso_fuel_line for extendable
        lhs = linexpr(
            (1, link_p[heat_ext]),
            (1, link_p[electric_ext].values),
            (-1, link_p_nom[electric_ext].values),
        )

        define_constraints(n, lhs, "<=", 0, "chplink", "top_iso_fuel_line_ext")

    if not electric_fix.empty:
        # top_iso_fuel_line for fixed
        lhs = linexpr((1, link_p[heat_fix]), (1, link_p[electric_fix].values))

        rhs = n.links.loc[electric_fix, "p_nom"].values

        define_constraints(n, lhs, "<=", rhs, "chplink", "top_iso_fuel_line_fix")

    if not electric.empty:
        # backpressure
        lhs = linexpr(
            (
                n.links.loc[electric, "c_b"].values * n.links.loc[heat, "efficiency"],
                link_p[heat],
            ),
            (-n.links.loc[electric, "efficiency"].values, link_p[electric].values),
        )

        define_constraints(n, lhs, "<=", 0, "chplink", "backpressure")


def add_co2_sequestration_limit(n, sns):
    co2_stores = n.stores.loc[n.stores.carrier == "co2 stored"].index

    if co2_stores.empty or ("Store", "e") not in n.variables.index:
        return

    vars_final_co2_stored = get_var(n, "Store", "e").loc[sns[-1], co2_stores]

    lhs = linexpr((1, vars_final_co2_stored)).sum()
    rhs = (
        n.config["sector"].get("co2_sequestration_potential", 5) * 1e6
    )  # TODO change 200 limit (Europe)

    name = "co2_sequestration_limit"
    define_constraints(
        n, lhs, "<=", rhs, "GlobalConstraint", "mu", axes=pd.Index([name]), spec=name
    )


def set_h2_colors(n):
    blue_h2 = get_var(n, "Link", "p")[
        n.links.index[n.links.index.str.contains("blue H2")]
    ]

    pink_h2 = get_var(n, "Link", "p")[
        n.links.index[n.links.index.str.contains("pink H2")]
    ]

    fuelcell_ind = n.loads[n.loads.carrier == "land transport fuel cell"].index

    other_ind = n.loads[
        (n.loads.carrier == "H2 for industry")
        | (n.loads.carrier == "H2 for shipping")
        | (n.loads.carrier == "H2")
    ].index

    load_fuelcell = (
        n.loads_t.p_set[fuelcell_ind].sum(axis=1) * n.snapshot_weightings["generators"]
    ).sum()

    load_other_h2 = n.loads.loc[other_ind].p_set.sum() * 8760

    load_h2 = load_fuelcell + load_other_h2

    weightings_blue = pd.DataFrame(
        np.outer(n.snapshot_weightings["generators"], [1.0] * len(blue_h2.columns)),
        index=n.snapshots,
        columns=blue_h2.columns,
    )

    weightings_pink = pd.DataFrame(
        np.outer(n.snapshot_weightings["generators"], [1.0] * len(pink_h2.columns)),
        index=n.snapshots,
        columns=pink_h2.columns,
    )

    total_blue = linexpr((weightings_blue, blue_h2)).sum().sum()

    total_pink = linexpr((weightings_pink, pink_h2)).sum().sum()

    rhs_blue = load_h2 * snakemake.config["sector"]["hydrogen"]["blue_share"]
    rhs_pink = load_h2 * snakemake.config["sector"]["hydrogen"]["pink_share"]

    define_constraints(n, total_blue, "=", rhs_blue, "blue_h2_share")

    define_constraints(n, total_pink, "=", rhs_pink, "pink_h2_share")


def add_existing(n):
    if snakemake.wildcards["planning_horizons"] == "2050":
        directory = (
            "results/"
            + "Existing_capacities/"
            + snakemake.config["run"].replace("2050", "2030")
        )
        n_name = (
            snakemake.input.network.split("/")[-1]
            .replace(str(snakemake.config["scenario"]["clusters"][0]), "")
            .replace(str(snakemake.config["costs"]["discountrate"][0]), "")
            .replace("_presec", "")
            .replace(".nc", ".csv")
        )
        df = pd.read_csv(directory + "/electrolyzer_caps_" + n_name, index_col=0)
        existing_electrolyzers = df.p_nom_opt.values

        h2_index = n.links[n.links.carrier == "H2 Electrolysis"].index
        n.links.loc[h2_index, "p_nom_min"] = existing_electrolyzers
        df = pd.read_csv(directory + "/res_caps_" + n_name, index_col=0)

        for tech in snakemake.config["custom_data"]["renewables"]:
            # df = pd.read_csv(snakemake.config["custom_data"]["existing_renewables"], index_col=0)
            existing_res = df.loc[tech]
            existing_res.index = existing_res.index.str.apply(lambda x: x + tech)
            tech_index = n.generators[n.generators.carrier == tech].index
            n.generators.loc[tech_index, tech] = existing_res


def extra_functionality(n, snapshots):
    """
    Collects supplementary constraints which will be passed to
    ``pypsa.optimization.optimize``.

    If you want to enforce additional custom constraints, this is a good location to add them.
    The arguments ``opts`` and ``snakemake.config`` are expected to be attached to the network.
    """
    opts = n.opts
    config = n.config
    if "BAU" in opts and n.generators.p_nom_extendable.any():
        add_bau_constraints(n, config)
    if "SAFE" in opts and n.generators.p_nom_extendable.any():
        add_safe_constraints(n, config)
    if "CCL" in opts and n.generators.p_nom_extendable.any():
        add_ccl_constraints(n, config)
    reserve = config["electricity"].get("operational_reserve", {})
    if reserve.get("activate"):
        add_operational_reserve_margin(n, snapshots, config)
    for o in opts:
        if "RES" in o:
            res_share = float(re.findall("[0-9]*\.?[0-9]+$", o)[0])
            add_res_constraints(n, res_share)
    for o in opts:
        if "EQ" in o:
            add_eq_constraints(n, o)
    add_battery_constraints(n)

    if (
        snakemake.config["policy_config"]["hydrogen"]["temporal_matching"]
        == "h2_yearly_matching"
    ):
        if snakemake.config["policy_config"]["hydrogen"]["additionality"] == True:
            logger.info(
                "additionality is currently not supported for yearly constraints, proceeding without additionality"
            )
        logger.info("setting h2 export to yearly greenness constraint")
        h2_export_yearly_constraint(n)

    elif (
        snakemake.config["policy_config"]["hydrogen"]["temporal_matching"]
        == "h2_monthly_matching"
    ):
        if not snakemake.config["policy_config"]["hydrogen"]["is_reference"]:
            logger.info("setting h2 export to monthly greenness constraint")
            monthly_constraints(n, n_ref)
        else:
            logger.info("preparing reference case for additionality constraint")

    elif (
        snakemake.config["policy_config"]["hydrogen"]["temporal_matching"]
        == "no_res_matching"
    ):
        logger.info("no h2 export constraint set")

    else:
        raise ValueError(
            'H2 export constraint is invalid, check config["policy_config"]'
        )

    if snakemake.config["sector"]["hydrogen"]["network"]:
        if snakemake.config["sector"]["hydrogen"]["network_limit"]:
            add_h2_network_cap(
                n, snakemake.config["sector"]["hydrogen"]["network_limit"]
            )

    if snakemake.config["sector"]["hydrogen"]["set_color_shares"]:
        logger.info("setting H2 color mix")
        set_h2_colors(n)

    add_co2_sequestration_limit(n, snapshots)


def solve_network(n, config, solving={}, **kwargs):
    set_of_options = solving["solver"]["options"]
    cf_solving = solving["options"]

    kwargs["solver_options"] = (
        solving["solver_options"][set_of_options] if set_of_options else {}
    )
    kwargs["solver_name"] = solving["solver"]["name"]
    kwargs["extra_functionality"] = extra_functionality
    skip_iterations = cf_solving.get("skip_iterations", False)
    if not n.lines.s_nom_extendable.any():
        skip_iterations = True
        logger.info("No expandable lines found. Skipping iterative solving.")

    # add to network for extra_functionality
    n.config = config

    if skip_iterations:
        status, condition = n.optimize(**kwargs)
    else:
        kwargs["track_iterations"] = (cf_solving.get("track_iterations", False),)
        kwargs["min_iterations"] = (cf_solving.get("min_iterations", 4),)
        kwargs["max_iterations"] = (cf_solving.get("max_iterations", 6),)
        status, condition = n.optimize.optimize_transmission_expansion_iteratively(
            **kwargs
        )

    if status != "ok":  # and not rolling_horizon:
        logger.warning(
            f"Solving status '{status}' with termination condition '{condition}'"
        )
    if "infeasible" in condition:
        labels = n.model.compute_infeasibilities()
        logger.info(f"Labels:\n{labels}")
        n.model.print_infeasibilities()
        raise RuntimeError("Solving status 'infeasible'")

    return n


if __name__ == "__main__":
    if "snakemake" not in globals():
        snakemake = mock_snakemake(
            "solve_network",
            simpl="",
            clusters="54",
            ll="copt",
            opts="Co2L-1H",
        )

    configure_logging(snakemake)

    tmpdir = snakemake.params.solving.get("tmpdir")
    if tmpdir is not None:
        build_directory(tmpdir, just_parent_directory=False)
    opts = snakemake.wildcards.opts.split("-")
    solving = snakemake.params.solving

    is_sector_coupled = "sopts" in snakemake.wildcards.keys()

    if is_sector_coupled:
        overrides = override_component_attrs(snakemake.input.overrides)
        n = pypsa.Network(snakemake.input.network, override_component_attrs=overrides)
    else:
        n = pypsa.Network(snakemake.input.network)

    if snakemake.params.augmented_line_connection.get("add_to_snakefile"):
        n.lines.loc[n.lines.index.str.contains("new"), "s_nom_min"] = (
            snakemake.params.augmented_line_connection.get("min_expansion")
        )

    if (
        snakemake.config["custom_data"]["add_existing"]
        and snakemake.wildcards.planning_horizons == "2050"
        and is_sector_coupled
    ):
        add_existing(n)

    if (
        snakemake.config["policy_config"]["hydrogen"]["additionality"]
        and not snakemake.config["policy_config"]["hydrogen"]["is_reference"]
        and snakemake.config["policy_config"]["hydrogen"]["temporal_matching"]
        != "no_res_matching"
        and is_sector_coupled
    ):
        n_ref_path = snakemake.config["policy_config"]["hydrogen"]["path_to_ref"]
        n_ref = pypsa.Network(n_ref_path)
    else:
        n_ref = None

    n = prepare_network(n, solving["options"])

    with memory_logger(
        filename=getattr(snakemake.log, "memory", None), interval=30.0
    ) as mem:
        n = solve_network(
            n,
            config=snakemake.config,
            solving=solving,
            solver_dir=tmpdir,
            solver_logfile=snakemake.log.solver,
        )
    logger.info(f"Maximum memory usage: {mem.mem_usage}")
    n.meta = dict(snakemake.config, **dict(wildcards=dict(snakemake.wildcards)))
    n.export_to_netcdf(snakemake.output[0])
    logger.info(f"Objective function: {n.objective}")
    logger.info(f"Objective constant: {n.objective_constant}")
