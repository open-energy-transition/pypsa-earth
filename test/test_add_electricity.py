# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-

import pathlib
import sys

import numpy as np
import pandas as pd
import pypsa
import yaml

sys.path.append("./scripts")

from _helpers import get_path
from add_electricity import attach_hydro, load_costs, load_powerplants

path_cwd = pathlib.Path.cwd()

path_to_config = get_path(path_cwd, "config.default.yaml")
with open(path_to_config, "r") as file:
    config_dict = yaml.safe_load(file)

costs_config_dict = {
    "year": 2030,
    "version": "v0.5.0",
    "rooftop_share": 0.14,
    "USD2013_to_EUR2013": 0.7532,
    "fill_values": {
        "FOM": 0,
        "VOM": 0,
        "efficiency": 1,
        "fuel": 0,
        "investment": 0,
        "lifetime": 25,
        "CO2 intensity": 0,
        "discount rate": 0.07,
    },
    "marginal_cost": {
        "solar": 0.01,
        "onwind": 0.015,
        "offwind": 0.015,
        "hydro": 0.0,
        "H2": 0.0,
        "electrolysis": 0.0,
        "fuel cell": 0.0,
        "battery": 0.0,
        "battery inverter": 0.0,
    },
    "emission_prices": {
        "co2": 0.0,
    },
}

config_dict = {
    "electricity": {
        "base_voltage": 380.0,
        "voltages": [132.0, 220.0, 300.0, 380.0, 500.0, 750.0],
        "co2limit": 1.487e9,
        "co2base": 1.487e9,
        "agg_p_nom_limits": "data/agg_p_nom_minmax.csv",
        "hvdc_as_lines": True,
        "automatic_emission": True,
        "automatic_emission_base_year": 1990,
        "operational_reserve": {
            "activate": True,
            "epsilon_load": 0.02,
            "epsilon_vres": 0.02,
            "contingency": 0,
        },
        "max_hours": {
            "battery": 6,
            "H2": 168,
        },
        "extendable_carriers": {
            "Generator": ["solar", "onwind", "offwind-ac", "offwind-dc", "OCGT"],
            "StorageUnit": ["H2"],
            "Store": ["battery", "H2"],
            "Link": ["H2 pipeline"],
        },
        "powerplants_filter": "(DateOut >= 2022 or DateOut != DateOut)",
        "custom_powerplants": False,
        "conventional_carriers": [
            "nuclear",
            "oil",
            "OCGT",
            "CCGT",
            "coal",
            "lignite",
            "geothermal",
            "biomass",
        ],
        "renewable_carriers": [
            "solar",
            "csp",
            "onwind",
            "offwind-ac",
            "offwind-dc",
            "hydro",
        ],
        "estimate_renewable_capacities": {
            "stats": "irena",
            "year": 2020,
            "p_nom_min": 1,
            "p_nom_max": False,
            "technology_mapping": {
                "Offshore": ["offwind-ac", "offwind-dc"],
                "Onshore": ["onwind"],
                "PV": ["solar"],
            },
        },
    },
    "renewable": {
        "onwind": {
            "cutout": "cutout-2013-era5",
            "resource": {"method": "wind", "turbine": "Vestas_V112_3MW"},
            "capacity_per_sqkm": 3,
            "copernicus": {
                "grid_codes": [
                    20,
                    30,
                    40,
                    60,
                    100,
                    111,
                    112,
                    113,
                    114,
                    115,
                    116,
                    121,
                    122,
                    123,
                    124,
                    125,
                    126,
                ],
                "distance": 1000,
                "distance_grid_codes": [50],
            },
            "natura": True,
            "potential": "simple",
            "clip_p_max_pu": 1.0e-2,
            "extendable": True,
        },
        "offwind - ac": {
            "cutout": "cutout-2013-era5",
            "resource": {
                "method": "wind",
                "turbine": "NREL_ReferenceTurbine_5MW_offshore",
            },
            "capacity_per_sqkm": 2,
            "correction_factor": 0.8855,
            "copernicus": {
                "grid_codes": [80, 200],
            },
            "natura": True,
            "max_depth": 50,
            "max_shore_distance": 30000,
            "potential": "simple",
            "clip_p_max_pu": 1.0e-2,
            "extendable": True,
        },
        "offwind - dc": {
            "cutout": "cutout-2013-era5",
            "resource": {
                "method": "wind",
                "turbine": "NREL_ReferenceTurbine_5MW_offshore",
            },
            "capacity_per_sqkm": 3,
            "correction_factor": 0.8855,
            "copernicus": {
                "grid_codes": [80, 200],
            },
            "natura": True,
            "max_depth": 50,
            "min_shore_distance": 30000,
            "potential": "simple",
            "clip_p_max_pu": 1.0e-2,
            "extendable": True,
        },
        "solar": {
            "cutout": "cutout-2013-era5",
            "resource": {
                "method": "pv",
                "panel": "CSi",
                "orientation": "latitude_optimal",
            },
            "capacity_per_sqkm": 4.6,
            "correction_factor": 0.854337,
            "copernicus": {
                "grid_codes": [20, 30, 40, 50, 60, 90, 100],
            },
            "natura": True,
            "potential": "simple",
            "clip_p_max_pu": 1.0e-2,
            "extendable": True,
        },
        "hydro": {
            "cutout": "cutout-2013-era5",
            "hydrobasins_level": 6,
            "resource": {
                "method": "hydro",
                "hydrobasins": "data/hydrobasins/hybas_world.shp",
                "flowspeed": 1.0,
            },
            "carriers": ["ror", "PHS", "hydro"],
            "PHS_max_hours": 6,
            "hydro_max_hours": "energy_capacity_totals_by_country",
            "hydro_max_hours_default": 6.0,
            "clip_min_inflow": 1.0,
            "extendable": True,
            "normalization": {
                "method": "hydro_capacities",
                "year": 2013,
            },
            "multiplier": 1.1,
        },
        "csp": {
            "cutout": "cutout-2013-era5-tutorial",
            "resource": {"method": "csp", "installation": "SAM_solar_tower"},
            "capacity_per_sqkm": 2.392,
            "copernicus": {
                "grid_codes": [20, 30, 40, 60, 90],
                "distancing_codes": [50],
                "distance_to_codes": 3000,
            },
            "natura": True,
            "potential": "simple",
            "clip_p_max_pu": 1.0e-2,
            "extendable": True,
            "csp_model": "simple",
        },
    },
    "cluster_options": {
        "simplify_network": {
            "to_substations": False,
            "algorithm": "kmeans",
            "feature": "solar+onwind-time",
            "exclude_carriers": [],
            "remove_stubs": True,
            "remove_stubs_across_borders": True,
            "p_threshold_drop_isolated": 20,
            "p_threshold_merge_isolated": 300,
            "s_threshold_fetch_isolated": 0.05,
        },
        "cluster_network": {
            "algorithm": "kmeans",
            "feature": "solar + onwind - time",
            "exclude_carriers": [],
        },
        "alternative_clustering": False,
        "distribute_cluster": ["load"],
        "out_logging": True,
        "aggregation_strategies": {
            "generators": {
                "p_nom": "sum",
                "p_nom_max": "sum",
                "p_nom_min": "sum",
                "p_min_pu": "mean",
                "marginal_cost": "mean",
                "committable": "any",
                "ramp_limit_up": "max",
                "ramp_limit_down": "max",
                "efficiency": "mean",
            }
        },
    },
}


def test_attach_hydro():
    file_path_costs = get_path(path_cwd, "data", "costs.csv")
    file_path_powerplants = get_path(path_cwd, "data", "custom_powerplants.csv")
    file_path_hydro_capacities = get_path(path_cwd, "data", "hydro_capacities.csv")
    test_network_de = pypsa.examples.scigrid_de(from_master=True)
    power_plants = load_powerplants(file_path_powerplants)

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

    attach_hydro(
        test_network_de,
        test_costs,
        power_plants,
        config_dict["renewable"],
        file_path_hydro_capacities,
        config_dict["cluster_options"]["alternative_clustering"],
    )

    for c in test_network_de.iterate_components(
        list(test_network_de.components.keys())[2:]
    ):
        print("AFTER Component '{}' has {} entries)".format(c.name, len(c.df)))

    assert False
