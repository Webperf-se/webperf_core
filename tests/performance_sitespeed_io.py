# -*- coding: utf-8 -*-
import json
from pathlib import Path
import os
import re
import subprocess
from datetime import datetime
from helpers.models import Rating
from helpers.setting_helper import get_config
from helpers.browser_helper import get_chromium_browser
from tests.utils import get_dependency_version, get_translation

def get_result(arg):
    """
    Executes a Sitespeed command and returns the result.

    This function runs a Sitespeed command either in a Docker container or directly via Node.js,
    depending on the value of `get_config('tests.sitespeed.docker.use')`.
    The command's output is captured and returned as a string.

    Args:
        arg (str): The arguments to pass to the Sitespeed command.

    Returns:
        str: The output of the Sitespeed command.
    """
    result = ''
    if get_config('tests.sitespeed.docker.use'):
        base_directory = Path(os.path.dirname(
            os.path.realpath(__file__)) + os.path.sep).parent
        data_dir = base_directory.resolve()

        sitespeedio_version = get_dependency_version('sitespeed.io')
        command = (f"docker run --rm -v {data_dir}:/sitespeed.io "
                   f"sitespeedio/sitespeed.io:{sitespeedio_version} {arg}")

        with subprocess.Popen(command.split(), stdout=subprocess.PIPE) as process:
            output, _ = process.communicate(
                timeout=get_config('general.request.timeout') * 10)
            result = str(output)
    else:
        command = (f"node node_modules{os.path.sep}sitespeed.io{os.path.sep}bin{os.path.sep}"
                   f"sitespeed.js {arg}")

        with subprocess.Popen(
            command.split(), stdout=subprocess.PIPE) as process:
            output, _ = process.communicate(
                timeout=get_config('general.request.timeout') * 10)
            result = str(output)

    return result


def run_test(global_translation, url):
    """
    Checking an URL against Sitespeed.io (Docker version). 
    For installation, check out:
    - https://hub.docker.com/r/sitespeedio/sitespeed.io/
    - https://www.sitespeed.io
    """

    local_translation = get_translation(
            'performance_sitespeed_io',
            get_config('general.language')
        )

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    rating = Rating(global_translation, get_config('general.review.improve-only'))
    result_dict = {}

    validator_result_dicts = []

    validators = get_validators()
    for validator in validators:
        if validator['name'].startswith('mobile'):
            validator_result_dicts.append(
                validate_on_mobile_using_validator(url, validator))
        if validator['name'].startswith('desktop'):
            validator_result_dicts.append(
                validate_on_desktop_using_validator(url, validator))

    # Are they still not ready they need to fix it...
    desktop_result_dict = validate_on_desktop(url)

    mobile_result_dict = validate_on_mobile(url)

    desktop_rating = rate_result_dict(desktop_result_dict, None,
                                      'desktop', global_translation)

    rating += desktop_rating
    result_dict.update(desktop_result_dict)

    mobile_rating = rate_result_dict(mobile_result_dict, None,
                                     'mobile', global_translation)

    rating += mobile_rating
    result_dict.update(mobile_result_dict)

    rating += rate_custom_result_dict(
        global_translation, result_dict, validator_result_dicts,
        desktop_result_dict, mobile_result_dict,
        desktop_rating, mobile_rating)

    if not rating.isused():
        rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return (rating, {'failed': True })

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    reviews = rating.get_reviews()
    print(global_translation('TEXT_SITE_RATING'), rating)
    if get_config('general.review.show'):
        print(
            global_translation('TEXT_SITE_REVIEW'),
            reviews)

    if get_config('general.review.data'):
        nice_json_data = json.dumps(result_dict, indent=3)
        print(
            global_translation('TEXT_SITE_REVIEW_DATA'),
            f'```json\r\n{nice_json_data}\r\n```')

    return (rating, result_dict)

def rate_custom_result_dict( # pylint: disable=too-many-arguments,too-many-locals
        global_translation, result_dict, validator_result_dicts,
        desktop_result_dict, mobile_result_dict,
        desktop_rating, mobile_rating):
    """
    Rates a custom result dictionary based on validator results and reference ratings.

    This function iterates over validator results,
    rates each one, and updates the overall rating.
    If a validator uses a reference (mobile or desktop),
    it compares the validator rating with the reference rating and
    adds advice to the overall review if the validator rating is higher.

    Returns:
        Rating: The overall rating after considering all validators.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    for validator_result_dict in validator_result_dicts:
        validator_name = validator_result_dict['name']
        reference_name = None
        reference_rating = None
        reference_result_dict = None
        use_reference = validator_result_dict['use_reference']
        if use_reference:
            if validator_name.startswith('mobile'):
                reference_name = 'mobile'
                reference_rating = mobile_rating.get_overall()
                reference_result_dict = mobile_result_dict
            if validator_name.startswith('desktop'):
                reference_name = 'desktop'
                reference_rating = desktop_rating.get_overall()
                reference_result_dict = desktop_result_dict

        validator_rating = rate_result_dict(validator_result_dict, reference_result_dict,
                                            validator_name, global_translation)
        rating += validator_rating
        result_dict.update(validator_result_dict)

        if use_reference and reference_rating is not None:
            validator_rating_overall = validator_rating.get_overall()
            if reference_rating < validator_rating_overall and\
                  validator_rating_overall != -1 and\
                  validator_rating_overall != -1:
                rating.overall_review += (
                    f'- [{reference_name}] Advice: Rating may improve from {reference_rating} to '
                    f'{validator_rating_overall} with {validator_name} changes\r\n')
    return rating


def get_validators():
    """
    Loads and returns data from the 'sitespeed-rules.json' file if it exists.

    Returns:
        list or dict: Data from the JSON file, or an empty list if the file doesn't exist.
    """
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent
    config_file = os.path.join(
        base_directory.resolve(), 'sitespeed-rules.json')
    if not os.path.exists(config_file):
        return []
    with open(config_file, encoding='utf-8') as json_config_file:
        data = json.load(json_config_file)
        return data


def validate_on_mobile_using_validator(url, validator_config):
    """
    Function to validate a URL on mobile using custom validators.

    Parameters:
    url (str): The URL to be validated.
    validator_config (dict): The validator config using HTML and/or Response headers.

    Returns:
    dict: The result dictionary containing the validation results.
    """
    browertime_plugin_options = get_browsertime_plugin_options(validator_config)
    arg = (
        '--shm-size=1g '
        f'-b {get_chromium_browser()} '
        '--mobile true '
        '--chrome.CPUThrottlingRate 3 '
        '--connectivity.profile 3gfast '
        '--visualMetrics true '
        '--plugins.remove screenshot '
        '--speedIndex true '
        '--browsertime.videoParams.createFilmstrip false '
        '--browsertime.chrome.args ignore-certificate-errors '
        f"-n {get_config('tests.sitespeed.iterations')} "
        '--preScript chrome-custom.cjs '
        f'{url}'
        f'{browertime_plugin_options}'
        )
    if get_config('tests.sitespeed.xvfb'):
        arg = '--xvfb ' + arg

    result_dict = get_result_dict(get_result(arg), validator_config['name'])
    result_dict['name'] = validator_config['name']
    result_dict['use_reference'] = validator_config['use_reference']

    return result_dict

def get_browsertime_plugin_options(validator_config):
    """
    Generates a string of plugin options for Browsertime based on
    the given validator configuration.

    The function iterates over 'headers' and 'htmls' in the validator_config.
    For each header, it appends a formatted string to the plugin options.
    The string contains the header name and value, with spaces and equals signs URL-encoded.
    Similarly for each html,
    it appends a formatted string with the 'replace' and 'replaceWith' values URL-encoded.

    Args:
        validator_config (dict): A dictionary containing 'headers' and/or 'htmls'.
        Each 'header' is a dictionary with 'name' and'value' keys.
        Each 'html' is a dictionary with 'replace' and 'replaceWith' keys.

    Returns:
        str: A string of Browsertime plugin options.
    """
    browertime_plugin_options = ''
    if 'headers' in validator_config:
        index = 1
        for header in validator_config['headers']:
            browertime_plugin_options += (
                f' --browsertime.webperf.header0{index}'
                f" {header['name'].replace(' ', '%20').replace('=', '%3D')}="
                f"{header['value'].replace(' ', '%20').replace('=', '%3D')}")
            index += 1
    if 'htmls' in validator_config:
        index = 1
        for header in validator_config['htmls']:
            browertime_plugin_options += (
                f' --browsertime.webperf.HTML0{index}'
                f" {header['replace'].replace(' ', '%20').replace('=', '%3D')}="
                f"{header['replaceWith'].replace(' ', '%20').replace('=', '%3D')}")
            index += 1
    return browertime_plugin_options


def validate_on_desktop_using_validator(url, validator_config):
    """
    Function to validate a URL on desktop using custom validators.

    Parameters:
    url (str): The URL to be validated.
    validator_config (dict): The validator config using HTML and/or Response headers.

    Returns:
    dict: The result dictionary containing the validation results.
    """
    browertime_plugin_options = get_browsertime_plugin_options(validator_config)

    arg = (
        '--shm-size=1g '
        f'-b {get_chromium_browser()} '
        '--connectivity.profile native '
        '--visualMetrics true '
        '--plugins.remove screenshot '
        '--speedIndex true '
        '--browsertime.videoParams.createFilmstrip false '
        '--browsertime.chrome.args ignore-certificate-errors '
        f"-n {get_config('tests.sitespeed.iterations')} "
        '--preScript chrome-custom.cjs '
        f'{url}'
        f'{browertime_plugin_options}'
        )
    if get_config('tests.sitespeed.xvfb'):
        arg = '--xvfb ' + arg

    result_dict = get_result_dict(get_result(arg), validator_config['name'])
    result_dict['name'] = validator_config['name']
    result_dict['use_reference'] = validator_config['use_reference']

    return result_dict


def validate_on_desktop(url):
    """
    Function to validate a URL on desktop.

    Parameters:
    url (str): The URL to be validated.

    Returns:
    dict: The result dictionary containing the validation results.
    """
    arg = (
        '--shm-size=1g '
        f'-b {get_chromium_browser()} '
        '--connectivity.profile native '
        '--visualMetrics true '
        '--plugins.remove screenshot '
        '--speedIndex true '
        '--browsertime.videoParams.createFilmstrip false '
        '--browsertime.chrome.args ignore-certificate-errors '
        f"-n {get_config('tests.sitespeed.iterations')} "
        '--preScript chrome-custom.cjs '
        f'{url}'
        )
    if get_config('tests.sitespeed.xvfb'):
        arg = '--xvfb ' + arg

    result_dict = get_result_dict(get_result(arg), 'desktop')

    return result_dict


def validate_on_mobile(url):
    """
    Function to validate a URL on mobile, simulating fast 3g.

    Parameters:
    url (str): The URL to be validated.

    Returns:
    dict: The result dictionary containing the validation results.
    """
    arg = (
        '--shm-size=1g '
        f'-b {get_chromium_browser()} '
        '--mobile true '
        '--connectivity.profile 3gfast '
        '--visualMetrics true '
        '--plugins.remove screenshot '
        '--speedIndex true '
        '--browsertime.videoParams.createFilmstrip false '
        '--browsertime.chrome.args ignore-certificate-errors '
        f"-n {get_config('tests.sitespeed.iterations')} "
        '--preScript chrome-custom.cjs '
        f'{url}'
        )
    if get_config('tests.sitespeed.xvfb'):
        arg = '--xvfb ' + arg

    result_dict = get_result_dict(get_result(arg), 'mobile')

    return result_dict


def rate_result_dict( # pylint: disable=too-many-branches,too-many-locals
        result_dict, reference_result_dict,
        mode, global_translation):
    """
    Function to rate a result dictionary based on a reference result dictionary and
    generate review texts.

    Parameters:
    result_dict (dict): The result dictionary to be rated.
    reference_result_dict (dict): The reference result dictionary for comparison.
    mode (str): The mode of changes.
    global_translation (str): The global translation used for rating.

    Returns:
    Rating: A Rating object with the overall and performance reviews.
    """
    limit = 500

    rating = Rating(global_translation, get_config('general.review.improve-only'))
    performance_review = ''
    overview_review = ''

    if reference_result_dict is not None:
        reference_name = get_reference_name(result_dict)
        external_to_remove = []
        for pair in reference_result_dict.items():
            key = pair[0]
            mobile_obj = pair[1]

            if key not in result_dict:
                continue

            noxternal_obj = result_dict[key]

            if 'median' not in mobile_obj:
                continue
            if 'median' not in noxternal_obj:
                continue

            key_matching = False
            txt = get_improve_advice_text(mode, limit, reference_name,
                                          key, mobile_obj, noxternal_obj)
            if txt is not None:
                overview_review += txt
                key_matching = True

            if 'range' not in mobile_obj:
                continue
            if 'range' not in noxternal_obj:
                continue
            key_matching = get_bumpy_advice_text(mode, limit, reference_name,
                                                 key, mobile_obj, noxternal_obj)

            if not key_matching:
                external_to_remove.append(key)

        for key in external_to_remove:
            del result_dict[key]

    cleanup_result_dict(result_dict)

    for pair in result_dict.items():
        value = pair[1]
        if 'msg' not in value:
            continue
        if 'points' in value and value['points'] != -1:
            points = value['points']
            entry_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            entry_rating.set_overall(points)
            entry_rating.set_performance(
                points, value['msg'])
            rating += entry_rating
        else:
            performance_review += f"{value['msg']}\r\n"

    rating.overall_review = rating.overall_review + overview_review
    rating.performance_review = rating.performance_review + performance_review
    return rating

def get_bumpy_advice_text(mode, limit, reference_name, key, mobile_obj, noxternal_obj): # pylint: disable=too-many-arguments
    """
    Function to generate advice text on how to make
    a certain key less "bumpy" based on the comparison of range values.

    The function compares the range value of 'mobile_obj' with the sum of 'limit' and
    the range value of 'noxternal_obj'.
    If the range value of 'mobile_obj' is greater,
    it calculates the difference between the two range values and generates advice text.
    If not, it returns None.

    Parameters:
    mode (str): The mode of changes.
    limit (float): The limit value for comparison.
    reference_name (str): The reference name.
    key (str): The key that could be made less "bumpy".
    mobile_obj (dict): A dictionary containing a 'range' key,
        the value of which is used for comparison.
    noxternal_obj (dict): A dictionary containing a 'range' key,
        the value of which is used for comparison.

    Returns:
    str or None: The advice text on how to make the key less "bumpy" with mode changes,
        or None if the condition is not met.
    """
    if mobile_obj['range'] > (limit + noxternal_obj['range']):
        value_diff = mobile_obj['range'] - noxternal_obj['range']
        txt = (
                    f'- [{reference_name}] Advice: {key} could be ±{value_diff:.2f}ms '
                    f'less "bumpy" with {mode} changes\r\n')

        return txt
    return None

def get_improve_advice_text(mode, limit, reference_name, key, mobile_obj, noxternal_obj): # pylint: disable=too-many-arguments
    """
    Function to generate advice text on how to improve a
    certain key based on the comparison of median values.

    The function compares the median value of 'mobile_obj' with the sum of 'limit' and
    the median value of 'noxternal_obj'.
    If the median value of 'mobile_obj' is greater,
    it calculates the difference between the two median values and generates advice text.
    If not, it returns None.

    Parameters:
    mode (str): The mode of changes.
    limit (float): The limit value for comparison.
    reference_name (str): The reference name.
    key (str): The key that may be improved.
    mobile_obj (dict): A dictionary containing a 'median' key,
        the value of which is used for comparison.
    noxternal_obj (dict): A dictionary containing a 'median' key,
        the value of which is used for comparison.

    Returns:
    str or None: The advice text on how to improve the key with mode changes,
        or None if the condition is not met.
    """
    if mobile_obj['median'] > (limit + noxternal_obj['median']):
        value_diff = mobile_obj['median'] - noxternal_obj['median']
        txt = (
                    f'- [{reference_name}] Advice: {key} may improve by '
                    f'{value_diff:.2f}ms with {mode} changes\r\n')
        return txt
    return None


def get_reference_name(result_dict):
    """
    Function to determine the reference name based on the 'name' key in the input dictionary.

    The function checks the start of the string value of the 'name' key in the input dictionary.
    If it starts with 'mobile', the reference name is set to 'mobile'.
    If it starts with 'desktop', the reference name is set to 'desktop'.
    If neither condition is met, the reference name defaults to 'UNKNOWN'.

    Parameters:
    result_dict (dict): A dictionary containing a 'name' key,
    the value of which is used to determine the reference name.

    Returns:
    str: The reference name, which can be 'mobile', 'desktop', or 'UNKNOWN'.
    """
    reference_name = 'UNKNOWN'
    if result_dict['name'].startswith('mobile'):
        reference_name = 'mobile'
    if result_dict['name'].startswith('desktop'):
        reference_name = 'desktop'
    return reference_name

def cleanup_result_dict(result_dict):
    """
    Remove specific keys from the result dictionary.

    Parameters:
    result_dict (dict): The result dictionary to be cleaned up.

    Returns:
    None: The function modifies the dictionary in-place and does not return anything.
    """
    if 'Points' in result_dict:
        del result_dict['Points']
    if 'name' in result_dict:
        del result_dict['name']
    if 'use_reference' in result_dict:
        del result_dict['use_reference']


def get_result_dict(data, mode):
    """
    Extract performance metrics from the data and calculate the results for each metric.

    This function uses a regular expression to extract performance metrics and
    their values from the data.
    It then calculates the results for each metric using the `get_data_for_entry` function and
    stores them in a dictionary.

    Parameters:
    data (str): The data containing the performance metrics and their values.
    mode (str): The mode of the device ('desktop' or 'mobile').

    Returns:
    dict: A dictionary where the keys are the performance metrics and
    the values are dictionaries containing the results for each metric.
    """
    result_dict = {}
    tmp_dict = {}
    regex = r"(?P<name>TTFB|DOMContentLoaded|firstPaint|FCP|LCP|Load|TBT|CLS|FirstVisualChange|SpeedIndex|VisualComplete85|LastVisualChange)\:[ ]{0,1}(?P<value>[0-9\.ms]+)" # pylint: disable=line-too-long
    matches = re.finditer(regex, data, re.MULTILINE)

    for _, match in enumerate(matches, start=1):
        name = match.group('name')
        value = match.group('value')

        if name not in tmp_dict:
            tmp_dict[name] = []
        tmp_dict[name].append(value)

    for pair in tmp_dict.items():
        key = pair[0]
        values = pair[1]
        tmp = get_data_for_entry(mode, key, values)

        result_dict[key] = tmp
    return result_dict

def get_data_for_entry(mode, key, values):
    """
    Calculate the performance data for a given entry.

    This function calculates the median, range, points, and message for a given performance metric.
    It processes the values, which are in milliseconds or seconds,
    and calculates the total, biggest, median, and range.
    It also gets the full name of the metric and calculates the points.

    Parameters:
    mode (str): The mode of the device ('desktop' or 'mobile').
    key (str): The performance metric key.
    values (list): The list of values for the performance metric.

    Returns:
    dict: A dictionary containing the median, range, mode, points, message, and values.
    """
    biggest = 0
    total = 0
    value_range = 0
    result = 0
    median = 0
    for value in values:
        number = 0
        if 'ms' in value:
            number = float(value.replace('ms', ''))
        elif 's' in value:
            number = float(
                    value.replace('s', '')) * 1000
        total += number
        biggest = max(biggest, number)
    value_count = len(values)
    if value_count < 2:
        value_range = 0
        result = total
    else:
        median = total / value_count
        value_range = biggest - median
        result = median

    fullname = get_fullname(key)
    points = get_points(mode, key, result, median)

    tmp = {
            'median': median,
            'range': value_range,
            'mode': mode,
            'points': points,
            'msg': f'- [{mode}] {fullname}: {result:.2f}ms, ±{value_range:.2f}ms',
            'values': values
        }
    return tmp

def get_fullname(key):
    """
    Converts a performance metric abbreviation to its full name.

    Args:
        key (str): The abbreviation of a web performance metric.

    Returns:
        str: The full name of the web performance metric, or the original key if no match is found.
    """
    fullname = key
    if 'TTFB' in key:
                # https://web.dev/ttfb/
        fullname = 'TTFB (Time to First Byte)'
    elif 'TBT' in key:
                # https://web.dev/tbt/
                # https://developer.chrome.com/docs/lighthouse/performance/lighthouse-total-blocking-time/#how-lighthouse-determines-your-tbt-score
        fullname = 'TBT (Total Blocking Time)'
    elif 'FCP' in key:
                # https://web.dev/fcp/
        fullname = 'FCP (First Contentful Paint)'
    elif 'LCP' in key:
                # https://web.dev/lcp/
        fullname = 'LCP (Largest Contentful Paint)'
    elif 'CLS' in key:
                # https://web.dev/cls/
        fullname = 'CLS (Cumulative Layout Shift)'
    return fullname

def get_points(mode, key, result, median):
    """
    Calculate the performance points based on the mode, key, result, and median.

    This function assigns points based on different performance metrics such as:
    TTFB, TBT, FCP, LCP, CLS, SpeedIndex, FirstVisualChange, VisualComplete85, and Load.
    The points are calculated differently for each metric and
    can also vary based on the mode ('desktop' or 'mobile').

    Parameters:
    mode (str): The mode of the device ('desktop' or 'mobile').
    key (str): The performance metric key.
    result (float): The result value for the SpeedIndex related metrics.
    median (float): The median value for the TTFB, TBT, FCP, LCP, and CLS metrics.

    Returns:
    float: The calculated performance points.

    Note:
    For more information on SpeedIndex, refer to: https://docs.webpagetest.org/metrics/speedindex/
    """
    points = -1
    if 'TTFB' in key:
        points = get_ttfb_points(mode, median)
    elif 'TBT' in key:
        points = get_tbt_points(median)
    elif 'FCP' in key:
        points = get_fcp_points(median)
    elif 'LCP' in key:
        points = get_lcp_points(mode, median)
    elif 'CLS' in key:
        points = get_cls_points(median)

    elif 'SpeedIndex' in key or\
              'FirstVisualChange' in key or\
              'VisualComplete85' in key or 'Load' in key:
            # https://docs.webpagetest.org/metrics/speedindex/
        adjustment = 500
        if 'mobile' in mode:
            adjustment = 1500

        limit = 500
            # give 0.5 seconds in credit
        speedindex_adjusted = result - adjustment
        if speedindex_adjusted <= 0:
                # speed index is 500 or below, give highest score
            points = 5.0
        else:
            points = 5.0 - ((speedindex_adjusted / limit) * 1.0)
    return points

def get_cls_points(median):
    """
    Calculate the Cumulative Layout Shift (CLS) points based on the mode and median.

    Parameters:
    mode (str): The mode of the device ('desktop' or 'mobile').
    median (float): The median CLS in milliseconds.

    Returns:
    float: The calculated CLS points.
    """
    points = 5.0
    if median <= 0.1:
        points = 5.0
    elif median <= 0.25:
        points = 3.0
    else:
        points = 1.0
    return points

def get_fcp_points(median):
    """
    Calculate the First Contentful Paint (FCP) points based on the mode and median.

    Parameters:
    mode (str): The mode of the device ('desktop' or 'mobile').
    median (float): The median FCP in milliseconds.

    Returns:
    float: The calculated FCP points.
    """
    points = 5.0
    if median <= 1800:
        points = 5.0
    elif median <= 3000:
        points = 3.0
    else:
        points = 1.0
    return points

def get_tbt_points(median):
    """
    Calculate the Total Blocking Time (TBT) points based on the mode and median.

    Parameters:
    mode (str): The mode of the device ('desktop' or 'mobile').
    median (float): The median TBT in milliseconds.

    Returns:
    float: The calculated TBT points.
    """
    points = 5.0
    if median <= 200:
        points = 5.0
    elif median <= 600:
        points = 3.0
    else:
        points = 1.0
    return points

def get_lcp_points(mode, median):
    """
    Calculate the Largest Contentful Paint (LCP) points based on the mode and median.

    Parameters:
    mode (str): The mode of the device ('desktop' or 'mobile').
    median (float): The median LCP in milliseconds.

    Returns:
    float: The calculated LCP points.
    """
    points = 5.0
    if 'desktop' in mode:
        if median <= 500:
            points = 5.0
        elif median <= 1000:
            points = 3.0
        else:
            points = 1.0
    elif 'mobile' in mode:
        if median <= 1500:
            points = 5.0
        elif median <= 2500:
            points = 3.0
        else:
            points = 1.0
    return points

def get_ttfb_points(mode, median):
    """
    Calculate the Time to First Byte (TTFB) points based on the mode and median.

    Parameters:
    mode (str): The mode of the device ('desktop' or 'mobile').
    median (float): The median TTFB in milliseconds.

    Returns:
    float: The calculated TTFB points.
    """
    points = 5.0
    if 'desktop' in mode:
        if median <= 250:
            points = 5.0
        elif median <= 450:
            points = 3.0
        else:
            points = 1.0
    elif 'mobile' in mode:
        if median <= 800:
            points = 5.0
        elif median <= 1800:
            points = 3.0
        else:
            points = 1.0
    return points
