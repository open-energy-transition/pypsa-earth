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
from base_network import _load_buses_from_osm, get_country

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

    data_list_input = [
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
    column_list_input = [
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
    df_exercise_input = pd.DataFrame(data_list_input, columns=column_list_input)

    data_list_reference = [
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
    column_list_reference = [
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
    df_exercise_reference = pd.DataFrame(
        data_list_reference, columns=column_list_reference
    ).set_index("bus_id")

    file_path = get_path(path_cwd, "buses_exercise.csv")
    df_exercise_input.to_csv(file_path)

    df_exercise_output = _load_buses_from_osm(file_path)

    df_comparison = df_exercise_output.compare(df_exercise_reference)

    pathlib.Path.unlink(file_path)

    assert df_comparison.empty
