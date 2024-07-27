# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.append("./scripts")

from _helpers import change_to_script_dir, get_path, mock_snakemake
from base_network import (
    _get_linetypes_config,
    _load_buses_from_osm,
    _load_converters_from_osm,
    _load_lines_from_osm,
    _load_transformers_from_osm,
    _set_electrical_parameters_lines,
    get_country,
)

path_cwd = pathlib.Path.cwd()

lines_dict = {
    "ac_types": {
        132.0: "243-AL1/39-ST1A 20.0",
        220.0: "Al/St 240/40 2-bundle 220.0",
        300.0: "Al/St 240/40 3-bundle 300.0",
        380.0: "Al/St 240/40 4-bundle 380.0",
        500.0: "Al/St 240/40 4-bundle 380.0",
        750.0: "Al/St 560/50 4-bundle 750.0",
    },
    "dc_types": {
        500.0: "HVDC XLPE 1000",
    },
    "s_max_pu": 0.7,
    "s_nom_max": np.inf,
    "length_factor": 1.25,
    "under_construction": "zero",
}

links_dict = {
    "p_max_pu": 1.0,
    "p_nom_max": np.inf,
    "under_construction": "zero",
}

transformers_dict = {
    "x": 0.1,
    "s_nom": 2000.0,
    "type": "",
}

voltages_list = [132.0, 220.0, 300.0, 380.0, 500.0, 750.0]


def test_get_country():
    data_list = [['"country"=>"NG"'], ['"country"=>"CH"'], ['"country"=>"AU"']]
    df_exercise_with_tags = pd.DataFrame(data_list, columns=["tags"])
    df_exercise_no_tags = pd.DataFrame(data_list, columns=["other"])

    series_with_tags = get_country(df_exercise_with_tags)
    reference_series_with_tags = pd.Series(["NG", "CH", "AU"])
    comparison_series_with_tags = series_with_tags.compare(reference_series_with_tags)

    series_no_tags = get_country(df_exercise_no_tags)
    reference_series_no_tags = pd.Series([np.nan, np.nan, np.nan])
    comparison_series_no_tags = series_no_tags.compare(reference_series_no_tags)

    assert comparison_series_with_tags.size == 0
    assert comparison_series_no_tags.size == 0


def test_load_buses_from_osm(tmpdir):

    data_buses_input = [
        [
            0,
            0,
            161000,
            False,
            "substation",
            False,
            "transmission",
            0.0,
            2.5914,
            9.3321,
            "BJ",
            "POINT (2.5914 9.3321)",
            True,
        ],
    ]
    column_buses_input = [
        "bus_id",
        "station_id",
        "voltage",
        "dc",
        "symbol",
        "under_construction",
        "tag_substation",
        "tag_area",
        "lon",
        "lat",
        "country",
        "geometry",
        "substation_lv",
    ]
    df_buses_input = pd.DataFrame(data_buses_input, columns=column_buses_input)

    data_buses_reference = [
        [
            "0",
            161.0,
            "substation",
            False,
            "transmission",
            0.0,
            2.5914,
            9.3321,
            "BJ",
            "POINT (2.5914 9.3321)",
            True,
            "AC",
            2.5914,
            9.3321,
        ],
    ]
    column_buses_reference = [
        "bus_id",
        "v_nom",
        "symbol",
        "under_construction",
        "tag_substation",
        "tag_area",
        "lon",
        "lat",
        "country",
        "geometry",
        "substation_lv",
        "carrier",
        "x",
        "y",
    ]
    df_buses_reference = pd.DataFrame(
        data_buses_reference, columns=column_buses_reference
    ).set_index("bus_id")

    file_path = get_path(tmpdir, "buses_exercise.csv")
    df_buses_input.to_csv(file_path)

    df_buses_output = _load_buses_from_osm(file_path)

    df_buses_comparison = df_buses_output.compare(df_buses_reference)

    pathlib.Path.unlink(file_path)

    assert df_buses_comparison.empty


def test_load_lines_from_osm(tmpdir):
    data_lines_input = [
        [
            "204361221-1_0",
            50.0,
            "line",
            161000,
            "111",
            "0",
            3.0,
            110071.89434240988,
            False,
            False,
            False,
            "BJ",
            "LINESTRING (2.6594 10.2042, 2.6594451 10.2042341)",
            "MULTIPOINT ((2.6594 10.2042), (2.5914 9.3321))",
            "POINT (2.6594 10.2042)",
            "POINT (2.5914 9.3321)",
            2.6594,
            10.2042,
            2.5914,
            9.3321,
        ],
    ]
    column_lines_input = [
        "line_id",
        "tag_frequency",
        "tag_type",
        "voltage",
        "bus0",
        "bus1",
        "circuits",
        "length",
        "underground",
        "under_construction",
        "dc",
        "country",
        "geometry",
        "bounds",
        "bus_0_coors",
        "bus_1_coors",
        "bus0_lon",
        "bus0_lat",
        "bus1_lon",
        "bus1_lat",
    ]
    df_lines_input = pd.DataFrame(data_lines_input, columns=column_lines_input)

    data_lines_reference = [
        [
            "204361221-1_0",
            50.0,
            "line",
            161.0,
            "111",
            "0",
            3.0,
            110.07189434240988,
            False,
            False,
            False,
            "BJ",
            "LINESTRING (2.6594 10.2042, 2.6594451 10.2042341)",
            "MULTIPOINT ((2.6594 10.2042), (2.5914 9.3321))",
            "POINT (2.6594 10.2042)",
            "POINT (2.5914 9.3321)",
            2.6594,
            10.2042,
            2.5914,
            9.3321,
        ],
    ]
    column_lines_reference = [
        "line_id",
        "tag_frequency",
        "tag_type",
        "v_nom",
        "bus0",
        "bus1",
        "num_parallel",
        "length",
        "underground",
        "under_construction",
        "dc",
        "country",
        "geometry",
        "bounds",
        "bus_0_coors",
        "bus_1_coors",
        "bus0_lon",
        "bus0_lat",
        "bus1_lon",
        "bus1_lat",
    ]
    df_lines_reference = pd.DataFrame(
        data_lines_reference, columns=column_lines_reference
    ).set_index("line_id")

    file_path = get_path(tmpdir, "lines_exercise.csv")
    df_lines_input.to_csv(file_path)

    df_lines_output = _load_lines_from_osm(file_path)

    df_lines_comparison = df_lines_output.compare(df_lines_reference)
    pathlib.Path.unlink(file_path)
    assert df_lines_comparison.empty


def test_load_transformers_from_osm(tmpdir):
    data_transformers_input = [
        [
            "transf_1_0",
            "1",
            "2",
            161000,
            330000,
            "BJ",
            "LINESTRING(2.648 6.7394, 2.649 6.7404)",
            "MULTIPOINT((2.648 6.7394), (2.649 6.7404))",
            "POINT(2.648 6.7394)",
            "POINT(2.649 6.7404)",
            2.648,
            6.7394,
            2.649,
            6.7404,
        ],
    ]
    column_transformers_input = [
        "line_id",
        "bus0",
        "bus1",
        "voltage_bus0",
        "voltage_bus1",
        "country",
        "geometry",
        "bounds",
        "bus_0_coors",
        "bus_1_coors",
        "bus0_lon",
        "bus0_lat",
        "bus1_lon",
        "bus1_lat",
    ]
    df_transformers_input = pd.DataFrame(
        data_transformers_input, columns=column_transformers_input
    )

    data_transformers_reference = [
        [
            "transf_1_0",
            0,
            "1",
            "2",
            161000,
            330000,
            "BJ",
            "LINESTRING(2.648 6.7394, 2.649 6.7404)",
            "MULTIPOINT((2.648 6.7394), (2.649 6.7404))",
            "POINT(2.648 6.7394)",
            "POINT(2.649 6.7404)",
            2.648,
            6.7394,
            2.649,
            6.7404,
        ],
    ]
    column_transformers_reference = [
        "transformer_id",
        "Unnamed: 0",
        "bus0",
        "bus1",
        "voltage_bus0",
        "voltage_bus1",
        "country",
        "geometry",
        "bounds",
        "bus_0_coors",
        "bus_1_coors",
        "bus0_lon",
        "bus0_lat",
        "bus1_lon",
        "bus1_lat",
    ]
    df_transformers_reference = pd.DataFrame(
        data_transformers_reference, columns=column_transformers_reference
    ).set_index("transformer_id")

    file_path = get_path(tmpdir, "transformers_exercise.csv")
    df_transformers_input.to_csv(file_path)

    df_transformers_output = _load_transformers_from_osm(file_path)

    df_transformers_comparison = df_transformers_output.compare(
        df_transformers_reference
    )
    pathlib.Path.unlink(file_path)
    assert df_transformers_comparison.empty


def test_load_converters_from_osm(tmpdir):
    data_converters_input = [
        [
            0,
            "convert_20_41",
            "41",
            "42",
            False,
            False,
            "US",
            "LINESTRING(-122.3787 37.6821, -122.3777 37.6831)",
        ],
    ]
    column_converters_input = [
        "index",
        "converter_id",
        "bus0",
        "bus1",
        "underground",
        "under_construction",
        "country",
        "geometry",
    ]
    df_converters_input = pd.DataFrame(
        data_converters_input, columns=column_converters_input
    )

    data_converters_reference = [
        [
            "convert_20_41",
            0,
            0,
            "41",
            "42",
            False,
            False,
            "US",
            "LINESTRING(-122.3787 37.6821, -122.3777 37.6831)",
            "B2B",
            True,
        ],
    ]
    column_converters_reference = [
        "converter_id",
        "Unnamed: 0",
        "index",
        "bus0",
        "bus1",
        "underground",
        "under_construction",
        "country",
        "geometry",
        "carrier",
        "dc",
    ]
    df_converters_reference = pd.DataFrame(
        data_converters_reference, columns=column_converters_reference
    ).set_index("converter_id")

    file_path = get_path(tmpdir, "converters_exercise.csv")
    df_converters_input.to_csv(file_path)

    df_converters_output = _load_converters_from_osm(file_path)

    df_converters_comparison = df_converters_output.compare(df_converters_reference)
    pathlib.Path.unlink(file_path)
    assert df_converters_comparison.empty


def test_get_linetypes_config():
    output_dict_ac = _get_linetypes_config(lines_dict["ac_types"], voltages_list)
    output_dict_dc = _get_linetypes_config(lines_dict["dc_types"], voltages_list)
    reference_dict_ac = {
        132.0: "243-AL1/39-ST1A 20.0",
        220.0: "Al/St 240/40 2-bundle 220.0",
        300.0: "Al/St 240/40 3-bundle 300.0",
        380.0: "Al/St 240/40 4-bundle 380.0",
        500.0: "Al/St 240/40 4-bundle 380.0",
        750.0: "Al/St 560/50 4-bundle 750.0",
    }
    reference_dict_dc = {
        500.0: "HVDC XLPE 1000",
    }
    assert output_dict_ac == reference_dict_ac
    assert output_dict_dc == reference_dict_dc
