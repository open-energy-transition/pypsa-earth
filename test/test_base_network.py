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
from base_network import _load_buses_from_osm, _load_lines_from_osm, get_country

path_cwd = str(pathlib.Path.cwd())


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


def test_load_buses_from_osm():

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
        [
            1,
            1,
            161000,
            False,
            "substation",
            False,
            "transmission",
            0.0,
            2.648,
            6.7394,
            "BJ",
            "POINT (2.648 6.7394)",
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
        [
            "1",
            161.0,
            "substation",
            False,
            "transmission",
            0.0,
            2.648,
            6.7394,
            "BJ",
            "POINT (2.648 6.7394)",
            True,
            "AC",
            2.648,
            6.7394,
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

    file_path = get_path(path_cwd, "buses_exercise.csv")
    df_buses_input.to_csv(file_path)

    df_buses_output = _load_buses_from_osm(file_path)

    df_buses_comparison = df_buses_output.compare(df_buses_reference)

    pathlib.Path.unlink(file_path)

    assert df_buses_comparison.empty


def test_load_lines_from_osm():
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
            "224381271-1_0",
            50.0,
            "line",
            330000,
            "11",
            "2",
            3.0,
            71555.72699869394,
            False,
            False,
            False,
            "BJ",
            "LINESTRING (3.2467 6.6037, 3.2465731 6.602494900000034)",
            "MULTIPOINT ((3.2467 6.6037), (2.649 6.7404))",
            "POINT (3.2467 6.6037)",
            "POINT (2.649 6.7404)",
            3.2467,
            6.6037,
            2.649,
            6.7404,
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
        [
            "224381271-1_0",
            50.0,
            "line",
            330.0,
            "11",
            "2",
            3.0,
            71.55572699869394,
            False,
            False,
            False,
            "BJ",
            "LINESTRING (3.2467 6.6037, 3.2465731 6.602494900000034)",
            "MULTIPOINT ((3.2467 6.6037), (2.649 6.7404))",
            "POINT (3.2467 6.6037)",
            "POINT (2.649 6.7404)",
            3.2467,
            6.6037,
            2.649,
            6.7404,
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

    file_path = get_path(path_cwd, "lines_exercise.csv")
    df_lines_input.to_csv(file_path)

    df_lines_output = _load_lines_from_osm(file_path)

    df_lines_comparison = df_lines_output.compare(df_lines_reference)
    pathlib.Path.unlink(file_path)
    assert df_lines_comparison.empty
