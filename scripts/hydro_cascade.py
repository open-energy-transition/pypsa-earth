# SPDX-FileCopyrightText: PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import math

import pandas as pd

REQUIRED_TOPOLOGY_COLUMNS = {
    "upstream",
    "downstream",
    "travel_time_hours",
}


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
