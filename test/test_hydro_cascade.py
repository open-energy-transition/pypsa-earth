# SPDX-FileCopyrightText: PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "scripts"),
)

from hydro_cascade import (
    resolve_cascade_plants,
    validate_cascade_topology,
)


class TestValidateCascadeTopology(unittest.TestCase):
    def test_valid_chain(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A", "B"],
                "downstream": ["B", "C"],
                "travel_time_hours": [6, 2],
            }
        )

        validate_cascade_topology(topology)

    def test_valid_confluence(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A", "B"],
                "downstream": ["C", "C"],
                "travel_time_hours": [6, 4],
            }
        )

        validate_cascade_topology(topology)

    def test_missing_column(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A"],
                "downstream": ["B"],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "missing required columns",
        ):
            validate_cascade_topology(topology)

    def test_empty_topology(self):
        topology = pd.DataFrame(
            columns=[
                "upstream",
                "downstream",
                "travel_time_hours",
            ]
        )

        with self.assertRaisesRegex(
            ValueError,
            "at least one connection",
        ):
            validate_cascade_topology(topology)

    def test_missing_node(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A"],
                "downstream": [None],
                "travel_time_hours": [1],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "missing upstream or downstream",
        ):
            validate_cascade_topology(topology)

    def test_self_loop(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A"],
                "downstream": ["A"],
                "travel_time_hours": [1],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "self-loop",
        ):
            validate_cascade_topology(topology)

    def test_duplicate_connection(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A", "A"],
                "downstream": ["B", "B"],
                "travel_time_hours": [1, 1],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "duplicate hydraulic connections",
        ):
            validate_cascade_topology(topology)

    def test_negative_delay(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A"],
                "downstream": ["B"],
                "travel_time_hours": [-1],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "negative travel times",
        ):
            validate_cascade_topology(topology)

    def test_non_numeric_delay(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A"],
                "downstream": ["B"],
                "travel_time_hours": ["six"],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "invalid travel times",
        ):
            validate_cascade_topology(topology)

    def test_branching_is_rejected(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A", "A"],
                "downstream": ["B", "C"],
                "travel_time_hours": [1, 2],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "at most one downstream connection",
        ):
            validate_cascade_topology(topology)

    def test_cycle_is_rejected(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A", "B", "C"],
                "downstream": ["B", "C", "A"],
                "travel_time_hours": [1, 1, 1],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "directed cycle",
        ):
            validate_cascade_topology(topology)

    def test_resolve_cascade_plants(self):
        topology = pd.DataFrame(
            {
                "upstream": ["PLANT_A", "PLANT_B"],
                "downstream": ["PLANT_B", "PLANT_C"],
                "travel_time_hours": [6, 2],
            }
        )

        powerplants = pd.DataFrame(
            {
                "plant_id": [
                    "PLANT_A",
                    "PLANT_B",
                    "PLANT_C",
                    "OTHER",
                ],
                "name": [
                    "Plant A",
                    "Plant B",
                    "Plant C",
                    "Other",
                ],
                "p_nom": [100, 200, 300, 400],
            }
        )

        result = resolve_cascade_plants(
            topology,
            powerplants,
        )

        self.assertEqual(
            set(result.index),
            {"PLANT_A", "PLANT_B", "PLANT_C"},
        )
        self.assertEqual(
            result.loc["PLANT_B", "p_nom"],
            200,
        )

    def test_resolve_requires_plant_id(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A"],
                "downstream": ["B"],
                "travel_time_hours": [1],
            }
        )

        powerplants = pd.DataFrame(
            {
                "name": ["A", "B"],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "plant_id",
        ):
            resolve_cascade_plants(
                topology,
                powerplants,
            )

    def test_duplicate_plant_id_is_rejected(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A"],
                "downstream": ["B"],
                "travel_time_hours": [1],
            }
        )

        powerplants = pd.DataFrame(
            {
                "plant_id": ["A", "A", "B"],
                "name": ["A1", "A2", "B"],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "Duplicate plant_id",
        ):
            resolve_cascade_plants(
                topology,
                powerplants,
            )

    def test_unresolved_topology_node_is_rejected(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A"],
                "downstream": ["UNKNOWN"],
                "travel_time_hours": [1],
            }
        )

        powerplants = pd.DataFrame(
            {
                "plant_id": ["A", "B"],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "cannot be resolved",
        ):
            resolve_cascade_plants(
                topology,
                powerplants,
            )


if __name__ == "__main__":
    unittest.main()
