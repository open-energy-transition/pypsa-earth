# -*- coding: utf-8 -*-
"""Builds a file including technology cost and efficiency data for industrial heating.
The data is separate from other technology costs because they are specifically compiled
to provide technological competition for Enhanced Geothermal Systems (EGS) in the north
American context.
"""

import logging

logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd

from _helpers import configure_logging


if __name__ == '__main__':
    configure_logging(snakemake)

    techdata = pd.read_csv(snakemake.input['costs'], index_col=[0,1])

    idx = pd.IndexSlice

    print(techdata)

    manual_costs = pd.DataFrame(
        columns=techdata.columns,
        index=pd.MultiIndex.from_tuples((), names=techdata.index.names)
    )

    # add molten salt storage costs
    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'investment'], 'value'] = 41_600
    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'investment'], 'unit'] = '$/MWhth'
    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'investment'], 'source'] = 'Viswanathan_2022 - Energy Storage Grand Challenge Cost and Performance Assessment 2022'
    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'investment'], 'further description'] = 'Salt Media + Storage Tank, for a system with 1000MWh capacity'

    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'FOM'], 'value'] = 1.5
    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'FOM'], 'unit'] = '%'
    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'FOM'], 'source'] = 'Viswanathan_2022 - Energy Storage Grand Challenge Cost and Performance Assessment 2022'
    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'FOM'], 'further description'] = 'Salt Media + Storage Tank, for a system with 1000MWh capacity'

    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'lifetime'], 'value'] = 35
    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'lifetime'], 'unit'] = 'years'
    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'lifetime'], 'source'] = 'Viswanathan_2022 - Energy Storage Grand Challenge Cost and Performance Assessment 2022'
    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'lifetime'], 'further description'] = 'Taken from a typical range of 30-50 years'

    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'efficiency'], 'value'] = 99.95
    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'efficiency'], 'unit'] = '%/hour'
    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'efficiency'], 'source'] = 'Viswanathan_2022 - Energy Storage Grand Challenge Cost and Performance Assessment 2022'
    manual_costs.loc[idx['Low-Temp Molten Salt Store', 'efficiency'], 'further description'] = 'Typical value assumed for molten salt storage with a daily thermal loss of 1-2% per day'


    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'investment'], 'value'] = 30_000
    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'investment'], 'unit'] = '$/MWth'
    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'investment'], 'source'] = 'Viswanathan_2022 - Energy Storage Grand Challenge Cost and Performance Assessment 2022'
    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'investment'], 'further description'] = 'Assumes output is heat only, and does not need conversion to AC'

    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'FOM'], 'value'] = 1.
    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'FOM'], 'unit'] = '%'
    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'FOM'], 'source'] = 'Viswanathan_2022 - Energy Storage Grand Challenge Cost and Performance Assessment 2022'
    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'FOM'], 'further description'] = 'Assumes output is heat only, and does not need conversion to AC'

    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'lifetime'], 'value'] = 35
    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'lifetime'], 'unit'] = 'years'
    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'lifetime'], 'source'] = 'Viswanathan_2022 - Energy Storage Grand Challenge Cost and Performance Assessment 2022'
    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'lifetime'], 'further description'] = 'Taken from a typical range of 30-50 years'

    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'efficiency'], 'value'] = 98.
    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'efficiency'], 'unit'] = '%'
    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'efficiency'], 'source'] = 'Viswanathan_2022 - Energy Storage Grand Challenge Cost and Performance Assessment 2022'
    manual_costs.loc[idx['Low-Temp Molten Salt Discharger', 'efficiency'], 'further description'] = 'Typical value for heat exchangers'

    # add SHIP costs
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'investment'], 'value'] = 350_000
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'investment'], 'unit'] = '$/MWth'
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'investment'], 'source'] = 'IEA-SHC-Task64-SubtaskE-D.E2-D.E3.pdf'
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'investment'], 'further description'] = 'For temperatures between 100-400C; Assumes Solar Collectors Coupled with Thermal Storage; Value reverse-engineered from LCOH; kWth is nameplate capacity'
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'investment'], 'currency_year'] = 2022.

    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'FOM'], 'value'] = 2
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'FOM'], 'unit'] = '%'
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'FOM'], 'source'] = 'IEA-SHC-Task64-SubtaskE-D.E2-D.E3.pdf'
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'FOM'], 'further description'] = 'Typical value for solar thermal'
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'FOM'], 'currency_year'] = 2022.

    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'efficiency-mexico'], 'value'] = 30
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'efficiency-mexico'], 'unit'] = '%'
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'efficiency-mexico'], 'source'] = 'IEA-SHC-Task64-SubtaskE-D.E2-D.E3.pdf'
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'efficiency-mexico'], 'further description'] = 'Data point number one for capacity factor in Mexico. Should be used to interpolate capacity factor for other locations' 
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'efficiency-mexico'], 'currency_year'] = 2022.

    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'efficiency-germany'], 'value'] = 20
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'efficiency-germany'], 'unit'] = '%'
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'efficiency-germany'], 'source'] = 'IEA-SHC-Task64-SubtaskE-D.E2-D.E3.pdf'
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'efficiency-germany'], 'further description'] = 'Data point number two for capacity factor in Germany/Austria. Should be used to interpolate capacity factor for other locations' 
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'efficiency-germany'], 'currency_year'] = 2022.

    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'lifetime'], 'value'] = 25
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'lifetime'], 'unit'] = 'years'
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'lifetime'], 'source'] = 'IEA-SHC-Task64-SubtaskE-D.E2-D.E3.pdf'
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'lifetime'], 'further description'] = 'Typical value for solar thermal'
    manual_costs.loc[idx['Solar Heat For Industrial Processes', 'lifetime'], 'currency_year'] = 2022.


    # add heat pump costs
    manual_costs = pd.concat([
        manual_costs,
        techdata.loc[
            idx[['industrial heat pump high temperature', 'industrial heat pump medium temperature'],:]
        ]
        ])

    manual_costs.loc[idx['Biogas', 'fuel cost'], 'value'] = 79.
    manual_costs.loc[idx['Biogas', 'fuel cost'], 'unit'] = '$/MWh'
    manual_costs.loc[idx['Biogas', 'fuel cost'], 'source'] = 'IEA: https://www.iea.org/reports/outlook-for-biogas-and-biomethane-prospects-for-organic-growth/sustainable-supply-potential-and-costs'
    manual_costs.loc[idx['Biogas', 'fuel cost'], 'further description'] = 'From regionalised supply curve for North America, assuming the higher end will dictate the price.'

    print(manual_costs)



