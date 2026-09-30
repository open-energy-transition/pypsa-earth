# SPDX-FileCopyrightText: PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import math
import warnings

import pandas as pd
import pypsa

REQUIRED_TOPOLOGY_COLUMNS = {
    "upstream",
    "downstream",
    "travel_time_hours",
}

PLANT_ID_COLUMN = "plant_id"


def validate_cascade_topology(topology: pd.DataFrame) -> None:
    """
    Validate a directed cascading-hydro topology.

    The topology contains one row per hydraulic connection with the columns
    ``upstream``, ``downstream`` and ``travel_time_hours``.

    Multiple upstream nodes may converge into one downstream node. Splitting
    one upstream flow into multiple downstream branches is currently not
    supported.

    Parameters
    ----------
    topology : pandas.DataFrame
        Cascading-hydro connection table.

    Raises
    ------
    ValueError
        If the topology is malformed or contains unsupported structures.
    """
    missing_columns = REQUIRED_TOPOLOGY_COLUMNS - set(topology.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Cascade topology is missing required columns: {missing}")

    if topology.empty:
        raise ValueError("Cascade topology must contain at least one connection.")

    edges = topology[["upstream", "downstream", "travel_time_hours"]].copy()

    if edges[["upstream", "downstream"]].isna().any().any():
        raise ValueError(
            "Cascade topology contains missing upstream or downstream node IDs."
        )

    for column in ["upstream", "downstream"]:
        empty = edges[column].map(
            lambda value: isinstance(value, str) and not value.strip()
        )
        if empty.any():
            raise ValueError(f"Cascade topology contains empty values in '{column}'.")

    if (edges["upstream"] == edges["downstream"]).any():
        raise ValueError("Cascade topology contains a self-loop.")

    if edges.duplicated(["upstream", "downstream"]).any():
        raise ValueError("Cascade topology contains duplicate hydraulic connections.")

    delays = pd.to_numeric(
        edges["travel_time_hours"],
        errors="coerce",
    )

    invalid_delay = delays.map(
        lambda value: pd.isna(value) or not math.isfinite(float(value))
    )

    if invalid_delay.any():
        raise ValueError("Cascade topology contains invalid travel times.")

    if (delays < 0).any():
        raise ValueError("Cascade topology contains negative travel times.")

    downstream_count = edges.groupby("upstream")["downstream"].nunique()

    branching_nodes = downstream_count[downstream_count > 1]

    if not branching_nodes.empty:
        nodes = ", ".join(map(str, branching_nodes.index.tolist()))
        raise ValueError(
            "Cascade topology currently supports at most one "
            f"downstream connection per node. Branching nodes: {nodes}"
        )

    downstream_by_upstream = dict(zip(edges["upstream"], edges["downstream"]))

    completed = set()

    for start in downstream_by_upstream:
        if start in completed:
            continue

        path = set()
        node = start

        while node in downstream_by_upstream:
            if node in path:
                raise ValueError("Cascade topology contains a directed cycle.")

            if node in completed:
                break

            path.add(node)
            node = downstream_by_upstream[node]

        completed.update(path)


def resolve_cascade_plants(
    topology: pd.DataFrame,
    powerplants: pd.DataFrame,
) -> pd.DataFrame:
    """
    Resolve cascade topology nodes against the powerplant table.

    Plants participating in a cascade must provide a unique ``plant_id``.

    Parameters
    ----------
    topology : pandas.DataFrame
        Cascade connections with ``upstream`` and ``downstream`` node IDs.
    powerplants : pandas.DataFrame
        Power plant table containing a ``plant_id`` column.

    Returns
    -------
    pandas.DataFrame
        Powerplant rows participating in the cascade, indexed by
        ``plant_id``.

    Raises
    ------
    ValueError
        If ``plant_id`` is unavailable, duplicated, or if topology nodes
        cannot be resolved.
    """
    if PLANT_ID_COLUMN not in powerplants.columns:
        raise ValueError(
            "Powerplant data must contain a 'plant_id' column "
            "to resolve cascading-hydro plants."
        )

    plant_ids = powerplants[PLANT_ID_COLUMN]

    duplicate_mask = plant_ids.notna() & plant_ids.astype(str).duplicated(keep=False)

    if duplicate_mask.any():
        duplicates = sorted(plant_ids.loc[duplicate_mask].astype(str).unique())
        raise ValueError(
            "Duplicate plant_id values found in powerplant data: "
            + ", ".join(duplicates)
        )

    plants = (
        powerplants.loc[plant_ids.notna()].copy().set_index(PLANT_ID_COLUMN, drop=False)
    )

    topology_nodes = set(topology["upstream"]).union(topology["downstream"])

    missing = sorted(topology_nodes - set(plants.index))

    if missing:
        raise ValueError(
            "Cascade topology references nodes which cannot be "
            "resolved to powerplants: " + ", ".join(map(str, missing))
        )

    return plants.loc[sorted(topology_nodes)].copy()


def add_hydro_reservoir(
    n: pypsa.Network,
    plant_id: str,
    electricity_bus: str,
    p_nom: float,
    max_hours: float,
    efficiency_dispatch: float,
    cyclic: bool = True,
) -> dict[str, str]:
    """Add a reservoir as a water bus, Store and turbine Link."""
    if p_nom <= 0:
        raise ValueError("Reservoir p_nom must be positive.")
    if max_hours <= 0:
        raise ValueError("Reservoir max_hours must be positive.")
    if not 0 < efficiency_dispatch <= 1:
        raise ValueError(
            "Reservoir dispatch efficiency must be in the interval (0, 1]."
        )

    if electricity_bus not in n.buses.index:
        raise ValueError(f"Electricity bus '{electricity_bus}' does not exist.")

    water_bus = f"{plant_id} water"
    store = f"{plant_id} reservoir"
    turbine = f"{plant_id} turbine"

    if "water" not in n.carriers.index:
        n.add("Carrier", "water")
    if "hydro" not in n.carriers.index:
        n.add("Carrier", "hydro")

    n.add(
        "Bus",
        water_bus,
        carrier="water",
    )

    n.add(
        "Store",
        store,
        bus=water_bus,
        carrier="hydro",
        e_nom=p_nom * max_hours,
        e_cyclic=cyclic,
    )

    n.add(
        "Link",
        turbine,
        bus0=water_bus,
        bus1=electricity_bus,
        bus2="",
        carrier="hydro",
        p_nom=p_nom / efficiency_dispatch,
        efficiency=efficiency_dispatch,
        efficiency2=1.0,
        delay2=0.0,
        cyclic_delay2=True,
    )

    return {
        "water_bus": water_bus,
        "store": store,
        "turbine": turbine,
    }


def connect_hydro_reservoirs(
    n: pypsa.Network,
    upstream_plant_id: str,
    downstream_plant_id: str,
    travel_time_hours: float,
    downstream_energy_ratio: float,
    cyclic_delay: bool = False,
) -> dict[str, str]:
    """Connect two hydro reservoirs with delayed turbine outflow and spill."""
    if travel_time_hours < 0:
        raise ValueError("Travel time must be non-negative.")

    if not math.isfinite(travel_time_hours):
        raise ValueError("Travel time must be finite.")

    if downstream_energy_ratio <= 0 or not math.isfinite(downstream_energy_ratio):
        raise ValueError("Downstream energy ratio must be positive and finite.")

    upstream_water_bus = f"{upstream_plant_id} water"
    downstream_water_bus = f"{downstream_plant_id} water"
    turbine = f"{upstream_plant_id} turbine"
    spill = f"{upstream_plant_id} spill"

    if upstream_water_bus not in n.buses.index:
        raise ValueError(f"Upstream water bus '{upstream_water_bus}' does not exist.")

    if downstream_water_bus not in n.buses.index:
        raise ValueError(
            f"Downstream water bus '{downstream_water_bus}' does not exist."
        )

    if turbine not in n.links.index:
        raise ValueError(f"Upstream turbine '{turbine}' does not exist.")

    n.links.loc[turbine, "bus2"] = downstream_water_bus
    n.links.loc[turbine, "efficiency2"] = downstream_energy_ratio
    n.links.loc[turbine, "delay2"] = travel_time_hours
    n.links.loc[turbine, "cyclic_delay2"] = cyclic_delay

    n.add(
        "Link",
        spill,
        bus0=upstream_water_bus,
        bus1=downstream_water_bus,
        bus2="",
        efficiency2=1.0,
        delay2=0.0,
        cyclic_delay2=True,
        carrier="hydro",
        p_nom=float("inf"),
        efficiency=downstream_energy_ratio,
        delay=travel_time_hours,
        cyclic_delay=cyclic_delay,
    )

    return {
        "turbine": turbine,
        "spill": spill,
    }


def derive_local_inflows(
    cumulative_inflows: pd.DataFrame,
    topology: pd.DataFrame,
    negative_policy: str = "raise",
) -> pd.DataFrame:
    """
    Convert cumulative inflows into local incremental inflows.

    Travel-time delays are handled separately by the hydraulic routing.
    """
    if negative_policy not in {"raise", "clip"}:
        raise ValueError("negative_policy must be either 'raise' or 'clip'.")

    validate_cascade_topology(topology)

    nodes = set(topology["upstream"]).union(topology["downstream"])
    missing = sorted(nodes - set(cumulative_inflows.columns))

    if missing:
        raise ValueError(
            "Missing cumulative inflow profiles for cascade nodes: "
            + ", ".join(map(str, missing))
        )

    local = cumulative_inflows.copy()

    for downstream, edges in topology.groupby("downstream"):
        upstream = edges["upstream"].tolist()
        local[downstream] = cumulative_inflows[downstream] - cumulative_inflows[
            upstream
        ].sum(axis=1)

    cascade_columns = list(nodes)
    negative = local[cascade_columns] < 0

    if negative.any().any():
        if negative_policy == "raise":
            counts = negative.sum()
            affected = counts[counts > 0]
            detail = ", ".join(f"{node}: {count}" for node, count in affected.items())
            raise ValueError(
                "Negative local inflows detected after cumulative-flow "
                f"subtraction ({detail})."
            )

        warnings.warn(
            "Negative local inflows detected after cumulative-flow "
            "subtraction and clipped to zero.",
            UserWarning,
            stacklevel=2,
        )
        local[cascade_columns] = local[cascade_columns].clip(lower=0.0)

    return local
