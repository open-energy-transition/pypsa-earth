# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-

import pathlib
import sys

sys.path.append("./scripts")

from build_shapes import get_countries_shapes, get_gadm_shapes, save_to_geojson

path_cwd = str(pathlib.Path.cwd())


def test_get_countries_shape(get_config_dict):
    """
    Verify what is returned by countries.
    """
    config_dict = get_config_dict

    countries_list = ["XK"]
    geo_crs = config_dict["crs"]["geo_crs"]

    update = config_dict["build_shape_options"]["update_file"]
    out_logging = config_dict["build_shape_options"]["out_logging"]
    contended_flag = config_dict["build_shape_options"]["contended_flag"]
    file_prefix = config_dict["build_shape_options"]["gadm_file_prefix"]
    gadm_url_prefix = config_dict["build_shape_options"]["gadm_url_prefix"]
    gadm_input_file_args = ["data", "gadm"]

    country_shapes_df = get_countries_shapes(
        countries_list,
        geo_crs,
        file_prefix,
        gadm_url_prefix,
        gadm_input_file_args,
        contended_flag,
        update,
        out_logging,
    )

    assert country_shapes_df.shape == (1,)
    assert country_shapes_df.index.unique().tolist() == ["XK"]


def test_gadm(get_config_dict):
    """
    Verify what is returned by gadm.
    """
    config_dict = get_config_dict

    mem_mb = 3096

    countries_list = ["XK"]
    geo_crs = config_dict["crs"]["geo_crs"]

    layer_id = config_dict["build_shape_options"]["gadm_layer_id"]
    update = config_dict["build_shape_options"]["update_file"]
    out_logging = config_dict["build_shape_options"]["out_logging"]
    year = config_dict["build_shape_options"]["year"]
    nprocesses = config_dict["build_shape_options"]["nprocesses"]
    contended_flag = config_dict["build_shape_options"]["contended_flag"]
    worldpop_method = config_dict["build_shape_options"]["worldpop_method"]
    gdp_method = config_dict["build_shape_options"]["gdp_method"]
    file_prefix = config_dict["build_shape_options"]["gadm_file_prefix"]
    gadm_url_prefix = config_dict["build_shape_options"]["gadm_url_prefix"]
    gadm_input_file_args = ["data", "gadm"]

    gadm_shapes_df = get_gadm_shapes(
        worldpop_method,
        gdp_method,
        countries_list,
        geo_crs,
        file_prefix,
        gadm_url_prefix,
        gadm_input_file_args,
        contended_flag,
        mem_mb,
        layer_id,
        update,
        out_logging,
        year,
        nprocesses=nprocesses,
    )

    assert gadm_shapes_df.shape == (7, 4)
    assert gadm_shapes_df.index.unique().tolist() == [f"XK.{x}_1" for x in range(1, 8)]
    assert gadm_shapes_df.loc["XK.1_1"]["pop"] == 207473.70381259918
    assert gadm_shapes_df.loc["XK.7_1"]["gdp"] == 2385293056.0
