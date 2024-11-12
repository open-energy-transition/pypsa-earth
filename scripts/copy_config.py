# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later
import pathlib
from shutil import copy

from _helpers import BASE_DIR, mock_snakemake

files_to_copy = {
    pathlib.Path(BASE_DIR, "./config.yaml"): "config.yaml",
    pathlib.Path(BASE_DIR, "./Snakefile"): "Snakefile",
    pathlib.Path(BASE_DIR, "./scripts/solve_network.py"): "solve_network.py",
    pathlib.Path(BASE_DIR, "./scripts/prepare_sector_network.py"): "prepare_sector_network.py",
}

if __name__ == "__main__":
    if "snakemake" not in globals():
        snakemake = mock_snakemake("copy_config")

    directory = snakemake.output["folder"]
    for f, name in files_to_copy.items():
        copy(f, directory + "/" + name)
