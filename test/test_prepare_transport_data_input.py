# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-


import sys

sys.path.append("./scripts")

from prepare_transport_data_input import download_co2_emissions, download_number_of_vehicles

def test_download_co2_emissions():
    CO2_emissions_csv = download_co2_emissions()
    assert CO2_emissions_csv.shape == (231, 6)


def test_download_number_of_vehicles():
    vehicles_csv = download_number_of_vehicles()
    assert vehicles_csv.shape == (162, 5)
