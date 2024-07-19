# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-

import sys

import numpy as np
import pandas as pd

sys.path.append("./scripts")

from base_network import get_country

data_list = [['"country"=>"NG"'], ['"country"=>"CH"'], ['"country"=>"AU"']]
df_exercise_with_tags = pd.DataFrame(data_list, columns=["tags"])
df_exercise_no_tags = pd.DataFrame(data_list, columns=["other"])


def test_get_country():

    series_with_tags = get_country(df_exercise_with_tags)
    reference_series_with_tags = pd.Series(["NG", "CH", "AU"])
    comparison_series_with_tags = series_with_tags.compare(reference_series_with_tags)

    series_no_tags = get_country(df_exercise_no_tags)
    reference_series_no_tags = pd.Series([np.nan, np.nan, np.nan])
    comparison_series_no_tags = series_no_tags.compare(reference_series_no_tags)

    assert comparison_series_with_tags.size == 0
    assert comparison_series_no_tags.size == 0
