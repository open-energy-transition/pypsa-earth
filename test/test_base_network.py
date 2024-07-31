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

from _helpers import get_path
from base_network import (
    _get_linetype_by_voltage,
    _get_linetypes_config,
    _load_buses_from_osm,
    _load_converters_from_osm,
    _load_lines_from_osm,
    _load_transformers_from_osm,
    _set_electrical_parameters_converters,
    _set_electrical_parameters_dc_lines,
    _set_electrical_parameters_lines,
    _set_electrical_parameters_links,
    _set_electrical_parameters_transformers,
    get_country,
)

path_cwd = pathlib.Path.cwd()

# Common references

# ---> lines

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
    [
        "204361287-1_1",
        0.0,
        "line",
        178658,
        "111",
        "0",
        3.0,
        118723.89434240988,
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

data_lines_ac_reference = [
    [
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
        "AC",
        "243-AL1/39-ST1A 20.0",
        0.7,
    ],
]

data_lines_dc_reference = [
    [
        0.0,
        "line",
        178.658,
        "111",
        "0",
        3.0,
        118.72389434240988,
        False,
        False,
        True,
        "BJ",
        "LINESTRING (2.6594 10.2042, 2.6594451 10.2042341)",
        "MULTIPOINT ((2.6594 10.2042), (2.5914 9.3321))",
        "POINT (2.6594 10.2042)",
        "POINT (2.5914 9.3321)",
        2.6594,
        10.2042,
        2.5914,
        9.3321,
        "DC",
        "HVDC XLPE 1000",
        0.7,
    ],
]

column_lines_ac_dc_reference = [
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
    "carrier",
    "type",
    "s_max_pu",
]

lines_ac_reference = pd.DataFrame(
    data_lines_ac_reference, columns=column_lines_ac_dc_reference
).set_index("tag_frequency")

lines_dc_reference = pd.DataFrame(
    data_lines_dc_reference, columns=column_lines_ac_dc_reference
).set_index("tag_frequency")

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

# ---> links

links_dict = {
    "p_max_pu": 2.1,
    "p_nom_max": np.inf,
    "under_construction": "zero",
}

# ---> transformers

transformers_dict = {
    "x": 0.1,
    "s_nom": 2000.0,
    "type": "",
}

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

# ---> converters

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

# ---> voltages

voltages_list = [132.0, 220.0, 300.0, 380.0, 500.0, 750.0]


def test_get_country():
    """
    Verify what returned by get_country()
    """
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
    """
    Verify what returned by _load_buses_from_osm.
    """
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
    """
    Verify what returned by _load_lines_from_osm.
    """
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
        [
            "204361287-1_1",
            0.0,
            "line",
            178.658,
            "111",
            "0",
            3.0,
            118.72389434240988,
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
    """
    Verify what returned by _load_transformers_from_osm.
    """
    file_path = get_path(tmpdir, "transformers_exercise.csv")
    df_transformers_input.to_csv(file_path)

    df_transformers_output = _load_transformers_from_osm(file_path)

    df_transformers_comparison = df_transformers_output.compare(
        df_transformers_reference
    )
    pathlib.Path.unlink(file_path)
    assert df_transformers_comparison.empty


def test_load_converters_from_osm(tmpdir):
    """
    Verify what returned by _load_converters_from_osm.
    """
    file_path = get_path(tmpdir, "converters_exercise.csv")
    df_converters_input.to_csv(file_path)

    df_converters_output = _load_converters_from_osm(file_path)

    df_converters_comparison = df_converters_output.compare(df_converters_reference)
    pathlib.Path.unlink(file_path)
    assert df_converters_comparison.empty


def test_get_linetypes_config():
    """
    Verify what returned by _get_linetypes_config.
    """
    output_dict_ac = _get_linetypes_config(lines_dict["ac_types"], voltages_list)
    output_dict_dc = _get_linetypes_config(lines_dict["dc_types"], voltages_list)
    assert output_dict_ac == lines_dict["ac_types"]
    assert output_dict_dc == lines_dict["dc_types"]


def test_get_linetype_by_voltage():
    """
    Verify what returned by _get_linetype_by_voltage.
    """
    v_nom_list = [
        50.0,
        101.0,
        180.0,
        210.0,
        220.0,
        225.0,
        285.0,
        300.0,
        333.0,
        390.0,
        600.0,
        750.0,
        800.0,
    ]

    line_type_list = []

    for v_nom in v_nom_list:
        line_type_list.append(_get_linetype_by_voltage(v_nom, lines_dict["ac_types"]))

    assert line_type_list == [
        "243-AL1/39-ST1A 20.0",
        "243-AL1/39-ST1A 20.0",
        "Al/St 240/40 2-bundle 220.0",
        "Al/St 240/40 2-bundle 220.0",
        "Al/St 240/40 2-bundle 220.0",
        "Al/St 240/40 2-bundle 220.0",
        "Al/St 240/40 3-bundle 300.0",
        "Al/St 240/40 3-bundle 300.0",
        "Al/St 240/40 3-bundle 300.0",
        "Al/St 240/40 4-bundle 380.0",
        "Al/St 240/40 4-bundle 380.0",
        "Al/St 560/50 4-bundle 750.0",
        "Al/St 560/50 4-bundle 750.0",
    ]


def test_set_electrical_parameters_lines(tmpdir):
    """
    Verify what returned by _set_electrical_parameters_lines.
    """
    file_path = get_path(tmpdir, "lines_exercise.csv")
    df_lines_input.to_csv(file_path)
    df_lines_output = _load_lines_from_osm(file_path).reset_index(drop=True)
    df_lines_output_ac = df_lines_output[
        df_lines_output.tag_frequency.astype(float) != 0
    ].copy()
    df_lines_output_dc = df_lines_output[
        df_lines_output.tag_frequency.astype(float) == 0
    ].copy()
    lines_ac = _set_electrical_parameters_lines(
        lines_dict, voltages_list, df_lines_output_ac
    ).set_index("tag_frequency")
    lines_dc = _set_electrical_parameters_dc_lines(
        lines_dict, voltages_list, df_lines_output_dc
    ).set_index("tag_frequency")

    df_lines_ac_comparison = lines_ac.compare(lines_ac_reference)
    df_lines_dc_comparison = lines_dc.compare(lines_dc_reference)

    pathlib.Path.unlink(file_path)

    assert df_lines_ac_comparison.empty
    assert df_lines_dc_comparison.empty


def test_set_electrical_parameters_links(tmpdir):
    """
    Verify what returned by _set_electrical_parameters_links.
    """
    file_path = get_path(tmpdir, "lines_exercise.csv")
    df_lines_input.to_csv(file_path)
    df_lines_output = _load_lines_from_osm(file_path).reset_index(drop=True)
    df_lines_output_dc = df_lines_output[
        df_lines_output.tag_frequency.astype(float) == 0
    ].copy()
    lines_dc = _set_electrical_parameters_dc_lines(
        lines_dict, voltages_list, df_lines_output_dc
    )

    new_lines_dc = _set_electrical_parameters_links(links_dict, lines_dc).set_index(
        "tag_frequency"
    )

    new_lines_dc_reference = lines_dc_reference.copy(deep=True)
    new_lines_dc_reference["p_max_pu"] = links_dict["p_max_pu"]
    new_lines_dc_reference["p_min_pu"] = -links_dict["p_max_pu"]
    pathlib.Path.unlink(file_path)
    df_comparison = new_lines_dc.compare(new_lines_dc_reference)
    assert df_comparison.empty


def test_set_electrical_parameters_transformers(tmpdir):
    """
    Verify what returned by _set_electrical_parameters_transformers.
    """
    file_path = get_path(tmpdir, "transformers_exercise.csv")
    df_transformers_input.to_csv(file_path)
    df_transformers_output = _load_transformers_from_osm(file_path)

    df_transformers_parameters = _set_electrical_parameters_transformers(
        transformers_dict, df_transformers_output
    )

    df_transformers_parameters_reference = df_transformers_reference.copy(deep=True)
    df_transformers_parameters_reference["x"] = transformers_dict["x"]
    df_transformers_parameters_reference["s_nom"] = transformers_dict["s_nom"]
    df_transformers_parameters_reference["type"] = transformers_dict["type"]
    pathlib.Path.unlink(file_path)
    df_comparison = df_transformers_parameters.compare(
        df_transformers_parameters_reference
    )
    assert df_comparison.empty


def test_set_electrical_parameters_converters(tmpdir):
    """
    Verify what returned by _set_electrical_parameters_converters.
    """
    file_path = get_path(tmpdir, "converters_exercise.csv")
    df_converters_input.to_csv(file_path)

    df_converters_output = _load_converters_from_osm(file_path)

    df_converters_parameters = _set_electrical_parameters_converters(
        links_dict, df_converters_output
    )

    df_converters_parameters.to_csv(get_path(path_cwd, "converters_output.csv"))

    df_converters_parameters_reference = df_converters_reference.copy(deep=True)
    df_converters_parameters_reference["p_max_pu"] = links_dict["p_max_pu"]
    df_converters_parameters_reference["p_min_pu"] = -links_dict["p_max_pu"]
    df_converters_parameters_reference["p_nom"] = 2000
    df_converters_parameters_reference["under_construction"] = False
    df_converters_parameters_reference["underground"] = False

    pathlib.Path.unlink(file_path)
    df_comparison = df_converters_parameters.compare(df_converters_parameters_reference)
    assert df_comparison.empty
