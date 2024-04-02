# -*- coding: utf-8 -*-
import os
from urllib.parse import urlparse
from datetime import datetime
import re
from bs4 import BeautifulSoup
from models import Rating
from tests.utils import get_config_or_default, get_root_url,\
    get_translation, has_redirect, get_http_content
from engines.sitemap import read_sitemap

# DEFAULTS
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USERAGENT = get_config_or_default('useragent')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
USE_DETAILED_REPORT = get_config_or_default('USE_DETAILED_REPORT')
KNOWN_EXTENSIONS = ['bmp', 'css', 'doc', 'docx', 'dot', 'eot', 'exe', 'git',
                    'ico', 'ics', 'jpeg', 'jpg', 'js','json', 'md', 'mov', 'mp3',
                    'mp4', 'pdf', 'png', 'ppt', 'pptx', 'pub', 'svg', 'tif',
                    'txt', 'unknown-in-download', 'webp', 'wmv', 'xls', 'xlsx', 'xml', 'zip']


def run_test(global_translation, lang_code, url):
    """
    Looking for:
    * robots.txt
    * at least one sitemap/siteindex mentioned in robots.txt
    * a RSS feed mentioned in the page's meta
    """

    local_translation = get_translation('standard_files', lang_code)

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    result_dict = {
        'url': url,
        'root_url': get_root_url(url)
    }

    # robots.txt
    rating += validate_robots(result_dict, global_translation, local_translation)

    # sitemap.xml
    rating += validate_sitemaps(
        result_dict,
        global_translation,
        local_translation)

    # rss feed
    rating += validate_feed(result_dict, global_translation, local_translation)

    # security.txt
    rating += validate_security_txt(result_dict, global_translation, local_translation)

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)

def validate_robots(result_dict, global_translation, local_translation):
    """
    Validates the robots.txt file of a website.

    This function checks the robots.txt file of a website and rates it based on its content. 
    It first checks if the robots.txt file is redirected, and if so, updates the URL. 
    It then retrieves the content of the robots.txt file.
    If the content is missing or does not contain 'user-agent', 'disallow', or 'allow',
    it sets the rating to 1.0 and the status to 'missing content'. 
    Otherwise, it sets the rating to 5.0 and the status to 'ok'.

    Args:
        result_dict (dict): A dictionary containing the results of the validation.
        global_translation (function): A function to translate text to a global language.
        local_translation (function): A function to translate text to a local language.

    Returns:
        Rating: A Rating object containing the overall rating and
        standards rating of the robots.txt file.
    """
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)


    robots_dict = {
        'url': result_dict['root_url'] + 'robots.txt'
    }

    (is_redirected, url_destination, _) = has_redirect(robots_dict['url'])
    if is_redirected:
        robots_dict['url'] = url_destination

    robots_dict['content'] = get_http_content(robots_dict['url'], True)

    if robots_dict['content'] is None or '</html>' in robots_dict['content'].lower() or \
          ('user-agent' not in robots_dict['content'].lower() \
           and 'disallow' not in robots_dict['content'].lower() \
           and 'allow' not in robots_dict['content'].lower()):
        rating.set_overall(1.0)
        rating.set_standards(1.0, local_translation("TEXT_ROBOTS_MISSING"))
        robots_dict['status'] = 'missing content'
        robots_dict['content'] = None
    else:
        rating.set_overall(5.0)
        rating.set_standards(5.0, local_translation("TEXT_ROBOTS_OK"))

        robots_dict['status'] = 'ok'

    result_dict['robots'] = robots_dict

    return rating


def validate_sitemaps(result_dict,
                      global_translation,
                      local_translation):
    """
    Validates the sitemaps of a website.

    This function checks the sitemaps of a website and rates them based on their content. 
    It first checks if the sitemaps are mentioned in the robots.txt file of the website. 
    If not, it sets the rating to 1.0 and the status to 'not in robots.txt'. 
    If the sitemaps are mentioned, it validates each sitemap URL and calculates a rating for each. 
    The final rating is the average of all the sitemap ratings.

    Args:
        result_dict (dict): A dictionary containing the results of the validation.
        global_translation (function): A function to translate text to a global language.
        local_translation (function): A function to translate text to a local language.

    Returns:
        Rating: A Rating object containing the overall rating and standards rating of the sitemaps.
    """
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    sitemaps_dict = {
        'nof_sitemaps': 0,
        'sitemap_urls_in_robots': [],
        'sitemaps': {},
        'use_https_only': True,
        'use_same_domain': True,
        'known_types': {},
        'has_duplicates': False,
        'nof_items': 0,
        'nof_items_no_duplicates': 0
    }

    if result_dict['robots']['status'] != 'ok' or\
            'sitemap:' not in result_dict['robots']['content'].lower():
        rating.set_overall(1.0)
        rating.set_standards(1.0, local_translation("TEXT_SITEMAP_MISSING"))
        sitemaps_dict['status'] = 'not in robots.txt'
        result_dict['sitemap'] = sitemaps_dict
        return rating

    regex = r"^sitemap\:(?P<url>[^\n]+)"
    matches = re.finditer(regex, result_dict['robots']['content'], re.MULTILINE | re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        sitemap_url = match.group('url').strip()
        sitemaps_dict["sitemap_urls_in_robots"].append(sitemap_url)

    sitemaps_dict["nof_sitemaps"] = len(sitemaps_dict["sitemap_urls_in_robots"])

    # NOTE: https://internetverkstan.se/ has styled sitemap

    if sitemaps_dict["nof_sitemaps"] == 0:
        rating.set_overall(2.0)
        rating.set_standards(2.0, local_translation("TEXT_SITEMAP_FOUND"))
        result_dict['sitemap'] = sitemaps_dict
        return rating

    robots_domain = get_domain(result_dict['robots']['url'])
    sitemaps_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    for sitemap_url in sitemaps_dict["sitemap_urls_in_robots"]:
        sitemaps_rating += validate_sitemap(sitemap_url,
                                            sitemaps_dict,
                                            robots_domain,
                                            global_translation,
                                            local_translation)

    if not sitemaps_rating.is_set:
        result_dict['sitemap'] = sitemaps_dict
        return rating

    final_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if USE_DETAILED_REPORT:
        final_rating.set_overall(sitemaps_rating.get_overall())
        final_rating.overall_review = sitemaps_rating.overall_review
        final_rating.set_standards(sitemaps_rating.get_standards())
        final_rating.standards_review = sitemaps_rating.standards_review
    else:
        review = ''
        points = sitemaps_rating.get_standards()
        if points >= 5.0:
            review = local_translation('TEXT_SITEMAP_VERY_GOOD')
        elif points >= 4.0:
            review = local_translation('TEXT_SITEMAP_IS_GOOD')
        elif points >= 3.0:
            review = local_translation('TEXT_SITEMAP_IS_OK')
        elif points > 1.0:
            review = local_translation('TEXT_SITEMAP_IS_BAD')
        elif points <= 1.0:
            review = local_translation('TEXT_SITEMAP_IS_VERY_BAD')

        final_rating.set_overall(sitemaps_rating.get_overall())
        final_rating.set_standards(
            points,
            review)
    rating += final_rating

    result_dict['sitemap'] = sitemaps_dict
    return rating

def get_domain(url):
    """
    Extracts the domain name from a given URL.
    """
    parsed_url = urlparse(url)
    return parsed_url.hostname

def validate_sitemap(sitemap_url,
                     sitemaps_dict,
                     robots_domain,
                     global_translation,
                     local_translation):
    """
    Validates a sitemap of a website.

    This function reads the sitemap from the provided URL and validates it.
    It checks if the sitemap uses HTTPS only, if it uses the same domain as the robots.txt file,
    and if it contains any duplicate entries. It then updates the 
    sitemaps dictionary with the results of the validation and calculates a rating for the sitemap.

    Args:
        sitemap_url (str): The URL of the sitemap to validate.
        sitemaps_dict (dict): A dictionary containing the results of the sitemap validation.
        robots_domain (str): The domain of the robots.txt file.
        global_translation (function): A function to translate text to a global language.
        local_translation (function): A function to translate text to a local language.

    Returns:
        Rating: A Rating object containing the overall rating and standards rating of the sitemap.
    """
    sitemaps = read_sitemap(sitemap_url, -1, -1, False)

    for key, items in sitemaps.items():
        if key == 'all':
            continue

        if key not in sitemaps_dict["sitemaps"]:
            sitemap_dict = create_sitemap_dict(items, robots_domain)
            sitemaps_dict["sitemaps"][key] = sitemap_dict

            if not sitemap_dict['use_https_only']:
                sitemaps_dict['use_https_only'] = False
            if not sitemap_dict['use_same_domain']:
                sitemaps_dict['use_same_domain'] = False
            if sitemap_dict['has_duplicates']:
                sitemaps_dict['has_duplicates'] = True
            sitemaps_dict['known_types'].update(sitemap_dict['known_types'])
            sitemaps_dict['nof_items'] += sitemap_dict['nof_items']
            sitemaps_dict['nof_items_no_duplicates'] += sitemap_dict['nof_items_no_duplicates']

    rating = rate_sitemap(sitemaps_dict, global_translation, local_translation, sitemaps)
    return rating

def rate_sitemap(sitemaps_dict, global_translation, local_translation, sitemaps):
    """
    Rates the sitemaps based on various criteria such as use of HTTPS, domain consistency,
    duplicate handling, known types, and size. 

    Parameters:
    sitemaps_dict (dict): Dictionary containing sitemap data.
    global_translation (function): Function for global translation.
    local_translation (function): Function for local translation.
    sitemaps (dict): Dictionary containing all sitemaps.

    Returns:
    Rating: A rating object representing the overall rating of the sitemaps.
    """
    sitemap_items = sitemaps['all']

    total_nof_items = len(sitemap_items)
    sitemap_items = list(set(sitemap_items))
    total_nof_items_no_duplicates = len(sitemap_items)

    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    rate_sitemap_use_https_only(sitemaps_dict, global_translation, local_translation, rating)
    rate_sitemap_use_same_domain(sitemaps_dict, global_translation, local_translation, rating)
    rate_sitemap_use_of_duplicates(global_translation,
                                   local_translation,
                                   total_nof_items,
                                   total_nof_items_no_duplicates,
                                   rating)

    rate_sitemap_use_known_types(sitemaps_dict,
                                 global_translation,
                                 local_translation,
                                 total_nof_items,
                                 rating)

    # loop sitemaps and see if any single sitemap exsits amount
    for key in sitemaps.keys():
        if key == 'all':
            continue

        nof_items = len(sitemaps[key])

        if nof_items > 50_000:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(
                        1.0)
            sub_rating.set_standards(
                        1.0,  local_translation("TEXT_SITEMAP_TOO_LARGE"))
            rating += sub_rating
        else:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(
                        5.0)
            sub_rating.set_standards(
                        5.0, local_translation("TEXT_SITEMAP_NOT_TOO_LARGE"))
            rating += sub_rating

    rate_sitemap_any_items(sitemaps_dict,
                           global_translation,
                           local_translation,
                           total_nof_items,
                           rating)
    return rating

def rate_sitemap_any_items(sitemaps_dict,
                           global_translation,
                           local_translation,
                           total_nof_items,
                           rating):
    """
    Rates the sitemaps based on the presence of any items. Updates the status in the sitemaps_dict.

    Parameters:
    sitemaps_dict (dict): Dictionary containing sitemap data.
    global_translation (function): Function for global translation.
    local_translation (function): Function for local translation.
    total_nof_items (int): Total number of items in the sitemaps.
    rating (Rating): The rating object to be updated.

    Returns:
    None: The function updates the rating and sitemaps_dict in-place.
    """
    if total_nof_items == 0:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    1.0)
        sub_rating.set_standards(
                    1.0, local_translation("TEXT_SITEMAP_BROKEN"))
        rating += sub_rating

        sitemaps_dict['status'] = "sitemap(s) seem to be broken"
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, local_translation("TEXT_SITEMAP_IS_OK"))
        rating += sub_rating

        sitemaps_dict['status'] = "sitemap(s) seem ok"

def rate_sitemap_use_known_types(sitemaps_dict,
                                 global_translation,
                                 local_translation,
                                 total_nof_items,
                                 rating):
    """
    Rates the sitemaps based on the use of known types.
    Updates the rating based on the proportion of webpages.

    Parameters:
    sitemaps_dict (dict): Dictionary containing sitemap data.
    global_translation (function): Function for global translation.
    local_translation (function): Function for local translation.
    total_nof_items (int): Total number of items in the sitemaps.
    rating (Rating): The rating object to be updated.

    Returns:
    None: The function updates the rating in-place.
    """
    type_keys = sitemaps_dict['known_types'].keys()
    if len(type_keys) > 1:
        webpages_points = 1.0
        if 'webpage' in type_keys:
            nof_webpages = sitemaps_dict['known_types']['webpage']
            ratio = nof_webpages / total_nof_items
            webpages_points = 5.0 * ratio

        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    webpages_points)
        sub_rating.set_standards(
                    webpages_points,  local_translation("TEXT_SITEMAP_NOT_ONLY_WEBPAGES"))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, local_translation("TEXT_SITEMAP_ONLY_WEBPAGES"))
        rating += sub_rating

def rate_sitemap_use_of_duplicates(global_translation,
                                   local_translation,
                                   total_nof_items,
                                   total_nof_items_no_duplicates,
                                   rating):
    """
    Rates the sitemaps based on the presence of duplicate items.
    Updates the rating based on the ratio of unique items.

    Parameters:
    global_translation (function): Function for global translation.
    local_translation (function): Function for local translation.
    total_nof_items (int): Total number of items in the sitemaps.
    total_nof_items_no_duplicates (int): Total number of unique items in the sitemaps.
    rating (Rating): The rating object to be updated.

    Returns:
    None: The function updates the rating in-place.
    """
    if total_nof_items !=  total_nof_items_no_duplicates:
        ratio = total_nof_items_no_duplicates / total_nof_items
        duplicates_points = 3.0 * ratio
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    duplicates_points)
        sub_rating.set_standards(
                    duplicates_points, local_translation("TEXT_SITEMAP_INCLUDE_DUPLICATES"))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, local_translation("TEXT_SITEMAP_NO_DUPLICATES"))
        rating += sub_rating

def rate_sitemap_use_same_domain(sitemaps_dict, global_translation, local_translation, rating):
    """
    This function rates the use of the same domain for sitemaps and robots.txt.

    Parameters:
    sitemaps_dict (dict): A dictionary containing information about the sitemaps.
    global_translation (function): A function for translating text globally.
    local_translation (function): A function for translating text locally.
    rating (Rating): An instance of the Rating class.

    The function checks if the sitemaps use the same domain as specified in the robots.txt file.
    If they do, it sets the overall and standards ratings to 5.0 and adds a positive message.
    If they don't, it sets the overall and standards ratings to 1.0 and
    adds a message for improvement. The function modifies the rating in-place.

    Returns:
    None
    """
    if not sitemaps_dict['use_same_domain']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    1.0)
        sub_rating.set_standards(
                    1.0, local_translation("TEXT_SITEMAP_NOT_SAME_DOMAIN_AS_ROBOTS_TXT"))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, local_translation("TEXT_SITEMAP_SAME_DOMAIN_AS_ROBOTS_TXT"))
        rating += sub_rating

def rate_sitemap_use_https_only(sitemaps_dict, global_translation, local_translation, rating):
    """
    This function rates the use of HTTPS only for sitemaps.

    Parameters:
    sitemaps_dict (dict): A dictionary containing information about the sitemaps.
    global_translation (function): A function for translating text globally.
    local_translation (function): A function for translating text locally.
    rating (Rating): An instance of the Rating class.

    The function checks if the sitemaps use HTTPS only.
    If they do, it sets the overall and standards ratings to 5.0 and adds a positive message.
    If they don't, it sets the overall and standards ratings to 1.0 and
    adds a message for improvement. The function modifies the rating in-place.

    Returns:
    None
    """
    if not sitemaps_dict['use_https_only']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    1.0)
        sub_rating.set_standards(
                    1.0, local_translation("TEXT_SITEMAP_NOT_STARTING_WITH_HTTPS_SCHEME"))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, local_translation("TEXT_SITEMAP_STARTING_WITH_HTTPS_SCHEME"))
        rating += sub_rating

def create_sitemap_dict(sitemap_items, robots_domain):
    """
    This function creates a dictionary with information about the sitemaps.

    Parameters:
    sitemap_items (list): A list of URLs in the sitemap.
    robots_domain (str): The domain specified in the robots.txt file.

    The function iterates over the sitemap items and checks if they use HTTPS only and
    if they are on the same domain as specified in the robots.txt file.
    It also checks for known extensions and counts the number of each type of item.
    The function creates a dictionary with this information and returns it.

    Returns:
    sitemap_dict (dict): A dictionary with information about the sitemaps.
    """
    nof_items = len(sitemap_items)
    nof_no_duplicates = len(list(set(sitemap_items)))

    sitemap_dict = {
        'use_https_only': True,
        'use_same_domain': True,
        'known_types': {},
        'has_duplicates': nof_items > nof_no_duplicates,
        'nof_items': nof_items,
        'nof_items_no_duplicates': nof_no_duplicates
    }

    item_types = {}

    for item_url in sitemap_items:
        item_type = 'webpage'

        if not item_url.lower().startswith('https://'):
            sitemap_dict['use_https_only'] = False

        parsed_item_url = urlparse(item_url)
        if robots_domain != parsed_item_url.hostname:
            sitemap_dict['use_same_domain'] = False

        tmp = os.path.splitext(parsed_item_url.path)[1].strip('.').lower()
        ext_len = len(tmp)
        if 2 <= ext_len >= 4:
            if tmp in KNOWN_EXTENSIONS:
                item_type = tmp
        elif parsed_item_url.path.startswith('/download/'):
            item_type = 'unknown-in-download'

        if item_type not in item_types:
            item_types[item_type] = []
        item_types[item_type].append(item_url)

    keys = sorted(list(item_types.keys()))

    for key in keys:
        sitemap_dict['known_types'][key] = len(item_types[key])

    return sitemap_dict


def is_feed(tag):
    """
    This function checks if a given tag is a feed.

    Parameters:
    tag (bs4.element.Tag): A BeautifulSoup tag object.

    The function checks if the tag is a 'link' and if it has a 'type' attribute.
    If it does, it checks if the 'type' attribute is one of the known feed types.
    If it is, the function returns True. Otherwise, it returns False.

    Returns:
    bool: True if the tag is a feed, False otherwise.
    """

    if tag.name != 'link':
        return False

    if tag.has_attr('type'):
        tag_type = tag['type']
        if 'application/rss+xml' in tag_type:
            return True
        if 'application/atom+xml' in tag_type:
            return True
        if 'application/feed+json' in tag_type:
            return True
    return False


def validate_feed(result_dict, global_translation, local_translation):
    """
    This function validates the presence of feeds in a webpage.

    Parameters:
    result_dict (dict): A dictionary containing the URL of the webpage to be validated.
    global_translation (function): A function for translating text globally.
    local_translation (function): A function for translating text locally.

    The function retrieves the content of the webpage and parses it using BeautifulSoup.
    It then finds all the feed tags in the parsed content.
    If no feeds are found, it sets the overall rating to 4.5 and adds a message for improvement.
    If feeds are found, it sets the overall rating to 5.0 and adds a positive message.
    It also stores the URLs of the feeds in the result dictionary.

    Returns:
    rating (Rating): An instance of the Rating class with the overall rating and message.
    """
    feed_dict = {
        'nof_feeds': 0,
        'feeds': []
    }
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    content = get_http_content(result_dict['url'], True, True)
    soup = BeautifulSoup(content, 'lxml')
    feeds = soup.find_all(is_feed)

    feed_dict['nof_feeds'] = len(feeds)
    if feed_dict['nof_feeds'] == 0:
        rating.set_overall(4.5, local_translation("TEXT_RSS_FEED_MISSING"))
        feed_dict['status'] = 'not in meta'
    elif feed_dict['nof_feeds'] > 0:
        rating.set_overall(5.0, local_translation("TEXT_RSS_FEED_FOUND"))
        feed_dict['status'] = 'found in meta'
        for single_feed in feeds:
            feed_dict['feeds'].append(single_feed.get('href'))

    result_dict['feeds'] = feed_dict

    return rating


def validate_security_txt(result_dict, global_translation, local_translation):
    """
    Validates the security.txt file at both the root and .well-known locations of a website.

    Parameters:
    result_dict (dict): A dictionary containing the root URL of the website.
    global_translation (function): Function to translate text globally.
    local_translation (function): Function to translate text locally.

    Returns:
    Rating: A rating object representing the overall, standards, and integrity/security ratings.
    """
    root_url = result_dict['root_url']
    security_dict = {
        'txts': {

        }
    }

    # normal location for security.txt
    security_wellknown_url = root_url + '.well-known/security.txt'
    security_wellknown_content = get_http_content(
        security_wellknown_url, True)

    # Note: security.txt can also be placed in root if
    # for example technical reasons prohibit use of /.well-known/
    security_root_url = root_url + 'security.txt'
    security_root_content = get_http_content(security_root_url, True)

    if security_wellknown_content == '' and security_root_content == '':
        # Can't find security.txt (not giving us 200 as status code)
        rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        rating.set_overall(1.0)
        rating.set_standards(1.0, local_translation("TEXT_SECURITY_MISSING"))
        rating.set_integrity_and_security(1.0, local_translation("TEXT_SECURITY_MISSING"))

        security_dict['status'] = 'missing'
        security_dict['txts'][security_wellknown_url] = {
            'status': 'missing'
        }
        security_dict['txts'][security_root_url] = {
            'status': 'missing'
        }

        result_dict['security'] = security_dict
        return rating

    security_wellknown_result = validate_securitytxt_content(
        security_wellknown_content,
        global_translation,
        local_translation)
    security_root_result = validate_securitytxt_content(
        security_root_content,
        global_translation,
        local_translation)

    security_wellknown_rating = security_wellknown_result[0]
    security_root_rating = security_root_result[0]

    security_dict['txts'][security_wellknown_url] = security_wellknown_result[1]
    security_dict['txts'][security_root_url] = security_root_result[1]
    result_dict['security'] = security_dict

    if security_wellknown_rating.get_overall() == security_root_rating.get_overall():
        result_dict['security']['status'] = security_dict['txts'][security_wellknown_url]['status']
        return security_wellknown_rating

    if security_wellknown_rating.get_overall() > security_root_rating.get_overall():
        result_dict['security']['status'] = security_dict['txts'][security_wellknown_url]['status']
        return security_wellknown_rating

    result_dict['security']['status'] = security_dict['txts'][security_root_url]['status']
    return security_root_rating


def validate_securitytxt_content(content, global_translation, local_translation):
    """
    Validates the content of a security.txt file.

    Parameters:
    content (str): The content of the security.txt file.
    global_translation (function): Function to translate text globally.
    local_translation (function): Function to translate text locally.

    Returns:
    dict: A dictionary containing the status of the security.txt content validation.
    """
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    security_dict = {}
    if content is None or ('<html' in content.lower()):
        # Html (404 page?) content instead of expected content
        rating.set_overall(1.0)
        rating.set_standards(1.0, local_translation("TEXT_SECURITY_WRONG_CONTENT"))
        rating.set_integrity_and_security(
            1.0, local_translation("TEXT_SECURITY_WRONG_CONTENT"))
        security_dict['status'] = 'wrong content'
    elif ('contact:' in content.lower() and 'expires:' in content.lower()):
        # Everything seems ok
        rating.set_overall(5.0)
        rating.set_standards(5.0, local_translation("TEXT_SECURITY_OK_CONTENT"))
        rating.set_integrity_and_security(
            5.0, local_translation("TEXT_SECURITY_OK_CONTENT"))
        security_dict['status'] = 'ok'
    elif not 'contact:' in content.lower():
        # Missing required Contact
        rating.set_overall(2.5)
        rating.set_standards(2.5, local_translation(
            "TEXT_SECURITY_REQUIRED_CONTACT_MISSING"))
        rating.set_integrity_and_security(
            2.5, local_translation("TEXT_SECURITY_REQUIRED_CONTACT_MISSING"))
        security_dict['status'] = 'required contact missing'
    elif not 'expires:' in content.lower():
        # Missing required Expires (added in version 10 of draft)
        rating.set_overall(2.5)
        rating.set_standards(2.5, local_translation(
            "TEXT_SECURITY_REQUIRED_EXPIRES_MISSING"))
        rating.set_integrity_and_security(
            4.0, local_translation("TEXT_SECURITY_REQUIRED_EXPIRES_MISSING"))
        security_dict['status'] = 'required expires missing'
    else:
        rating.set_overall(1.0, local_translation("TEXT_SECURITY_WRONG_CONTENT"))
        security_dict['status'] = 'wrong content, no contact or expires'

    return (rating, security_dict)
