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

from add_electricity import attach_hydro, load_costs, load_powerplants

path_cwd = pathlib.Path.cwd()

path_config = pathlib.Path(path_cwd, "config.default.yaml")
with open(path_config, "r") as file:
    config_dict = yaml.safe_load(file)


def test_attach_hydro():

    # get number of hydro plants from powerplants.csv and check whether the number of Storage Units is indeed correct

    file_path_costs = pathlib.Path(path_cwd, "test", "test_data", "costs.csv")
    file_path_powerplants = pathlib.Path(
        path_cwd, "test", "test_data", "powerplants.csv"
    )
    file_path_hydro_capacities = pathlib.Path(path_cwd, "data", "hydro_capacities.csv")
    file_path_hydro_profile = pathlib.Path(
        path_cwd, "test", "test_data", "profile_hydro_sampled.nc"
    )

    test_network_de = pypsa.examples.scigrid_de(from_master=True)
    test_network_de.buses["country"] = "US"

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

    print("=================")
    print("=================")
    print("=================")

    attach_hydro(
        test_network_de,
        test_costs,
        power_plants,
        config_dict["renewable"],
        file_path_hydro_capacities,
        file_path_hydro_profile,
        config_dict["cluster_options"]["alternative_clustering"],
    )

    for c in test_network_de.iterate_components(
        list(test_network_de.components.keys())[2:]
    ):
        print("AFTER Component '{}' has {} entries)".format(c.name, len(c.df)))

        if c.name == "StorageUnit":
            print(test_network_de.storage_units.inflow.unique())

    assert False
