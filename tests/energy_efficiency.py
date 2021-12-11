# -*- coding: utf-8 -*-
from os import truncate
from tests.performance_lighthouse import run_test as lighthouse_perf_run_test
from models import Rating
import datetime

from tests.utils import *
import gettext
_local = gettext.gettext

# Code below is built from: https://gitlab.com/wholegrain/carbon-api-2-0

KWG_PER_GB = 1.805
RETURNING_VISITOR_PERCENTAGE = 0.75
FIRST_TIME_VIEWING_PERCENTAGE = 0.25
PERCENTAGE_OF_DATA_LOADED_ON_SUBSEQUENT_LOAD = 0.02
CARBON_PER_KWG_GRID = 475
# PER_KWG_RENEWABLE = 33.4
# PERCENTAGE_OF_ENERGY_IN_DATACENTER = 0.1008
# PERCENTAGE_OF_ENERGY_IN_TRANSMISSION_AND_END_USER = 0.8992
# CO2_GRAMS_TO_LITRES = 0.5562


def adjust_data_transfer(transfer_bytes):
    return (transfer_bytes * RETURNING_VISITOR_PERCENTAGE) + (PERCENTAGE_OF_DATA_LOADED_ON_SUBSEQUENT_LOAD * transfer_bytes * FIRST_TIME_VIEWING_PERCENTAGE)


def energy_consumption(bytesAdjusted):
    return bytesAdjusted * (KWG_PER_GB / 1073741824)


def get_co2_grid(energy):
    return energy * CARBON_PER_KWG_GRID


# def get_co2_renewable(energy):
#     return ((energy * PERCENTAGE_OF_ENERGY_IN_DATACENTER) * CARBON_PER_KWG_RENEWABLE) + ((energy * PERCENTAGE_OF_ENERGY_IN_TRANSMISSION_AND_END_USER) * CARBON_PER_KWG_GRID)


def convert_2_co2(transfer_bytes):
    bytesAdjusted = adjust_data_transfer(transfer_bytes)
    energy = energy_consumption(bytesAdjusted)
    co2Grid = get_co2_grid(energy)
    # co2Renewable = get_co2_renewable(energy)
    return co2Grid


def cleaner_than(co2):
    # This array needs to be updated periodically with new data. This was
    # originally calculated with a database query but that was too slow at
    # scale. We can look in to writing a cron job that will generate and export
    # from the database once a month, that is then loaded in this file.

    # This array was last generated with rankings/index.php on 27/01/2020
    percentiles = [0.00126957622871866, 0.004035396817140881, 0.012595561048805604, 0.023304715095553624, 0.036438786824583, 0.050362397616329, 0.064014899640461,
                   0.077739052678226,
                   0.092126836186624,
                   0.10757047217165,
                   0.125027739890344,
                   0.140696302455872,
                   0.15929047315768,
                   0.177734818869488,
                   0.19581439489964,
                   0.21422507361825607,
                   0.232736823359142,
                   0.246082174332492, 0.264348156430992, 0.28306902111392, 0.30180466482882, 0.320295382181204, 0.33950686554985604, 0.360111566931774, 0.38114308483189, 0.40185357017186396, 0.42035354145420606, 0.4393550630164101, 0.458541453493762, 0.47918906703882, 0.499654077413412, 0.521285635156174, 0.5405494875603221, 0.56161428648152, 0.58238456980151, 0.604316363860106, 0.6256429617179278, 0.6478269528228661, 0.6691073942929641, 0.68867154881184, 0.7103787320465419, 0.7331362414675519, 0.7562483364936439, 0.780892842691506, 0.80396830015467, 0.8269877794821401, 0.85060546199698, 0.874387816802448, 0.899691291111552, 0.92324242726303, 0.9511826145960923, 0.976586133398462, 1.002258239346, 1.02822903453074, 1.0566669431626, 1.08448123862022, 1.1130571798008, 1.1446436812039398, 1.17548103245766, 1.2075157831423, 1.2419762271574795, 1.27780212823068, 1.31343697309996, 1.3535322129548801, 1.3963404885134, 1.43538821676594, 1.4786819721653202, 1.52287253339568, 1.5710404823845998, 1.6176354301871, 1.6627899659050596, 1.71503331661196, 1.7731704594157403, 1.8271314036959998, 1.8888232850004, 1.9514501162933802, 2.01843049142384, 2.08929918752446, 2.1680425684300615, 2.2538809089543, 2.347435716407921, 2.44446281762258, 2.551568006854039, 2.6716183180923796, 2.8030676779506, 2.947526052684458, 3.1029734241542397, 3.2801577012624605, 3.4659335564053406, 3.6858566410374, 3.9539822299055203, 4.2833358140900835, 4.686514950833381, 5.167897618200399, 5.7413021838327, 6.52500051792535, 7.628926245040858, 9.114465674521588, 12.30185529895519, 92.584834950345]

    position = 0
    # this should always be exactly 100 number of values
    for item in percentiles:
        position += 1
        if(co2 < item):
            return (100 - position) / 100
    return 0


def run_test(_, langCode, url):
    """
    Analyzes URL with Website Carbon Calculator API.
    API documentation: https://api.websitecarbon.com
    https://gitlab.com/wholegrain/carbon-api-2-0
    """

    language = gettext.translation(
        'energy_efficiency_websitecarbon', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local("TEXT_RUNNING_TEST"))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    result_dict = {}
    lighthouse_perf_result = lighthouse_perf_run_test(_, langCode, url, True)

    transfer_bytes = lighthouse_perf_result[1]['total-byte-weight']
    result_dict['total-byte-weight'] = transfer_bytes
    #print('transfer bytes: {0}'.format(transfer_bytes))

    co2 = convert_2_co2(transfer_bytes)
    result_dict['co2'] = co2

    cleaner = cleaner_than(co2) * 100
    result_dict['cleaner_than'] = cleaner

    review = ''

    # handicap points
    points = float("{0:.2f}".format((5 * (cleaner / 100)) + 0.9))

    if cleaner >= 80:
        review = _local("TEXT_WEBSITE_IS_VERY_GOOD")
    elif cleaner >= 70:
        review = _local("TEXT_WEBSITE_IS_GOOD")
    elif cleaner >= 60:
        review = _local("TEXT_WEBSITE_IS_OK")
    elif cleaner >= 50:
        review = _local("TEXT_WEBSITE_IS_BAD")
    elif cleaner <= 40:
        review = _local("TEXT_WEBSITE_IS_VERY_BAD")

    review += _local("TEXT_GRAMS_OF_CO2").format(round(co2, 2))
    review += _local("TEXT_BETTER_THAN").format(int(cleaner))
    # if 'false' in green.lower():
    # review += _local("TEXT_GREEN_ENERGY_FALSE")
    # elif 'true' in green.lower():
    # review += _local("TEXT_GREEN_ENERGY_TRUE")

    rating = Rating(_)
    rating.set_overall(points, review)

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)
