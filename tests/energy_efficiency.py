# -*- coding: utf-8 -*-
from datetime import datetime
from helpers.setting_helper import get_config
from models import Rating
from tests import energy_efficiency_carbon_percentiles
import tests.energy_efficiency_carbon_percentiles2022 as energy_efficiency_carbon_percentiles_2022
from tests.performance_lighthouse import run_test as lighthouse_perf_run_test
from tests.utils import get_translation

# Code below is built from: https://gitlab.com/wholegrain/carbon-api-2-0

KWG_PER_GB = 1.805
RETURNING_VISITOR_PERCENTAGE = 0.75
FIRST_TIME_VIEWING_PERCENTAGE = 0.25
PERCENTAGE_OF_DATA_LOADED_ON_SUBSEQUENT_LOAD = 0.02
CARBON_PER_KWG_GRID = 475

def adjust_data_transfer(transfer_bytes):
    """
    Adjusts the data transfer bytes considering the percentage of
    returning visitors and first-time viewers.

    Parameters:
    transfer_bytes (int): The original data transfer bytes.

    Returns:
    float: The adjusted data transfer bytes.
    """
    return (transfer_bytes * RETURNING_VISITOR_PERCENTAGE)\
        + (PERCENTAGE_OF_DATA_LOADED_ON_SUBSEQUENT_LOAD *\
           transfer_bytes * FIRST_TIME_VIEWING_PERCENTAGE)

def energy_consumption(bytes_adjusted):
    """
    Calculates the energy consumption based on the adjusted data transfer bytes.

    Parameters:
    bytes_adjusted (float): The adjusted data transfer bytes.

    Returns:
    float: The energy consumption in kilowatt-grams per gigabyte.
    """
    return bytes_adjusted * (KWG_PER_GB / 1073741824)

def get_co2_grid(energy):
    """
    Calculates the CO2 emissions based on the energy consumption.

    Parameters:
    energy (float): The energy consumption in kilowatt-grams per gigabyte.

    Returns:
    float: The CO2 emissions in the grid.
    """
    return energy * CARBON_PER_KWG_GRID

def convert_2_co2(transfer_bytes):
    """
    Converts the data transfer bytes to CO2 emissions.

    This function adjusts the data transfer bytes,
    calculates the energy consumption based on the adjusted bytes,
    and then calculates the CO2 emissions based on the energy consumption.

    Parameters:
    transfer_bytes (int): The original data transfer bytes.

    Returns:
    float: The CO2 emissions in the grid.
    """
    bytes_adjusted = adjust_data_transfer(transfer_bytes)
    energy = energy_consumption(bytes_adjusted)
    co2_grid = get_co2_grid(energy)
    return co2_grid


def cleaner_than(co2, year='current'):
    """
    Determines how much cleaner a given CO2 value is compared to a set of percentiles.

    This function compares a given CO2 value to a set of percentiles that
    represent the distribution of CO2 values for a particular year.
    The percentiles are loaded from a file that is updated periodically with new data.

    Parameters:
    co2 (float): The CO2 value to compare.
    year (str, optional): The year for which to load the percentiles.
    If not specified, the current year's percentiles are loaded. Defaults to 'current'.

    Returns:
    float: The percentile of the given CO2 value. This is a value between 0 and 1,
    where 1 means the CO2 value is cleaner than all the percentiles,
    and 0 means it is not cleaner than any of them.
    """
    # This array needs to be updated periodically with new data. This was
    # originally calculated with a database query but that was too slow at
    # scale. We can look in to writing a cron job that will generate and export
    # from the database once a month, that is then loaded in this file.

    percentiles = False
    if year == '2022':
        percentiles = energy_efficiency_carbon_percentiles_2022.get_percentiles()
    else:
        percentiles = energy_efficiency_carbon_percentiles.get_percentiles()
    position = 0
    # this should always be exactly 100 number of values
    for item in percentiles:
        position += 1
        if co2 < item:
            return (100 - position) / 100
    return 0


def format_bytes(size):
    """
    Converts a byte size into a human-readable format.

    This function takes a size in bytes and converts it into a more readable format,
    using the appropriate unit (bytes, kilobytes, megabytes, gigabytes, or terabytes).

    Parameters:
    size (int): The size in bytes to be converted.

    Returns:
    tuple: A tuple containing the converted size and the unit used for the conversion.
           The size is a float and the unit is a string.
    """
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'k', 2: 'm', 3: 'g', 4: 't'}
    while size > power:
        size /= power
        n += 1
    return size, power_labels[n]+'b'


def run_test(global_translation, url):
    """
    Analyzes URL with Lighthouse and uses weight to calculate co2 and rate compared to other sites.
    """

    local_translation = get_translation(
            'energy_efficiency',
            get_config('general.language')
        )

    print(local_translation("TEXT_RUNNING_TEST"))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    result_dict = {}
    transfer_bytes = get_total_bytes_for_url(
        global_translation,
        url)
    if transfer_bytes is None:
        rating = Rating(global_translation)
        rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return (rating, {'failed': True })

    result_dict['total-byte-weight'] = transfer_bytes

    co2 = convert_2_co2(transfer_bytes)
    result_dict['co2'] = co2

    cleaner = cleaner_than(co2) * 100
    cleaner_2022 = cleaner_than(co2, '2022') * 100
    result_dict['cleaner_than'] = cleaner

    review = ''

    points = float(f"{(5 * (cleaner / 100)):.2f}")

    # handicap points
    if cleaner >= 95:
        points = 5.0

    if cleaner >= 90:
        review = local_translation("TEXT_WEBSITE_IS_VERY_GOOD")
    elif cleaner >= 70:
        review = local_translation("TEXT_WEBSITE_IS_GOOD")
    elif cleaner >= 50:
        review = local_translation("TEXT_WEBSITE_IS_OK")
    elif cleaner >= 30:
        review = local_translation("TEXT_WEBSITE_IS_BAD")
    elif cleaner < 30:
        review = local_translation("TEXT_WEBSITE_IS_VERY_BAD")

    review += local_translation("TEXT_GRAMS_OF_CO2").format(round(co2, 2))
    latest_generated_date = energy_efficiency_carbon_percentiles.get_generated_date()
    review += local_translation("TEXT_BETTER_THAN").format(
                    int(cleaner),
                    latest_generated_date)

    old_generated_date = energy_efficiency_carbon_percentiles_2022.get_generated_date()
    review += local_translation("TEXT_BETTER_THAN").format(
                    int(cleaner_2022),
                    old_generated_date)

    transfer_info = format_bytes(transfer_bytes)
    review += local_translation("TEXT_TRANSFER_SIZE").format(transfer_info[0], transfer_info[1])

    rating = Rating(global_translation)
    rating.set_overall(points, review)

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)

def get_total_bytes_for_url(global_translation, url):
    """
    Runs a Lighthouse performance test on a given URL and returns the total byte weight of the page.

    This function is specifically designed to work with multilingual websites.
    It uses the 'global_translation'
    to handle the language-specific aspects of the website.

    Parameters:
    global_translation (dict): A dictionary containing language-specific translations.
    url (str): The URL of the webpage to run the Lighthouse performance test on.

    Returns:
    int: The total byte weight of the webpage as determined by the Lighthouse performance test.
    """
    lighthouse_perf_result = lighthouse_perf_run_test(global_translation, url, True)

    if not lighthouse_perf_result[0].isused():
        return None

    transfer_bytes = lighthouse_perf_result[1]['total-byte-weight']
    return transfer_bytes
