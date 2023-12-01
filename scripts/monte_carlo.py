# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
"""
Prepares network files with monte-carlo parameter sweeps for solving process.

Relevant Settings
-----------------

.. code:: yaml

    monte_carlo:
    options:
        add_to_snakefile: false
        # Uniform: https://chaospy.readthedocs.io/en/master/api/chaospy.Uniform.html
        # Normal: https://chaospy.readthedocs.io/en/master/api/chaospy.Normal.html
        # LogNormal: https://chaospy.readthedocs.io/en/master/api/chaospy.LogNormal.html
        # Triange: https://chaospy.readthedocs.io/en/master/api/chaospy.Triangle.html
        # Beta: https://chaospy.readthedocs.io/en/master/api/chaospy.Beta.html
        # Gamma: https://chaospy.readthedocs.io/en/master/api/chaospy.Gamma.html
        distribution: "Uniform" # "Uniform", "Normal", "LogNormal", "Triangle", "Beta", "Gamma"
        # [mean, std] for Normal and LogNormal
        # [lower_bound, upper_bound] for Uniform
        # [lower_bound, midpoint, upper_bound] for Triangle 
        # [alpha, beta] for Beta
        # [shape, scale] for Gamma
        distribution_params: [0,1]
        samples: 4 # number of optimizations. Note that number of samples when using scipy has to be the square of a prime number
        sampling_strategy: "scipy"  # "pydoe2", "chaospy", "scipy", packages that are supported
    pypsa_standard:
        # User can add here flexibly more features for the Monte-Carlo sampling.
        # Given as "key: value" format
        # Key: add below the pypsa object for the monte_carlo sampling, "network" is only allowed for filtering!
        # Value: currently supported format [l_bound, u_bound] or empty [], represent multiplication factors for the object
        loads_t.p_set: [0.9, 1.1]
        # generators_t.p_max_pu.loc[:, n.generators.carrier == "wind"]: [0.9, 1.1]
        # generators_t.p_max_pu.loc[:, n.generators.carrier == "solar"]: [0.9, 1.1]

.. seealso::
    Documentation of the configuration file ``config.yaml`` at :ref:`_monte_cf`

Inputs
------
- ``networks/elec_s_10_ec_lcopt_Co2L-24H.nc``

Outputs
-------
- ``networks/elec_s_10_ec_lcopt_Co2L-24H_{unc}.nc``
e.g.    networks/elec_s_10_ec_lcopt_Co2L-24H_m0.nc
        networks/elec_s_10_ec_lcopt_Co2L-24H_m1.nc
        ...

Description
-----------
PyPSA-Earth is deterministic which means that a set of inputs give a set of outputs.
Parameter sweeps can help to explore the uncertainty of the outputs cause by parameter changes.
Many are familiar with the classical "sensitivity analysis" that can be applied by varying the
input of only one feature, while exploring its outputs changes. Here implemented is a
"global sensitivity analysis" that can help to explore the multi-dimensional uncertainty space
when more than one feature are changed at the same time.

To do so, the scripts is separated in two building blocks: One creates the experimental design,
the other, modifies and outputs the network file. Building the experimental design is currently
supported by the packages pyDOE2, chaospy and scipy. This should give users the freedom to
explore alternative approaches. The orthogonal latin hypercube sampling is thereby found as most
performant, hence, implemented here. Sampling the multi-dimensional uncertainty space is relatively
easy. It only requires two things: The number of *samples* (e.g. PyPSA networks) and *features* (e.g.
load or solar timeseries). This results in an experimental design of the dimension (samples X features).

Additionally, upper and lower bounds *per feature* need to be provided such that the experimental
design can be scaled accordingly. Currently the user can define uncertainty ranges e.g. bounds,
for all PyPSA objects that are `int` or `float`. Boolean values could be used but require testing.
The experimental design `lhs_scaled` (dimension: sample X features) is then used to modify the PyPSA
networks. Thereby, this script creates samples x amount of networks. The iterators comes from the
wildcard {unc}, which is described in the config.yaml and created in the Snakefile as a range from
0 to (total number of) SAMPLES.
"""
import logging
import os

import chaospy
import numpy as np
import pandas as pd
import pypsa
from _helpers import configure_logging, create_logger
from pyDOE2 import lhs
from scipy.stats import qmc
from solve_network import *

logger = create_logger(__name__)


def monte_carlo_sampling_pydoe2(
    N_FEATURES,
    SAMPLES,
    DISTRIBUTION,
    DISTRIBUTION_PARAMS,
    criterion=None,
    iteration=None,
    random_state=42,
    correlation_matrix=None,
):
    """
    Creates Latin Hypercube Sample (LHS) implementation from PyDOE2 with
    various options. Additionally all "corners" are simulated.

    Adapted from Disspaset: https://github.com/energy-modelling-toolkit/Dispa-SET/blob/master/scripts/build_and_run_hypercube.py
    Documentation on PyDOE2: https://github.com/clicumu/pyDOE2 (fixes latin_cube errors)
    """

    # Generate a Nfeatures-dimensional latin hypercube varying between 0 and 1:
    lh = lhs(
        N_FEATURES,
        samples=SAMPLES,
        criterion=criterion,
        iterations=iteration,
        random_state=random_state,
        correlation_matrix=correlation_matrix,
    )

    lh = rescale_distribution(lh, DISTRIBUTION, DISTRIBUTION_PARAMS)
    discrepancy = qmc.discrepancy(lh)
    logger.info("Discrepancy is:", discrepancy,
          " more details in function documentation.")

    return lh


def monte_carlo_sampling_chaospy(
    N_FEATURES,
    SAMPLES,
    DISTRIBUTION,
    DISTRIBUTION_PARAMS,
    rule="latin_hypercube",
    seed=42,
):
    """
    Creates Latin Hypercube Sample (LHS) implementation from chaospy.

    Documentation on Chaospy: https://github.com/clicumu/pyDOE2 (fixes latin_cube errors)
    Documentation on Chaospy latin-hyper cube (quasi-Monte Carlo method): https://chaospy.readthedocs.io/en/master/user_guide/fundamentals/quasi_random_samples.html#Quasi-random-samples

    """
    import chaospy
    from scipy.stats import qmc
    from sklearn.preprocessing import MinMaxScaler

    params = tuple(DISTRIBUTION_PARAMS)
    # generate a Nfeatures-dimensional latin hypercube varying between 0 and 1:
    N_FEATURES = f"chaospy.{DISTRIBUTION}{params}, " * N_FEATURES
    cube = eval(
        f"chaospy.J({N_FEATURES})"
    )  # writes Nfeatures times the chaospy.uniform... command)
    lh = cube.sample(SAMPLES, rule=rule, seed=seed).T

    # to check the discrepancy of the samples, the values needs to be from 0-1
    mm = MinMaxScaler(feature_range=(0, 1), clip=True)
    lh = mm.fit_transform(lh)

    discrepancy = qmc.discrepancy(lh)
    logger.info("Discrepancy is:", discrepancy,
          " more details in function documentation.")

    return lh


def monte_carlo_sampling_scipy(
    N_FEATURES,
    SAMPLES,
    DISTRIBUTION,
    DISTRIBUTION_PARAMS,
    centered=False,
    strength=2,
    optimization=None,
    seed=42,
):
    """
    Creates Latin Hypercube Sample (LHS) implementation from SciPy with various options:
    - Center the point within the multi-dimensional grid, centered=True
    - optimization scheme, optimization="random-cd"
    - strength=1, classical LHS
    - strength=2, performant orthogonal LHS, requires the sample to be a prime or square of a prime e.g. sqr(121)=11

    Options could be combined to produce an optimized centered orthogonal array
    based LHS. After optimization, the result would not be guaranteed to be of strength 2.

    Documentation for Quasi-Monte Carlo approaches: https://docs.scipy.org/doc/scipy/reference/stats.qmc.html
    Documentation for Latin Hypercube: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.LatinHypercube.html#scipy.stats.qmc.LatinHypercube
    Orthogonal LHS is better than basic LHS: https://github.com/scipy/scipy/pull/14546/files, https://en.wikipedia.org/wiki/Latin_hypercube_sampling
    """
    from scipy.stats import qmc

    sampler = qmc.LatinHypercube(
        d=N_FEATURES,
        centered=centered,
        strength=strength,
        optimization=optimization,
        seed=seed,
    )

    lh = sampler.random(n=SAMPLES)

    lh = rescale_distribution(lh, DISTRIBUTION, DISTRIBUTION_PARAMS)
    discrepancy = qmc.discrepancy(lh)
    logger.info("Discrepancy is:", discrepancy,
          " more details in function documentation.")

    return lh


def rescale_distribution(latin_hypercube: np.array, distribution: str,
                         distribution_params: list):
    """
    Rescales a Latin hypercube sampling (LHS) using specified distribution parameters.

    Parameters:
    - latin_hypercube (np.array): The Latin hypercube sampling to be rescaled.
    - distribution (str): The target distribution for rescaling. Supported options: 
                          "Uniform", "Normal", "LogNormal", "Triangle", "Beta", "Gamma".
    - distribution_params (list): Parameters specific to the chosen distribution. 
                                  For example, for Normal distribution, it should be [mean, std].

    Returns:
    - np.array: Rescaled Latin hypercube sampling.

    Note:
    - The function supports rescaling for Uniform, Normal, LogNormal, Triangle, Beta, and Gamma distributions.
    - The rescaled samples will have values in the range [0, 1].
    """
    from scipy.stats import norm, lognorm, beta, gamma, triang
    from sklearn.preprocessing import MinMaxScaler

    if distribution == "Uniform":
        pass
    elif distribution == "Normal":
        mean, std = distribution_params
        latin_hypercube = norm.ppf(latin_hypercube, mean, std)
    elif distribution == "LogNormal":
        mean, std = distribution_params
        latin_hypercube = lognorm.ppf(latin_hypercube, s=0.90)
    elif distribution == "Triangle":
        tri_mean = np.mean(distribution_params)
        latin_hypercube = triang.ppf(latin_hypercube, tri_mean)
    elif distribution == "Beta":
        a, b = distribution_params
        latin_hypercube = beta.ppf(latin_hypercube, a, b)
    elif distribution == "Gamma":
        shape, scale = distribution_params
        latin_hypercube = gamma.ppf(latin_hypercube, shape, scale)

    # samples space needs to be from 0 to 1
    mm = MinMaxScaler(feature_range=(0, 1), clip=True)
    latin_hypercube = mm.fit_transform(latin_hypercube)

    return latin_hypercube


def validate_parameters(
    sampling_strategy: str, samples: int, distribution: str, distribution_params: list
) -> None:
    """
    Validates the parameters for a given probability distribution.
    Inputs from user through the config file needs to be validated before proceeding to perform monte-carlo simulations.

    Parameters:
    - sampling_strategy: str
        The chosen sampling strategy from chaospy, scipy and pydoe2
    - samples: int
        The number of samples to generate for the simulation
    - distribution: str
        The name of the probability distribution.
    - distribution_params: list
        The parameters associated with the probability distribution.

    Raises:
    - ValueError: If the parameters are invalid for the specified distribution.
    """

    valid_strategy = ["chaospy", "scipy", "pydoe2"]
    valid_distribution = ["Uniform", "Normal", "LogNormal", "Triangle", "Beta", "Gamma"]

    # verifying samples and distribution_params
    if samples is None:
        raise ValueError(f"assign a value to samples")
    elif type(samples) is float or type(samples) is str:
        raise ValueError(f"samples must be an integer")
    elif distribution_params is None or len(distribution_params) == 0:
        raise ValueError(f"assign a list of parameters to distribution_params")

    # verify sampling strategy
    if sampling_strategy not in valid_strategy:
        raise ValueError(
            f" Invalid sampling strategy: {sampling_strategy}. Choose from {valid_strategy}"
        )

    # verify distribution
    if distribution not in valid_distribution:
        raise ValueError(
            f"Unsupported Distribution : {distribution}. Choose from {valid_distribution}"
        )

    # special case handling for Triangle distribution
    if distribution == "Triangle":
        if len(distribution_params) == 2:
            print(
                f"{distribution} distribution has to be 3 parameters in the order of [lower_bound, mid_range, upper_bound]"
            )
            # use the mean as the middle value
            distribution_params.insert(1, np.mean(distribution_params))
        elif len(distribution_params) != 3:
            raise ValueError(
                f"{distribution} distribution has to be 3 parameters in the order of [lower_bound, mid_range, upper_bound]"
            )

    if distribution in ["Normal", "LogNormal", "Uniform", "Beta", "Gamma"]:
        if len(distribution_params) != 2:
            raise ValueError(f"{distribution} distribution must have 2 parameters")

    # handling having 0 as values in Beta and Gamma
    if distribution in ["Beta", "Gamma"]:
        if np.min(distribution_params) <= 0:
            raise ValueError(
                f"{distribution} distribution cannot have values lower than zero in parameters"
            )

    return None


if __name__ == "__main__":
    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        snakemake = mock_snakemake(
            "monte_carlo",
            simpl="",
            clusters="10",
            ll="copt",
            opts="Co2L-24H",
            unc="m0",
        )
    configure_logging(snakemake)
    monte_carlo_config = snakemake.params.monte_carlo

    ### SCENARIO INPUTS
    ###
    MONTE_CARLO_PYPSA_FEATURES = {
        k: v
        for k, v in monte_carlo_config["pypsa_standard"].items() if v
    }  # removes key value pairs with empty value e.g. []
    MONTE_CARLO_OPTIONS = monte_carlo_config["options"]
    L_BOUNDS = [item[0] for item in MONTE_CARLO_PYPSA_FEATURES.values()]
    U_BOUNDS = [item[1] for item in MONTE_CARLO_PYPSA_FEATURES.values()]
    N_FEATURES = len(MONTE_CARLO_PYPSA_FEATURES
                     )  # only counts features when specified in config
    SAMPLES = MONTE_CARLO_OPTIONS.get(
        "samples"
    )  # TODO: What is the optimal sampling? Fabian Neumann answered that in "Broad ranges" paper
    SAMPLING_STRATEGY = MONTE_CARLO_OPTIONS.get("sampling_strategy")
    DISTRIBUTION = MONTE_CARLO_OPTIONS.get("distribution")
    DISTRIBUTION_PARAMS = MONTE_CARLO_OPTIONS.get("distribution_params")

    ### PARAMETERS VALIDATION
    # validates the parameters supplied from config file
    validate_parameters(SAMPLING_STRATEGY, SAMPLES, DISTRIBUTION,
                        DISTRIBUTION_PARAMS)

    ### SCENARIO CREATION / SAMPLING STRATEGY
    ###
    if SAMPLING_STRATEGY == "pydoe2":
        lh = monte_carlo_sampling_pydoe2(
            N_FEATURES,
            SAMPLES,
            DISTRIBUTION,
            DISTRIBUTION_PARAMS,
            criterion=None,
            iteration=None,
            random_state=42,
            correlation_matrix=None,
        )
    if SAMPLING_STRATEGY == "scipy":
        lh = monte_carlo_sampling_scipy(
            N_FEATURES,
            SAMPLES,
            DISTRIBUTION,
            DISTRIBUTION_PARAMS,
            centered=False,
            strength=2,
            optimization=None,
            seed=42,
        )
    if SAMPLING_STRATEGY == "chaospy":
        lh = monte_carlo_sampling_chaospy(
            N_FEATURES,
            SAMPLES,
            DISTRIBUTION,
            DISTRIBUTION_PARAMS,
            rule="latin_hypercube",
            seed=42,
        )
    lh_scaled = qmc.scale(lh, L_BOUNDS, U_BOUNDS)

    ### MONTE-CARLO MODIFICATIONS
    ###
    n = pypsa.Network(snakemake.input[0])
    unc_wildcards = snakemake.wildcards[-1]
    i = int(unc_wildcards[1:])
    j = 0
    for k, v in MONTE_CARLO_PYPSA_FEATURES.items():
        # this loop sets in one scenario each "i" feature assumption
        # k is the config input key "loads_t.p_set"
        # v is the lower and upper bound [0.8,1.3], that was used for lh_scaled
        # i, j interaction number to pick values of experimental setup
        # Example: n.loads_t.p_set = network.loads_t.p_set = .loads_t.p_set * lh_scaled[0,0]
        exec(f"n.{k} = n.{k} * {lh_scaled[i,j]}")
        logger.info(
            f"Scaled n.{k} by factor {lh_scaled[i,j]} in the {i} scenario")
        j = j + 1

    ### EXPORT AND METADATA
    #
    latin_hypercube_dict = (pd.DataFrame(lh_scaled).rename_axis(
        "Nruns").add_suffix("_feature")).to_dict()
    n.meta.update(latin_hypercube_dict)
    n.export_to_netcdf(snakemake.output[0])
