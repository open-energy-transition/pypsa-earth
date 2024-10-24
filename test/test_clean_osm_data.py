# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-

import pathlib
import pytest
import sys

sys.path.append("./scripts")

from test.conftest import get_config_dict

from clean_osm_data import filter_voltage, load_network_data, prepare_substation_df

path_cwd = str(pathlib.Path.cwd())

input_files_dictionary = {
    "cables": pathlib.Path(path_cwd, "test", "test_data", "sampled_raw_cables.geojson"),
    "lines": pathlib.Path(path_cwd, "test", "test_data", "sampled_raw_lines.geojson"),
    "substations": pathlib.Path(path_cwd, "test", "test_data", "sampled_raw_substations.geojson")
}


def test_filter_voltage(get_config_dict):
    """
    The test verifies what is returned by filter_voltage.
    """
    config_dict = get_config_dict
    data_options = config_dict["clean_osm_data_options"]
    voltage_threshold = float(data_options["threshold_voltage"])
    df_all_substations = load_network_data("substations", data_options, input_files_dictionary)
    df_all_substations = prepare_substation_df(df_all_substations)
    output_df = filter_voltage(df_all_substations, voltage_threshold)
    assert output_df.loc[output_df["voltage"] < voltage_threshold].shape[0] == 0


@pytest.mark.parametrize(
    "network_asset, use_custom_val, expected", [
        ("substations", "OSM_only", ("substation", 6065)),
        ("lines", "OSM_only", ("line", 4715)),
        ("cables", "custom_only", ("cable", 485)),
        ("cables", "add_custom", ("cable", 970)),
        ("cables", "OSM_only", ("cable", 485)),
    ],)
def test_load_network_data(get_config_dict, network_asset, use_custom_val, expected):
    """
    The test verifies what is returned by load_network_data.
    """
    config_dict = get_config_dict
    data_options = config_dict["clean_osm_data_options"]
    data_options[f"use_custom_{network_asset}"] = use_custom_val
    if data_options[f"use_custom_{network_asset}"] in ["add_custom", "custom_only"]:
        data_options[f"path_custom_{network_asset}"] = input_files_dictionary[network_asset]
    output_df = load_network_data(network_asset, data_options, input_files_dictionary)
    assert len(output_df["tags.power"].unique()) == 1 and output_df["tags.power"].unique()[0] == expected[0]
    assert output_df.shape[0] == expected[1]


def test_prepare_substation_df(get_config_dict):
    """
    The test verifies what is returned by prepare_substation_df.
    """
    config_dict = get_config_dict
    data_options = config_dict["clean_osm_data_options"]
    column_list_reference = [
        "bus_id",
        "symbol",
        "tag_substation",
        "voltage",
        "geometry",
        "lon",
        "lat",
        "dc",
        "under_construction",
        "station_id",
        "tag_area",
        "country",
    ]
    df_all_substations = load_network_data("substations", data_options, input_files_dictionary)
    output_df = prepare_substation_df(df_all_substations)
    assert output_df.shape == (6065, 12)
    assert len(output_df["dc"].unique()) == 1 and ~output_df["dc"].unique()[0]
    assert len(output_df["under_construction"].unique()) == 1 and ~output_df["under_construction"].unique()[0]
    assert all([x == y for x, y in zip(list(output_df.columns), column_list_reference)])
