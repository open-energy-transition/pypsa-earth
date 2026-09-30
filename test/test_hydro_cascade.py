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
    add_hydro_reservoir,
    connect_hydro_reservoirs,
    derive_local_inflows,
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

    def test_add_hydro_reservoir(self):
        import pypsa

        n = pypsa.Network()
        n.add("Bus", "electricity")

        components = add_hydro_reservoir(
            n=n,
            plant_id="PLANT_A",
            electricity_bus="electricity",
            p_nom=100.0,
            max_hours=4.0,
            efficiency_dispatch=0.9,
            cyclic=False,
        )

        self.assertEqual(
            components["water_bus"],
            "PLANT_A water",
        )
        self.assertEqual(
            n.stores.at["PLANT_A reservoir", "e_nom"],
            400.0,
        )
        self.assertAlmostEqual(
            n.links.at["PLANT_A turbine", "p_nom"],
            100.0 / 0.9,
        )
        self.assertAlmostEqual(
            n.links.at["PLANT_A turbine", "efficiency"],
            0.9,
        )
        self.assertEqual(
            n.links.at["PLANT_A turbine", "bus0"],
            "PLANT_A water",
        )
        self.assertEqual(
            n.links.at["PLANT_A turbine", "bus1"],
            "electricity",
        )

    def test_add_hydro_reservoir_rejects_invalid_efficiency(self):
        import pypsa

        n = pypsa.Network()
        n.add("Bus", "electricity")

        with self.assertRaisesRegex(
            ValueError,
            "dispatch efficiency",
        ):
            add_hydro_reservoir(
                n=n,
                plant_id="PLANT_A",
                electricity_bus="electricity",
                p_nom=100.0,
                max_hours=4.0,
                efficiency_dispatch=0.0,
            )

    def test_connect_hydro_reservoirs(self):
        import pypsa

        n = pypsa.Network()
        n.add("Bus", "electricity")

        add_hydro_reservoir(
            n=n,
            plant_id="A",
            electricity_bus="electricity",
            p_nom=100.0,
            max_hours=4.0,
            efficiency_dispatch=0.9,
        )

        add_hydro_reservoir(
            n=n,
            plant_id="B",
            electricity_bus="electricity",
            p_nom=200.0,
            max_hours=5.0,
            efficiency_dispatch=0.9,
        )

        result = connect_hydro_reservoirs(
            n=n,
            upstream_plant_id="A",
            downstream_plant_id="B",
            travel_time_hours=6.0,
            downstream_energy_ratio=0.5,
            cyclic_delay=False,
        )

        self.assertEqual(result["turbine"], "A turbine")
        self.assertEqual(result["spill"], "A spill")

        self.assertEqual(
            n.links.at["A turbine", "bus2"],
            "B water",
        )
        self.assertAlmostEqual(
            n.links.at["A turbine", "efficiency2"],
            0.5,
        )
        self.assertAlmostEqual(
            n.links.at["A turbine", "delay2"],
            6.0,
        )
        self.assertFalse(n.links.at["A turbine", "cyclic_delay2"])

        self.assertEqual(
            n.links.at["A spill", "bus0"],
            "A water",
        )
        self.assertEqual(
            n.links.at["A spill", "bus1"],
            "B water",
        )
        self.assertAlmostEqual(
            n.links.at["A spill", "efficiency"],
            0.5,
        )
        self.assertAlmostEqual(
            n.links.at["A spill", "delay"],
            6.0,
        )

    def test_connect_hydro_reservoirs_rejects_negative_delay(self):
        import pypsa

        n = pypsa.Network()
        n.add("Bus", "electricity")

        add_hydro_reservoir(
            n=n,
            plant_id="A",
            electricity_bus="electricity",
            p_nom=100.0,
            max_hours=4.0,
            efficiency_dispatch=0.9,
        )

        add_hydro_reservoir(
            n=n,
            plant_id="B",
            electricity_bus="electricity",
            p_nom=100.0,
            max_hours=4.0,
            efficiency_dispatch=0.9,
        )

        with self.assertRaisesRegex(
            ValueError,
            "Travel time",
        ):
            connect_hydro_reservoirs(
                n=n,
                upstream_plant_id="A",
                downstream_plant_id="B",
                travel_time_hours=-1.0,
                downstream_energy_ratio=1.0,
            )

    def test_full_three_reservoir_cascade(self):
        import pypsa

        n = pypsa.Network()
        n.set_snapshots(pd.RangeIndex(4))

        for bus in ["A elec", "B elec", "C elec"]:
            n.add("Bus", bus)

        for plant, bus in [
            ("A", "A elec"),
            ("B", "B elec"),
            ("C", "C elec"),
        ]:
            add_hydro_reservoir(
                n=n,
                plant_id=plant,
                electricity_bus=bus,
                p_nom=200.0,
                max_hours=10.0,
                efficiency_dispatch=0.9,
                cyclic=False,
            )

        connect_hydro_reservoirs(
            n=n,
            upstream_plant_id="A",
            downstream_plant_id="B",
            travel_time_hours=1.0,
            downstream_energy_ratio=1.0,
            cyclic_delay=False,
        )

        connect_hydro_reservoirs(
            n=n,
            upstream_plant_id="B",
            downstream_plant_id="C",
            travel_time_hours=1.0,
            downstream_energy_ratio=1.0,
            cyclic_delay=False,
        )

        local_inflows = {
            "A": [100.0, 0.0, 0.0, 0.0],
            "B": [40.0, 0.0, 0.0, 0.0],
            "C": [30.0, 0.0, 0.0, 0.0],
        }

        for plant, profile in local_inflows.items():
            p_nom = max(profile)

            n.add(
                "Generator",
                f"{plant} inflow",
                bus=f"{plant} water",
                p_nom=p_nom,
                p_min_pu=[x / p_nom for x in profile],
                p_max_pu=[x / p_nom for x in profile],
            )

        loads = {
            "A elec": [90.0, 0.0, 0.0, 0.0],
            "B elec": [36.0, 90.0, 0.0, 0.0],
            "C elec": [27.0, 36.0, 90.0, 0.0],
        }

        for bus, profile in loads.items():
            n.add(
                "Load",
                f"{bus} load",
                bus=bus,
                p_set=profile,
            )

        for turbine in ["A turbine", "B turbine", "C turbine"]:
            n.links.loc[turbine, "marginal_cost"] = 1e-6

        n.optimize(
            solver_name="highs",
            include_objective_constant=False,
        )

        expected = {
            "A turbine": [100.0, 0.0, 0.0, 0.0],
            "A->B": [0.0, 100.0, 0.0, 0.0],
            "B turbine": [40.0, 100.0, 0.0, 0.0],
            "B->C": [0.0, 40.0, 100.0, 0.0],
            "C turbine": [30.0, 40.0, 100.0, 0.0],
        }

        actual = {
            "A turbine": n.links_t.p0["A turbine"],
            "A->B": -n.links_t.p2["A turbine"],
            "B turbine": n.links_t.p0["B turbine"],
            "B->C": -n.links_t.p2["B turbine"],
            "C turbine": n.links_t.p0["C turbine"],
        }

        for key in expected:
            self.assertTrue(
                (abs(actual[key] - expected[key]) < 1e-6).all(),
                key,
            )

    def test_derive_local_inflows_chain(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A", "B"],
                "downstream": ["B", "C"],
                "travel_time_hours": [1, 1],
            }
        )

        cumulative = pd.DataFrame(
            {
                "A": [100.0, 0.0],
                "B": [140.0, 0.0],
                "C": [170.0, 0.0],
            }
        )

        local = derive_local_inflows(
            cumulative,
            topology,
        )

        pd.testing.assert_frame_equal(
            local,
            pd.DataFrame(
                {
                    "A": [100.0, 0.0],
                    "B": [40.0, 0.0],
                    "C": [30.0, 0.0],
                }
            ),
        )

    def test_derive_local_inflows_confluence(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A", "B"],
                "downstream": ["C", "C"],
                "travel_time_hours": [1, 1],
            }
        )

        cumulative = pd.DataFrame(
            {
                "A": [30.0],
                "B": [20.0],
                "C": [70.0],
            }
        )

        local = derive_local_inflows(
            cumulative,
            topology,
        )

        self.assertAlmostEqual(
            local.loc[0, "C"],
            20.0,
        )

    def test_derive_local_inflows_requires_all_profiles(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A"],
                "downstream": ["B"],
                "travel_time_hours": [1],
            }
        )

        cumulative = pd.DataFrame(
            {
                "A": [100.0],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "Missing cumulative inflow",
        ):
            derive_local_inflows(
                cumulative,
                topology,
            )

    def test_derive_local_inflows_raises_on_negative_values(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A"],
                "downstream": ["B"],
                "travel_time_hours": [1],
            }
        )

        cumulative = pd.DataFrame(
            {
                "A": [100.0, 50.0],
                "B": [90.0, 80.0],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "Negative local inflows detected",
        ):
            derive_local_inflows(
                cumulative,
                topology,
            )

    def test_derive_local_inflows_clips_negative_values(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A"],
                "downstream": ["B"],
                "travel_time_hours": [1],
            }
        )

        cumulative = pd.DataFrame(
            {
                "A": [100.0, 50.0],
                "B": [90.0, 80.0],
            }
        )

        with self.assertWarnsRegex(
            UserWarning,
            "clipped to zero",
        ):
            local = derive_local_inflows(
                cumulative,
                topology,
                negative_policy="clip",
            )

        self.assertEqual(local.loc[0, "B"], 0.0)
        self.assertEqual(local.loc[1, "B"], 30.0)

    def test_derive_local_inflows_rejects_invalid_negative_policy(self):
        topology = pd.DataFrame(
            {
                "upstream": ["A"],
                "downstream": ["B"],
                "travel_time_hours": [1],
            }
        )

        cumulative = pd.DataFrame(
            {
                "A": [100.0],
                "B": [120.0],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "negative_policy",
        ):
            derive_local_inflows(
                cumulative,
                topology,
                negative_policy="ignore",
            )


if __name__ == "__main__":
    unittest.main()
