# SPDX-FileCopyrightText: PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
import unittest
from pathlib import Path

import pandas as pd
import pypsa

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "scripts"),
)

from hydro_cascade import (
    add_hydro_reservoir,
    connect_hydro_reservoirs,
    derive_local_inflows,
    discharge_to_hydraulic_inflow,
    pop_cascade_storage_units,
    resolve_cascade_plants,
    restore_cascade_storage_units,
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

    def test_discharge_to_hydraulic_inflow(self):
        discharge = pd.DataFrame(
            {
                "A": [100.0],
                "B": [40.0],
            }
        )

        dam_heights = pd.Series(
            {
                "A": 20.0,
                "B": 50.0,
            }
        )

        inflow = discharge_to_hydraulic_inflow(
            discharge,
            dam_heights,
            multiplier=1.0,
        )

        self.assertAlmostEqual(inflow.loc[0, "A"], 20.0)
        self.assertAlmostEqual(inflow.loc[0, "B"], 20.0)

    def test_discharge_to_hydraulic_inflow_applies_multiplier(self):
        discharge = pd.DataFrame({"A": [100.0]})
        dam_heights = pd.Series({"A": 20.0})

        inflow = discharge_to_hydraulic_inflow(
            discharge,
            dam_heights,
            multiplier=2.0,
        )

        self.assertAlmostEqual(inflow.loc[0, "A"], 40.0)

    def test_discharge_to_hydraulic_inflow_requires_height(self):
        discharge = pd.DataFrame({"A": [100.0]})
        dam_heights = pd.Series({"B": 20.0})

        with self.assertRaisesRegex(
            ValueError,
            "Missing dam heights",
        ):
            discharge_to_hydraulic_inflow(
                discharge,
                dam_heights,
            )

    def test_cascade_supports_downstream_energy_ratio_above_one(self):
        n = pypsa.Network()
        n.set_snapshots(pd.RangeIndex(3))

        n.add("Carrier", "AC")

        for plant in ["ITT", "KGU"]:
            n.add("Bus", f"{plant} elec", carrier="AC")

            add_hydro_reservoir(
                n,
                plant_id=plant,
                electricity_bus=f"{plant} elec",
                p_nom=3000.0,
                max_hours=10.0,
                efficiency_dispatch=0.9,
                cyclic=False,
            )

        ratio = 600.0 / 24.5

        connect_hydro_reservoirs(
            n,
            upstream_plant_id="ITT",
            downstream_plant_id="KGU",
            travel_time_hours=1.0,
            downstream_energy_ratio=ratio,
            cyclic_delay=False,
        )

        n.links.loc[
            ["ITT turbine", "KGU turbine"],
            "marginal_cost",
        ] = 1e-6

        n.add(
            "Generator",
            "ITT inflow",
            bus="ITT water",
            p_nom=100.0,
            p_min_pu=[1.0, 0.0, 0.0],
            p_max_pu=[1.0, 0.0, 0.0],
        )

        n.add(
            "Load",
            "ITT load",
            bus="ITT elec",
            p_set=[90.0, 0.0, 0.0],
        )

        expected = 100.0 * ratio

        n.add(
            "Load",
            "KGU load",
            bus="KGU elec",
            p_set=[0.0, expected * 0.9, 0.0],
        )

        n.optimize(
            solver_name="highs",
            include_objective_constant=False,
        )

        self.assertAlmostEqual(
            n.links_t.p0.loc[1, "KGU turbine"],
            expected,
        )

    def test_preserve_cascade_storage_unit_through_clustering(self):
        from pypsa.clustering.spatial import get_clustering_from_busmap

        n = pypsa.Network()
        n.set_snapshots(pd.RangeIndex(2))

        n.add("Carrier", "AC")
        n.add("Carrier", "hydro")
        n.add("Bus", ["A", "B"], carrier="AC")

        n.add(
            "StorageUnit",
            "cascade",
            bus="A",
            carrier="hydro",
            p_nom=100.0,
            max_hours=4.0,
            efficiency_dispatch=0.9,
            inflow=[10.0, 20.0],
        )

        n.add(
            "StorageUnit",
            "regular",
            bus="B",
            carrier="hydro",
            p_nom=200.0,
            max_hours=6.0,
            efficiency_dispatch=0.9,
            inflow=[30.0, 40.0],
        )

        n.storage_units["plant_id"] = ""
        n.storage_units.loc["cascade", "plant_id"] = "TEST_CASCADE"

        static, dynamic = pop_cascade_storage_units(n)

        busmap = pd.Series(
            {
                "A": "X",
                "B": "X",
            }
        )

        nc = get_clustering_from_busmap(
            n,
            busmap,
            aggregate_one_ports={"StorageUnit": {}},
        ).n

        restore_cascade_storage_units(
            nc,
            static,
            dynamic,
            busmap,
        )

        self.assertIn("cascade", nc.storage_units.index)
        self.assertEqual(
            nc.storage_units.loc["cascade", "bus"],
            "X",
        )
        self.assertEqual(
            nc.storage_units.loc["cascade", "plant_id"],
            "TEST_CASCADE",
        )
        self.assertEqual(
            nc.storage_units.loc["cascade", "p_nom"],
            100.0,
        )
        self.assertEqual(
            nc.storage_units_t.inflow["cascade"].tolist(),
            [10.0, 20.0],
        )


if __name__ == "__main__":
    unittest.main()
