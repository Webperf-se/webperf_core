# -*- coding: utf-8 -*-
import re
from datetime import datetime, timedelta
import time
import urllib.parse
from bs4 import BeautifulSoup
from models import Rating
from tests.utils import get_http_content, get_config_or_default, get_translation

REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
DIGG_URL = 'https://www.digg.se/tdosanmalan'

checked_urls = {}
canonical = 'https://www.digg.se/tdosanmalan' # pylint: disable=invalid-name

def run_test(global_translation, lang_code, url):
    """
    Runs a test on a given URL and returns the rating and a dictionary.

    This function uses both global and local translations to print status updates.
    It parses the URL, gets the default information, checks the item,
    rates the statement, and finally returns the rating and a dictionary.

    Parameters:
    global_translation (function): A function that provides global translation.
    lang_code (str): The language code to be used for local translation.
    url (str): The URL to be tested.

    Returns:
    tuple: A tuple containing the rating (an instance of the Rating class) and a dictionary.
    """
    local_translation = get_translation('a11y_statement', lang_code)

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return_dict = {}
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    o = urllib.parse.urlparse(url)
    org_url_start = f'{o.scheme}://{o.hostname}'
    global canonical # pylint: disable=global-statement
    canonical = get_digg_report_canonical()

    start_item = get_default_info(url, '', 'url.start', 0.0, 0)
    statements = check_item(start_item, None, org_url_start, global_translation, local_translation)

    if statements is not None:
        for statement in statements:
            for item in start_item['items']:
                if statement['url'] == item['url'] and statement['depth'] > item['depth']:
                    statement['depth'] = item['depth']

            rating += rate_statement(statement, global_translation, local_translation)
            # Should we test all found urls or just best match?
            break
    else:
        info = {'called_url': url}
        rating += rate_statement(info, global_translation, local_translation)

    if not rating.isused():
        rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return (rating, {'failed': True })


    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, return_dict)


def get_digg_report_canonical():
    """
    Retrieve the canonical URL from the Digg report.

    This function fetches the content of the Digg URL and
    searches for the 'canonical' link in the HTML.
    If found, it returns the absolute URL.
    If the canonical URL is a relative URL, it is converted to an
    absolute URL using the hostname from the Digg URL.
    If no canonical link is found, it returns the Digg URL.

    Returns:
        str: The canonical URL if found, otherwise the Digg URL.
    """
    content = get_http_content(DIGG_URL)
    content_match = re.search(
        r'<link rel="canonical" href="(?P<url>[^"]+)', content)
    if content_match:
        o = urllib.parse.urlparse(DIGG_URL)
        org_url_start = f'{o.scheme}://{o.hostname}'
        url = content_match.group('url')
        if url.startswith('/'):
            url = f'{org_url_start}{url}'
        return url
    return DIGG_URL


def check_item(item, root_item, org_url_start, global_translation, local_translation):
    """
    Check an item for statements and recursively check its children if necessary.

    This function checks if an item has a statement. 
    If it does, the item is added to the statements list.
    If the item doesn't have a statement and its depth is less than 2,
    the function will recursively check the item's children.
    The function will stop checking children if more than 10 have been checked or if a
    child with a precision less than 0.5 is found.

    Args:
        item (dict): The item to be checked.
        root_item (dict): The root item of the item to be checked.
        org_url_start (str): The original URL start.
        global_translation (dict): The global translation dictionary used for checking.
        local_translation (dict): The local translation dictionary used for checking.

    Returns:
        list: A list of statements if any are found, None otherwise.
    """
    statements = []
    content = None
    if item['url'] not in checked_urls:
        content = get_http_content(item['url'], True)
        time.sleep(1)
        checked_urls[item['url']] = content
    else:
        content = checked_urls[item['url']]
        # return statements

    item['root'] = root_item
    if root_item is None:
        item['items'] = []
    else:
        item['items'] = item['root']['items']

    item['validated'] = True
    item['children'] = get_interesting_urls(
        content, org_url_start, item['depth'] + 1)

    item['content'] = content
    if has_statement(item, global_translation, local_translation):
        item['precision'] = 1.0
        statements.append(item)
    elif item['depth'] < 2:
        del item['content']
        child_index = 0
        for child_pair in item['children'].items():
            if child_index > 10:
                break
            child_index += 1
            child = child_pair[1]
            item['items'].append(child)
            if len(statements) > 0 and child['precision'] < 0.5:
                continue
            tmp = check_item(child, root_item, org_url_start, global_translation, local_translation)
            if tmp is not None:
                statements.extend(tmp)

    if len(statements) > 0:
        return statements
    return None


def has_statement(item, global_translation, local_translation):
    """
    Determine if a given item has a statement based on its rating.

    This function rates the item using global and local translations.
    If the overall rating is greater than 1, the item is considered to have a statement.

    Args:
        item (object): The item to be rated.
        global_translation (dict): The global translation dictionary used for rating.
        local_translation (dict): The local translation dictionary used for rating.

    Returns:
        bool: True if the item has a statement, False otherwise.
    """
    rating = rate_statement(item, global_translation, local_translation)
    if rating.get_overall() > 1:
        return True

    return False


def get_default_info(url, text, method, precision, depth):
    """
    Constructs a dictionary with default information.

    This function takes in several parameters,
    processes the 'text' parameter, and stores all parameters in a dictionary.

    Parameters:
    url (str): The URL to be stored in the dictionary.
    text (str): The text to be processed and stored in the dictionary.
    If provided,
    it is converted to lowercase and stripped of leading/trailing periods and hyphens.
    method (str): The method to be stored in the dictionary.
    precision (int/float): The precision value to be stored in the dictionary.
    depth (int): The depth value to be stored in the dictionary.

    Returns:
    dict: A dictionary containing the processed parameters.
    """
    result = {}

    if text is not None:
        text = text.lower().strip('.').strip('-').strip()

    result['url'] = url
    result['method'] = method
    result['precision'] = precision
    result['text'] = text
    result['depth'] = depth

    return result


def rate_statement(statement, global_translation, local_translation):
    """
    Rates an accessibility statement based on various criteria.

    The function rates the accessibility statement based on its content and various other factors
    such as the presence of a 'called_url', the compatibility text, the notification function URL,
    the unreasonably burdensome accommodation, the depth at which the statement was found, the
    evaluation method, and the updated date. The overall rating is then updated accordingly.

    Parameters:
    statement (dict): The statement to be rated.
    global_translation (function): A function that translates a given key to a global string.
    local_translation (function): A function that translates a given key to a localized string.

    Returns:
    Rating: The Rating object with the updated overall rating.
    """
    # https://www.digg.se/kunskap-och-stod/digital-tillganglighet/skapa-en-tillganglighetsredogorelse
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    if 'called_url' not in statement:
        # rating.set_overall(
        #     5.0, '- Tillgänglighetsredogörelse: {0}'.format(statement['url']))
        # rating.set_overall(
        #     5.0, '- Tillgänglighetsredogörelse hittad')
        statement_content = statement['content']
        soup = BeautifulSoup(statement_content, 'lxml')

        # STATEMENTS MUST INCLUDE (ACCORDING TO
        # https://www.digg.se/kunskap-och-stod/digital-tillganglighet/ \
        # skapa-en-tillganglighetsredogorelse ):
        # - Namnet på den offentliga aktören.
        # - Namnet på den digitala servicen (till exempel webbplatsens,
        #   e-tjänstens eller appens namn).
        # - Följsamhet till lagkraven med formuleringen:
        #       helt förenlig,
        #       delvis förenlig eller
        #       inte förenlig.
        rating += rate_compatible_text(global_translation, local_translation, soup)
        # - Detaljerad, fullständig och tydlig förteckning av innehåll som inte är tillgängligt och
        #   skälen till varför det inte är tillgängligt.
        # - Datum för bedömning av följsamhet till lagkraven.
        # - Datum för senaste uppdatering.
        # - Meddelandefunktion eller länk till sådan.
        # - Länk till DIGG:s anmälningsfunktion (https://www.digg.se/tdosanmalan).
        rating += rate_notification_function_url(global_translation, local_translation, soup)
        # - Redogörelse av innehåll som undantagits på grund av
        #   oskäligt betungande anpassning (12 §) med tydlig motivering.
        rating += rate_unreasonably_burdensome_accommodation(
            global_translation,
            local_translation,
            soup)
        # - Redogörelse av innehåll som inte omfattas av lagkraven (9 §).

        if rating.get_overall() > 1 or looks_like_statement(statement, soup):
            # - Redogörelsen ska vara lätt att hitta
            #   - Tillgänglighetsredogörelsen ska vara publicerad i ett
            #     tillgängligt format (det bör vara en webbsida).
            #   - För en webbplats ska en länk till tillgänglighetsredogörelsen finnas tydligt
            #     presenterad på webbplatsens startsida, alternativt finnas åtkomlig
            #     från alla sidor exempelvis i en sidfot.
            rating += rate_found_depth(global_translation, local_translation, statement)
            # - Utvärderingsmetod (till exempel självskattning, granskning av extern part).
            rating += rate_evaluation_method(global_translation, local_translation, soup)
            # För en webbplats som är (mer eller mindre) statisk,
            # ska tillgänglighetsredogörelsen ses över åtminstone en gång per år.
            rating += rate_updated_date(global_translation, local_translation, soup)

        tmp = rating.overall_review.replace('GOV-IGNORE', '').strip('\r\n\t ')
        if len(tmp) > 0:
            rating.overall_review = local_translation(
                'TEXT_REVIEW_ACCESSIBILITY_STATEMENT_URL').format(
                statement['url'], rating.overall_review)
    else:
        tmp = rating.overall_review.replace('GOV-IGNORE', '').strip('\r\n\t ')
        if len(tmp) > 0:
            rating.set_overall(1.0, local_translation(
                'TEXT_REVIEW_NO_ACCESSIBILITY_STATEMENT'))
            rating.overall_review = local_translation('TEXT_REVIEW_CALLED_URL').format(
                statement['called_url'], rating.overall_review)

    return rating

def find_dates(regex, element_text):
    """
    Finds all dates in a given text that match a given regular expression.

    The function uses the regular expression to find all matches in the text. It then extracts and
    returns the weighted document date from each match using the `get_waighted_doc_date_from_match`
    function.

    Parameters:
    regex (str): The regular expression to be used for finding dates.
    element_text (str): The text in which to find dates.

    Returns:
    list: A list of dictionaries, each containing the type, date, and weight of a found date.
    """
    matches = re.finditer(regex, element_text, re.IGNORECASE)
    dates = [get_waighted_doc_date_from_match(match) for match in matches]
    return dates

def rate_updated_date(global_translation, local_translation, soup):
    """
    Rates the update date of a document parsed from a BeautifulSoup object.

    The function finds all dates in the text of the 'body' element of the soup object using a set of
    regular expressions. It then rates the most recent date found based on how recent it is and
    updates the overall rating accordingly.

    Parameters:
    global_translation (function): A function that translates a given key to a global string.
    local_translation (function): A function that translates a given key to a localized string.
    soup (BeautifulSoup): The BeautifulSoup object containing the document to be rated.

    Returns:
    Rating: The Rating object with the updated overall rating.
    """
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    dates = []

    element = soup.find('body')
    if element is None:
        return rating

    element_text = element.get_text()

    regexes = [
        r"(?P<typ>bedömning|redogörelse|uppdater|gransk)(?P<text>[^>.]*) (?P<day>[0-9]{1,2} )(?P<month>(?:jan(?:uari)*|feb(?:ruari)*|mar(?:s)*|apr(?:il)*|maj|jun(?:i)*|jul(?:i)*|aug(?:usti)*|sep(?:tember)*|okt(?:ober)*|nov(?:ember)*|dec(?:ember)*) )(?P<year>20[0-9]{2})", # pylint: disable=line-too-long
        r" (?P<day>[0-9]{1,2} )(?P<month>(?:jan(?:uari)*|feb(?:ruari)*|mar(?:s)*|apr(?:il)*|maj|jun(?:i)*|jul(?:i)*|aug(?:usti)*|sep(?:tember)*|okt(?:ober)*|nov(?:ember)*|dec(?:ember)*) )(?P<year>20[0-9]{2})(?P<text>[^>.]*)(?P<typ>bedömning|redogörelse|uppdater|gransk)", # pylint: disable=line-too-long
        r"(?P<typ>bedömning|redogörelse|uppdater|gransk)(?P<text>[^>.]*) (?P<day>)(?P<month>(?:jan(?:uari)*|feb(?:ruari)*|mar(?:s)*|apr(?:il)*|maj|jun(?:i)*|jul(?:i)*|aug(?:usti)*|sep(?:tember)*|okt(?:ober)*|nov(?:ember)*|dec(?:ember)*) )(?P<year>20[0-9]{2})", # pylint: disable=line-too-long
        r" (?P<day>)(?P<month>(?:jan(?:uari)*|feb(?:ruari)*|mar(?:s)*|apr(?:il)*|maj|jun(?:i)*|jul(?:i)*|aug(?:usti)*|sep(?:tember)*|okt(?:ober)*|nov(?:ember)*|dec(?:ember)*) )(?P<year>20[0-9]{2})(?P<text>[^>.]*)(?P<typ>bedömning|redogörelse|uppdater|gransk)", # pylint: disable=line-too-long
        r"(?P<typ>bedömning|redogörelse|uppdater|gransk)(?P<text>[^>.]*) (?P<year>20[0-9]{2}-)(?P<month>[0-9]{2}-)(?P<day>[0-9]{2})", # pylint: disable=line-too-long
        r" (?P<year>20[0-9]{2}-)(?P<month>[0-9]{2}-)(?P<day>[0-9]{2})(?P<text>[^>.]*)(?P<typ>bedömning|redogörelse|uppdater|gransk)", # pylint: disable=line-too-long
        r"(?P<typ>bedömning|redogörelse|uppdater|gransk)(?P<text>[^>.]*) (?P<day>[0-9]{1,2} )*(?P<month>(?:jan(?:uari)*|feb(?:ruari)*|mar(?:s)*|apr(?:il)*|maj|jun(?:i)*|jul(?:i)*|aug(?:usti)*|sep(?:tember)*|okt(?:ober)*|nov(?:ember)*|dec(?:ember)*) )(?P<year>20[0-9]{2})", # pylint: disable=line-too-long
        r" (?P<day>[0-9]{1,2} )*(?P<month>(?:jan(?:uari)*|feb(?:ruari)*|mar(?:s)*|apr(?:il)*|maj|jun(?:i)*|jul(?:i)*|aug(?:usti)*|sep(?:tember)*|okt(?:ober)*|nov(?:ember)*|dec(?:ember)*) )(?P<year>20[0-9]{2})(?P<text>[^>.]*)(?P<typ>bedömning|redogörelse|uppdater|gransk)" # pylint: disable=line-too-long
    ]

    for regex in regexes:
        dates.extend(find_dates(regex, element_text))

    if len(dates) == 0:
        rating.set_overall(
            1.0, local_translation('TEXT_REVIEW_NO_UPDATE_DATE'))
        return rating

    dates = sorted(dates, key=get_sort_on_weight)
    date_info = dates.pop()['date']
    date_doc = datetime(date_info[0], date_info[1], date_info[2])

    rate_updated_year_date(local_translation, rating, date_doc)

    return rating

def rate_updated_year_date(local_translation, rating, date_doc):
    """
    Rates the document date based on how recent it is and updates the overall rating.

    The function calculates cutoff dates for the past 1 to 5 years.
    It then compares the document date with these cutoffs and
    sets the overall rating accordingly. The rating is set to a higher
    value if the document date is more recent.

    Parameters:
    local_translation (function): A function that translates a given key to a localized string.
    rating (Rating): The Rating object whose overall rating is to be updated.
    date_doc (datetime): The document date to be rated.

    Returns:
    None
    """
    year = 365
    delta_1_year = timedelta(days=year)
    cutoff_1_year = datetime.utcnow() - delta_1_year

    delta_2_year = timedelta(days=2*year)
    cutoff_2_year = datetime.utcnow() - delta_2_year

    delta_3_year = timedelta(days=3*year)
    cutoff_3_year = datetime.utcnow() - delta_3_year

    delta_4_year = timedelta(days=4*year)
    cutoff_4_year = datetime.utcnow() - delta_4_year

    delta_5_year = timedelta(days=5*year)
    cutoff_5_year = datetime.utcnow() - delta_5_year

    if cutoff_1_year < date_doc:
        rating.set_overall(
            5.0, local_translation('TEXT_REVIEW_IN_1YEAR_UPDATE_DATE'))
    elif cutoff_2_year < date_doc:
        rating.set_overall(
            4.5, local_translation('TEXT_REVIEW_OLDER_THAN_1YEAR_UPDATE_DATE'))
    elif cutoff_3_year < date_doc:
        rating.set_overall(
            4.0, local_translation('TEXT_REVIEW_OLDER_THAN_2YEAR_UPDATE_DATE'))
    elif cutoff_4_year < date_doc:
        rating.set_overall(
            3.0, local_translation('TEXT_REVIEW_OLDER_THAN_3YEAR_UPDATE_DATE'))
    elif cutoff_5_year < date_doc:
        rating.set_overall(
            2.0, local_translation('TEXT_REVIEW_OLDER_THAN_4YEAR_UPDATE_DATE'))
    else:
        rating.set_overall(
            1.5, local_translation('TEXT_REVIEW_OLDER_THAN_5YEAR_UPDATE_DATE'))


def get_waighted_doc_date_from_match(match):
    """
    Extracts and returns the weighted document date from a given match object.

    The function parses the 'typ', 'day', 'month', and 'year' groups from the match object,
    applies necessary transformations,
    and calculates a weight for the date based on the 'typ' remark.

    Parameters:
    match (re.Match): The match object containing groups 'typ', 'day', 'month', and 'year'.

    Returns:
    dict: A dictionary containing:
        - 'type': The type of the document, extracted from the 'typ' group of the match.
        - 'date': A tuple (year, month, day) representing the document date.
        - 'weight': A float representing the weight of the date.
    """
    weight = 0.3
    remark = match.group('typ')
    if remark is not None:
        remark = remark.strip().lower()
    day = match.group('day')
    month = match.group('month')
    year = match.group('year')
    if year is not None:
        year = int(year.strip().strip('-'))
    if month is not None:
        month = month.strip().strip('-').lower()
        month = convert_to_month_number(month)

    if day is not None and day != '':
        day = int(day.strip().strip('-'))
    else:
        day = 1
        weight = 0.1

    tmp_weight = get_date_weight(remark)
    if tmp_weight is not None:
        weight = tmp_weight

    return {
        'type': remark,
        'date': (year, month, day),
        'weight': weight
    }

def convert_to_month_number(month):
    """
    This function converts a month name or number to a month number.

    It checks if the input month starts with any of the short month names in
    a predefined dictionary and returns the corresponding month number.
    If the input month does not start with any of the short month 
    names, it returns the input month converted to an integer.

    Parameters:
    month (str or int): The month name or number to be converted.

    Returns:
    int: The month number.
    """
    month_dict = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 
        'maj': 5, 'jun': 6, 'jul': 7, 'aug': 8, 
        'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12
    }
    for short_month_name, month_number in month_dict.items():
        if month.lower().startswith(short_month_name):
            return month_number
    return int(month)


def looks_like_statement(statement, soup):
    """
    This function checks if a given statement looks like a valid statement.

    It searches for specific strings in the 'soup' object's 'h1' and 'title' tags and
    checks the 'precision' attribute of the statement.
    The function returns True if any of these conditions are met.

    Parameters:
    statement (dict): The statement containing the 'precision' attribute to be checked.
    soup (BeautifulSoup object): The parsed HTML document to search.

    Returns:
    bool: True if the statement looks like a valid statement, False otherwise.
    """
    element = soup.find('h1', string=re.compile(
        "tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog(.{1,6}|ö|&ouml;|&#246;)relse",
        flags=re.MULTILINE | re.IGNORECASE))
    if element:
        return True

    element = soup.find('title', string=re.compile(
        "tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog(.{1,6}|ö|&ouml;|&#246;)relse",
        flags=re.MULTILINE | re.IGNORECASE))
    if element:
        return True

    if statement['precision'] >= 0.5:
        return True

    return False


def rate_found_depth(global_translation, local_translationl, statement):
    """
    This function rates the depth of a given statement.

    It checks the 'depth' attribute of the statement and assigns ratings based on its value.
    The function returns a 'Rating' object with the overall rating set.

    Parameters:
    global_translation (function): A function to translate text to a global language.
    local_translationl (function): A function to translate text to a local language.
    statement (dict): The statement containing the 'depth' attribute to be rated.

    Returns:
    rating (Rating object): The 'Rating' object with the overall rating set.
    """
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    depth = statement["depth"]

    if depth == 1:
        rating.set_overall(
            5.0, local_translationl('TEXT_REVIEW_LINK_STARTPAGE'))
    elif depth > 1:
        rating.set_overall(
            3.0, local_translationl('TEXT_REVIEW_LINK_OTHER'))

    return rating


def rate_evaluation_method(global_translation, local_translation, soup):
    """
    This function rates the evaluation method used in a given context.

    It searches for specific strings related to various evaluation methods in
    the provided 'soup' object and assigns ratings based on the findings.
    The function returns a 'Rating' object with the overall 
    rating set.

    Parameters:
    global_translation (function): A function to translate text to a global language.
    local_translation (function): A function to translate text to a local language.
    soup (BeautifulSoup object): The parsed HTML document to search.

    Returns:
    rating (Rating object): The 'Rating' object with the overall rating set.
    """
    match = soup.find(string=re.compile(
        "(sj(.{1, 6}|ä|&auml;|&#228;)lvskattning|intern[a]{0,1} kontroller|intern[a]{0,1} test(ning|er){0,1}]|utvärderingsmetod|tillgänglighetsexpert(er){0,1}|funka|etu ab|siteimprove|oberoende granskning|oberoende tillgänglighetsgranskning(ar){0,1}|tillgänglighetskonsult(er){0,1}|med hjälp av|egna tester|oberoende experter|Hur vi testat webbplats(en){0,1}|vi testat webbplatsen|intervjuer|rutiner|checklistor|checklista|utbildningar|automatiserade|automatisk|maskinell|kontrollverktyg)", # pylint: disable=line-too-long
        flags=re.MULTILINE | re.IGNORECASE))
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if match:
        rating.set_overall(
            5.0, local_translation('TEXT_REVIEW_EVALUATION_METHOD_FOUND'))
    else:
        rating.set_overall(
            1.0, local_translation('TEXT_REVIEW_EVALUATION_METHOD_NOT_FOUND'))

    return rating


def rate_unreasonably_burdensome_accommodation(global_translation, local_translation, soup):
    """
    This function rates whether an accommodation is unreasonably burdensome.

    It searches for specific strings in the provided 'soup' object and
    assigns ratings based on the findings. The ratings are based on the presence or
    absence of the terms "Oskäligt betungande anpassning" or 
    "12 § lagen". The function returns a 'Rating' object with the overall and
    accessibility ratings set.

    Parameters:
    global_translation (function): A function to translate text to a global language.
    local_translation (function): A function to translate text to a local language.
    soup (BeautifulSoup object): The parsed HTML document to search.

    Returns:
    rating (Rating object): The 'Rating' object with the overall and accessibility ratings set.
    """
    match = soup.find(string=re.compile(
        "(Oskäligt betungande anpassning|12[ \t\r\n]§ lagen)", flags=re.MULTILINE | re.IGNORECASE))
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if match:
        rating.set_overall(
            5.0, local_translation('TEXT_REVIEW_ADAPTATION_FOUND'))
        rating.set_a11y(
            4.0, local_translation('TEXT_REVIEW_ADAPTATION_FOUND'))
    else:
        # rating.set_overall(
        #     5.0, '- Anger ej oskäligt betungande anpassning (12 §)')
        rating.set_a11y(
            5.0, local_translation('TEXT_REVIEW_ADAPTATION_NOT_FOUND'))

    return rating


def rate_notification_function_url(global_translation, local_translation, soup):
    """
    Rates the notification function URL based on its presence and correctness.

    This function checks the HTML content for the presence of specific URLs and assigns a rating
    based on the match. The rating is determined by the 'correctness' of the URL, which is defined
    by specific patterns found in the HTML content. The function uses regex for pattern matching
    and BeautifulSoup for HTML parsing.

    Parameters:
    global_translation (function): A function to translate global text.
    local_translation (function): A function to translate local text.
    soup (BeautifulSoup): A BeautifulSoup object containing the parsed HTML content.

    Returns:
    Rating: A Rating object containing the overall rating of the URL.
    """
    match_correct_url = soup.find(href=DIGG_URL)

    match_canonical_url = soup.find(href=canonical)

    match_old_reference = soup.find(href=re.compile(
        "digg\\.se[a-z\\/\\-]+anmal\\-bristande\\-tillganglighet",
        flags=re.MULTILINE | re.IGNORECASE))

    is_digg = False
    for i in soup.select('link[rel*=canonical]'):
        if 'digg.se' in i['href']:
            is_digg = True
    if is_digg:
        # NOTE: digg.se has of course all links relative. This is a fix for that..
        match_canonical_url = soup.find('main').find(
            href=canonical.replace('https://www.digg.se', ''))

    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if match_correct_url:
        rating.set_overall(
            5.0, local_translation('TEXT_REVIEW_NOTIFICATION_FUNCTION_URL_FOUND'))
    elif match_canonical_url:
        rating.set_overall(
            5.0, local_translation('TEXT_REVIEW_NOTIFICATION_FUNCTION_CANONICAL_URL_FOUND'))
    elif match_old_reference:
        rating.set_overall(
            4.5, local_translation('TEXT_REVIEW_NOTIFICATION_FUNCTION_OLD_URL_FOUND'))
    else:
        rating.set_overall(
            1.0, local_translation('TEXT_REVIEW_NOTIFICATION_FUNCTION_URL_NOT_FOUND'))

    return rating


def rate_compatible_text(global_translation, local_translation, soup):
    """
    Rates the compatibility of a text based on its content.

    This function searches for specific patterns in the text and
    assigns a rating based on the match.
    The rating is determined by the 'compatibility' of the text,
    which is defined by specific keywords found in the text.
    The function uses regex for pattern matching and BeautifulSoup for HTML parsing.

    Parameters:
    global_translation (function): A function to translate global text.
    local_translation (function): A function to translate local text.
    soup (BeautifulSoup): A BeautifulSoup object containing the parsed HTML content.

    Returns:
    Rating: A Rating object containing the overall and accessibility (a11y) ratings of the text.
    """
    element = soup.find(string=re.compile(
        "(?P<test>helt|delvis|inte) förenlig", flags=re.MULTILINE | re.IGNORECASE))
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if element:
        text = element.get_text()
        regex = r'(?P<test>helt|delvis|inte) förenlig'
        match = re.search(regex, text, flags=re.IGNORECASE)
        test = match.group('test').lower()
        if 'inte' in test:
            rating.set_overall(
                5.0, local_translation('TEXT_REVIEW_COMPATIBLE_TEXT_OVERALL_NOT_COMPATIBLE'))
            rating.set_a11y(
                1.0, local_translation('TEXT_REVIEW_COMPATIBLE_TEXT_A11Y_NOT_COMPATIBLE'))
        elif 'delvis' in test:
            rating.set_overall(
                5.0, local_translation('TEXT_REVIEW_COMPATIBLE_TEXT_OVERALL_PARTLY_COMPATIBLE'))
            rating.set_a11y(
                3.0, local_translation('TEXT_REVIEW_COMPATIBLE_TEXT_A11Y_PARTLY_COMPATIBLE'))
        else:
            rating.set_overall(
                5.0, local_translation('TEXT_REVIEW_COMPATIBLE_TEXT_OVERALL_FULL_COMPATIBLE'))
            rating.set_a11y(
                5.0, local_translation('TEXT_REVIEW_COMPATIBLE_TEXT_A11Y_FULL_COMPATIBLE'))
    else:
        rating.set_overall(
            1.0, local_translation('TEXT_REVIEW_COMPATIBLE_TEXT_OVERALL_NOT_FOUND'))

    return rating


def get_sort_on_precision(item):
    """
    Returns the precision value of a given item for sorting purposes.

    This function is typically used as a key function when sorting a list of items based on their
    precision values.

    Parameters:
    item (tuple): The item to extract the precision value from. The item is expected to be a tuple
    where the second element is a dictionary containing a "precision" key.

    Returns:
    float: The precision value of the item.
    """
    return item[1]["precision"]


def get_sort_on_weight(item):
    """
    Returns the weight value of a given item for sorting purposes.

    This function is typically used as a key function when sorting a list of items based on their
    weight values.

    Parameters:
    item (dict): The item to extract the weight value from. The item is expected to be a dictionary
    containing a "weight" key.

    Returns:
    float: The weight value of the item.
    """
    return item["weight"]

def get_date_weight(text):
    """
    Determines the weight of a given text based on matching patterns.

    This function checks the input text against a list of predefined regex patterns. Each pattern is
    associated with a weight value. If the text matches a pattern, the corresponding weight
    value is returned.

    Parameters:
    text (str): The text to check for weight.

    Returns:
    float: The weight of the text. If no pattern matches, None is returned.

    Note:
    The function uses regex for pattern matching.
    """
    patterns = [
        {
            'regex': r'bedömning',
            'weight': 1.0
        },
        {
            'regex': r'redogörelse',
            'weight': 0.9
        },
        {
            'regex': r'gransk',
            'weight': 0.7
        },
        {
            'regex': r'uppdater',
            'weight': 0.5
        }
    ]

    for pattern in patterns:
        if re.match(pattern['regex'], text, flags=re.MULTILINE | re.IGNORECASE) is not None:
            return pattern['weight']

    return None

def get_text_precision(text):
    """
    Determines the precision of a given text based on matching patterns.

    This function checks the input text against a list of predefined regex patterns. Each pattern is
    associated with a precision value. If the text matches a pattern, the corresponding precision
    value is returned.

    Parameters:
    text (str): The text to check for precision.

    Returns:
    float: The precision of the text. If no pattern matches, a default precision of 0.1 is returned.

    Note:
    The function uses regex for pattern matching.
    """
    patterns = [
        {
            'regex': r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog(.{1,6}|ö|&ouml;|&#246;)relse$', # pylint: disable=line-too-long
            'precision': 0.55
        },
        {
            'regex': r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog(.{1,6}|ö|&ouml;|&#246;)relse', # pylint: disable=line-too-long
            'precision': 0.5
        },
        {
            'regex': r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighet$', # pylint: disable=line-too-long
            'precision': 0.4
        },
        {
            'regex': r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighet', # pylint: disable=line-too-long
            'precision': 0.35
        },
        {
            'regex': r'tillg(.{1,6}|ä|&auml;|&#228;)nglighet', # pylint: disable=line-too-long
            'precision': 0.3
        },
        {
            'regex': r'om webbplats', # pylint: disable=line-too-long
            'precision': 0.29
        },
        {
            'regex': r'^[ \t\r\n]*om [a-z]+$', # pylint: disable=line-too-long
            'precision': 0.25
        },
        {
            'regex': r'^[ \t\r\n]*om [a-z]+', # pylint: disable=line-too-long
            'precision': 0.2
        }
    ]

    for pattern in patterns:
        if re.match(pattern['regex'], text, flags=re.MULTILINE | re.IGNORECASE) is not None:
            return pattern['precision']

    return 0.1


def get_interesting_urls(content, org_url_start, depth):
    """
    Extracts and returns interesting URLs from the given HTML content.

    This function parses the HTML content, finds all anchor tags,
    and filters out URLs based on certain criteria.
    The URLs are then sorted based on the precision of the text associated with each URL.

    Parameters:
    content (str): The HTML content to parse.
    org_url_start (str): The original URL start for relative URL resolution.
    depth (int): The depth of the URL in the website hierarchy.

    Returns:
    dict: A dictionary of URLs as keys and their associated information as values. If no interesting
    URLs are found, an empty dictionary is returned.

    Note:
    The function uses BeautifulSoup for HTML parsing and regex for URL filtering.
    """
    urls = {}

    soup = BeautifulSoup(content, 'lxml')
    links = soup.find_all("a")

    for link in links:
        if not link.find(string=re.compile(
                r"(om [a-z]+|(tillg(.{1,6}|ä|&auml;|&#228;)nglighet(sredog(.{1,6}|ö|&ouml;|&#246;)relse){0,1}))", # pylint: disable=line-too-long
                flags=re.MULTILINE | re.IGNORECASE)):
            continue

        url = f"{link.get('href')}"

        if url is None:
            continue
        if url.endswith('.pdf'):
            continue
        if url.startswith('//'):
            continue
        if url.startswith('/'):
            url = f'{org_url_start}{url}'
        if url.startswith('#'):
            continue

        if not url.startswith(org_url_start):
            continue

        text = link.get_text().strip()

        precision =  get_text_precision(text)

        info = get_default_info(
            url, text, 'url.text', precision, depth)
        if url not in checked_urls:
            urls[url] = info

    if len(urls) > 0:
        urls = dict(
            sorted(urls.items(), key=get_sort_on_precision, reverse=True))
        return urls
    return urls
