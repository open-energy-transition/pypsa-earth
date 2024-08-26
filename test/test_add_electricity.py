# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-

import pathlib
import sys

import pandas as pd
import xarray as xr

sys.path.append("./scripts")

from test.conftest import (
    get_config_dict,
    get_power_network_scigrid_de,
    get_power_plants,
)

from add_electricity import (
    _add_missing_carriers_from_costs,
    attach_hydro,
    calculate_annuity,
    load_costs,
    load_powerplants,
)

path_cwd = pathlib.Path.cwd()


def test_calculate_annuity():

    # test for r being a pandas Series
    n_series = pd.Series(data={"x": 1, "y": 2, "z": 3}, index=["x", "y", "z"])
    r_series = pd.Series(data={"x": 1, "y": 2, "z": 3}, index=["x", "y", "z"])
    output_series = calculate_annuity(n_series, r_series)
    print(output_series)
    comparison_series = output_series.compare(
        pd.Series(
            data={"x": 2.000000, "y": 9.0 / 4.0, "z": 192.0 / 63.0},
            index=["x", "y", "z"],
        )
    )
    print(comparison_series)
    assert comparison_series.empty

    # test for r being a non-negative scalar
    output_value = calculate_annuity(1.0, 1.0)
    assert output_value == 2.0

    # test for r being a negative scalar
    output_value = calculate_annuity(1.0, -1.0)
    assert output_value == 1.0


def test_add_missing_carriers_from_costs(
    get_config_dict, get_power_network_scigrid_de, tmpdir
):
    file_path_costs = pathlib.Path(path_cwd, "test", "test_data", "costs.csv")
    config_dict = get_config_dict
    test_network_de = get_power_network_scigrid_de
    number_years = test_network_de.snapshot_weightings.objective.sum() / 8760.0
    test_costs = load_costs(
        file_path_costs,
        config_dict["costs"],
        config_dict["electricity"],
        number_years,
    )
    carriers = ["ror", "PHS", "hydro"]

    reference_component_dict = {
        "Bus": 585,
        "Carrier": 3,
        "Line": 852,
        "LineType": 34,
        "Transformer": 96,
        "TransformerType": 14,
        "Load": 489,
        "Generator": 1423,
        "StorageUnit": 38,
    }

    _add_missing_carriers_from_costs(test_network_de, test_costs, carriers)

    output_component_dict = {}
    for c in test_network_de.iterate_components(
        list(test_network_de.components.keys())[2:]
    ):
        output_component_dict[c.name] = len(c.df)

    assert reference_component_dict == output_component_dict


def test_attach_hydro(
    get_config_dict, get_power_network_scigrid_de, get_power_plants, tmpdir
):
    config_dict = get_config_dict
    file_path_costs = pathlib.Path(path_cwd, "test", "test_data", "costs.csv")
    file_path_powerplants = pathlib.Path(tmpdir, "powerplants_de.csv")
    file_path_hydro_capacities = pathlib.Path(path_cwd, "data", "hydro_capacities.csv")
    file_path_hydro_profile = pathlib.Path(tmpdir, "profile_hydro_de.nc")

    test_network_de = get_power_network_scigrid_de
    test_network_de.buses["country"] = "DE"

    number_years = test_network_de.snapshot_weightings.objective.sum() / 8760.0
    test_costs = load_costs(
        file_path_costs,
        config_dict["costs"],
        config_dict["electricity"],
        number_years,
    )

    for c in test_network_de.iterate_components(
        list(test_network_de.components.keys())[2:]
    ):
        print("BEFORE Component '{}' has {} entries)".format(c.name, len(c.df)))

        if c.name == "StorageUnit":
            print("storage unit_t inflow", test_network_de.storage_units_t.inflow)

    powerplants_file = get_power_plants
    powerplants_file.to_csv(file_path_powerplants)
    power_plants = load_powerplants(file_path_powerplants)

    inflow_de = xr.DataArray(
        1,
        coords={
            "plant": [str(x) for x in power_plants.index.values],
            "time": test_network_de.snapshots.values,
        },
        dims=["plant", "time"],
    )
    inflow_de.to_netcdf(file_path_hydro_profile)

    attach_hydro(
        test_network_de,
        test_costs,
        power_plants,
        config_dict["renewable"],
        file_path_hydro_capacities,
        file_path_hydro_profile,
        config_dict["cluster_options"]["alternative_clustering"],
    )

    reference_component_dict = {
        "Bus": 585,
        "Carrier": 3,
        "Line": 852,
        "LineType": 34,
        "Transformer": 96,
        "TransformerType": 14,
        "Load": 489,
        "Generator": 2059,
        "StorageUnit": 69,
    }

    # attach_hydro adds:
    # - 636 Generators (corresponding to the ror technology)
    # - 4 Storage Units (corresponding to the hydro technology)
    # - 27 Storage Units (corresponding to the phs technology)

    output_component_dict = {}
    for c in test_network_de.iterate_components(
        list(test_network_de.components.keys())[2:]
    ):
        output_component_dict[c.name] = len(c.df)
        print("AFTER Component '{}' has {} entries)".format(c.name, len(c.df)))

        if c.name == "StorageUnit":
            print("storage unit_t inflow", test_network_de.storage_units_t.inflow)

    assert reference_component_dict == output_component_dict
