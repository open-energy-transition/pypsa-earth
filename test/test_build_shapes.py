# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-

import pathlib
import sys

import geopandas as gpd
import numpy as np

sys.path.append("./scripts")

from build_shapes import (
    _simplify_polys,
    country_cover,
    download_WorldPop_standard,
    get_countries_shapes,
    get_gadm_shapes,
    save_to_geojson,
)

path_cwd = str(pathlib.Path.cwd())


def test_simplify_polys(get_config_dict):
    """
    Verify what is returned by _simplify_polys.
    """

    config_dict = get_config_dict

    countries_list = ["NG"]
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

    simplified_poly = _simplify_polys(country_shapes_df)

    simplified_poly_df = gpd.GeoDataFrame(
        geometry=[
            country_cover(
                simplified_poly, eez_shapes=None, out_logging=False, distance=0.02
            )
        ]
    )
    simplified_poly_df["area"] = simplified_poly_df.area
    simplified_poly_df["centroid"] = simplified_poly_df.centroid
    assert np.round(simplified_poly_df.area[0], 6) == 75.750018
    assert (
        str(simplified_poly_df.centroid[0])
        == "POINT (8.100522482086877 9.591585359563023)"
    )


def test_get_countries_shapes(get_config_dict):
    """
    Verify what is returned by get_countries_shapes.
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


def test_country_cover(get_config_dict):
    """
    Verify what is returned by country_cover.
    """

    config_dict = get_config_dict

    countries_list = ["NG"]
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

    africa_shapes_df = gpd.GeoDataFrame(
        geometry=[
            country_cover(
                country_shapes_df, eez_shapes=None, out_logging=False, distance=0.02
            )
        ]
    )
    africa_shapes_df["area"] = africa_shapes_df.area
    africa_shapes_df["centroid"] = africa_shapes_df.centroid
    assert np.round(africa_shapes_df.area[0], 6) == 75.750104
    assert (
        str(africa_shapes_df.centroid[0])
        == "POINT (8.100519548407405 9.59158035236806)"
    )


def test_download_world_pop_standard(get_config_dict):
    """
    Verify what is returned by download_WorldPop_standard.
    """

    config_dict = get_config_dict
    update_val = config_dict["build_shape_options"]["update_file"]
    out_logging_val = config_dict["build_shape_options"]["out_logging"]

    world_pop_input_file, world_pop_file_name = download_WorldPop_standard(
        "NG",
        year=2020,
        update=update_val,
        out_logging=out_logging_val,
        size_min=300,
    )
    assert world_pop_file_name == "nga_ppp_2020_UNadj_constrained.tif"


def test_get_gadm_shapes(get_config_dict):
    """
    Verify what is returned by get_gadm_shapes.
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
