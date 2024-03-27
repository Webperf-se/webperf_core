# -*- coding: utf-8 -*-
import re
from datetime import datetime, timedelta
import time
import urllib.parse
from bs4 import BeautifulSoup
from models import Rating
from tests.utils import get_http_content, get_config_or_default, get_translation

review_show_improvements_only = get_config_or_default('review_show_improvements_only')
checked_urls = {}
digg_url = 'https://www.digg.se/tdosanmalan'
canonical = 'https://www.digg.se/tdosanmalan'


def run_test(global_translation, lang_code, url):
    """

    """

    local_translation = get_translation('a11y_statement', lang_code)

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return_dict = {}
    rating = Rating(global_translation, review_show_improvements_only)

    o = urllib.parse.urlparse(url)
    org_url_start = f'{o.scheme}://{o.hostname}'
    global canonical
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

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, return_dict)


def get_digg_report_canonical():
    content = get_http_content(digg_url)
    content_match = re.search(
        r'<link rel="canonical" href="(?P<url>[^"]+)', content)
    if content_match:
        o = urllib.parse.urlparse(digg_url)
        org_url_start = f'{o.scheme}://{o.hostname}'
        url = content_match.group('url')
        if url.startswith('/'):
            url = f'{org_url_start}{url}'
        return url
    else:
        return digg_url


def check_item(item, root_item, org_url_start, global_translation, local_translation):
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
    rating = rate_statement(item, global_translation, local_translation)
    if rating.get_overall() > 1:
        return True

    return False


def get_default_info(url, text, method, precision, depth):
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
    # https://www.digg.se/kunskap-och-stod/digital-tillganglighet/skapa-en-tillganglighetsredogorelse
    rating = Rating(global_translation, review_show_improvements_only)

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


def rate_updated_date(global_translation, local_translation, soup):
    rating = Rating(global_translation, review_show_improvements_only)
    dates = []

    element = soup.find('body')
    if element is None:
        return rating

    element_text = element.get_text()

    date_doc = None

    regex = r"(?P<typ>bedömning|redogörelse|uppdater|gransk)(?P<text>[^>.]*) (?P<day>[0-9]{1,2} )(?P<month>(?:jan(?:uari)*|feb(?:ruari)*|mar(?:s)*|apr(?:il)*|maj|jun(?:i)*|jul(?:i)*|aug(?:usti)*|sep(?:tember)*|okt(?:ober)*|nov(?:ember)*|dec(?:ember)*) )(?P<year>20[0-9]{2})"
    matches = re.finditer(regex, element_text, re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        dates.append(get_doc_date_from_match(match))

    regex = r" (?P<day>[0-9]{1,2} )(?P<month>(?:jan(?:uari)*|feb(?:ruari)*|mar(?:s)*|apr(?:il)*|maj|jun(?:i)*|jul(?:i)*|aug(?:usti)*|sep(?:tember)*|okt(?:ober)*|nov(?:ember)*|dec(?:ember)*) )(?P<year>20[0-9]{2})(?P<text>[^>.]*)(?P<typ>bedömning|redogörelse|uppdater|gransk)"
    matches = re.finditer(regex, element_text, re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        dates.append(get_doc_date_from_match(match))

    regex = r"(?P<typ>bedömning|redogörelse|uppdater|gransk)(?P<text>[^>.]*) (?P<day>)(?P<month>(?:jan(?:uari)*|feb(?:ruari)*|mar(?:s)*|apr(?:il)*|maj|jun(?:i)*|jul(?:i)*|aug(?:usti)*|sep(?:tember)*|okt(?:ober)*|nov(?:ember)*|dec(?:ember)*) )(?P<year>20[0-9]{2})"
    matches = re.finditer(regex, element_text, re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        dates.append(get_doc_date_from_match(match))

    regex = r" (?P<day>)(?P<month>(?:jan(?:uari)*|feb(?:ruari)*|mar(?:s)*|apr(?:il)*|maj|jun(?:i)*|jul(?:i)*|aug(?:usti)*|sep(?:tember)*|okt(?:ober)*|nov(?:ember)*|dec(?:ember)*) )(?P<year>20[0-9]{2})(?P<text>[^>.]*)(?P<typ>bedömning|redogörelse|uppdater|gransk)"
    matches = re.finditer(regex, element_text, re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        dates.append(get_doc_date_from_match(match))

    regex = r"(?P<typ>bedömning|redogörelse|uppdater|gransk)(?P<text>[^>.]*) (?P<year>20[0-9]{2}-)(?P<month>[0-9]{2}-)(?P<day>[0-9]{2})"
    matches = re.finditer(regex, element_text, re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        dates.append(get_doc_date_from_match(match))

    regex = r" (?P<year>20[0-9]{2}-)(?P<month>[0-9]{2}-)(?P<day>[0-9]{2})(?P<text>[^>.]*)(?P<typ>bedömning|redogörelse|uppdater|gransk)"
    matches = re.finditer(regex, element_text, re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        dates.append(get_doc_date_from_match(match))

    regex = r"(?P<typ>bedömning|redogörelse|uppdater|gransk)(?P<text>[^>.]*) (?P<day>[0-9]{1,2} )*(?P<month>(?:jan(?:uari)*|feb(?:ruari)*|mar(?:s)*|apr(?:il)*|maj|jun(?:i)*|jul(?:i)*|aug(?:usti)*|sep(?:tember)*|okt(?:ober)*|nov(?:ember)*|dec(?:ember)*) )(?P<year>20[0-9]{2})"
    matches = re.finditer(regex, element_text, re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        dates.append(get_doc_date_from_match(match))

    regex = r" (?P<day>[0-9]{1,2} )*(?P<month>(?:jan(?:uari)*|feb(?:ruari)*|mar(?:s)*|apr(?:il)*|maj|jun(?:i)*|jul(?:i)*|aug(?:usti)*|sep(?:tember)*|okt(?:ober)*|nov(?:ember)*|dec(?:ember)*) )(?P<year>20[0-9]{2})(?P<text>[^>.]*)(?P<typ>bedömning|redogörelse|uppdater|gransk)"
    matches = re.finditer(regex, element_text, re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        dates.append(get_doc_date_from_match(match))

    if len(dates) == 0:
        rating.set_overall(
            1.0, local_translation('TEXT_REVIEW_NO_UPDATE_DATE'))
        return rating

    dates = sorted(dates, key=get_sort_on_weight)
    date_info = dates.pop()['date']
    date_doc = datetime(date_info[0], date_info[1], date_info[2])

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

    return rating


def get_doc_date_from_match(match):
    weight = 0.3
    type = match.group('typ')
    if type is not None:
        type = type.strip().lower()
    day = match.group('day')
    month = match.group('month')
    year = match.group('year')
    if year is not None:
        year = int(year.strip().strip('-'))
    if month is not None:
        month = month.strip().strip('-').lower()
        if 'jan' in month:
            month = 1
        elif 'feb' in month:
            month = 2
        elif 'mar' in month:
            month = 3
        elif 'apr' in month:
            month = 4
        elif 'maj' in month:
            month = 5
        elif 'jun' in month:
            month = 6
        elif 'jul' in month:
            month = 7
        elif 'aug' in month:
            month = 8
        elif 'sep' in month:
            month = 9
        elif 'okt' in month:
            month = 10
        elif 'nov' in month:
            month = 11
        elif 'dec' in month:
            month = 12
        else:
            month = int(month)

    if day is not None and day != '':
        day = int(day.strip().strip('-'))
    else:
        day = 1
        weight = 0.1
    if 'bedömning' in type:
        weight = 1.0
    elif 'redogörelse' in type:
        weight = 0.9
    elif 'gransk' in type:
        weight = 0.7
    elif 'uppdater' in type:
        weight = 0.5
    return {
        'type': type,
        'date': (year, month, day),
        'weight': weight
    }


def looks_like_statement(statement, soup):
    element = soup.find('h1', string=re.compile(
        "tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog(.{1,6}|ö|&ouml;|&#246;)relse", flags=re.MULTILINE | re.IGNORECASE))
    if element:
        return True

    element = soup.find('title', string=re.compile(
        "tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog(.{1,6}|ö|&ouml;|&#246;)relse", flags=re.MULTILINE | re.IGNORECASE))
    if element:
        return True

    if statement['precision'] >= 0.5:
        return True

    return False


def rate_found_depth(global_translation, local_translationl, statement):
    rating = Rating(global_translation, review_show_improvements_only)

    depth = statement["depth"]

    if depth == 1:
        rating.set_overall(
            5.0, local_translationl('TEXT_REVIEW_LINK_STARTPAGE'))
    elif depth > 1:
        rating.set_overall(
            3.0, local_translationl('TEXT_REVIEW_LINK_OTHER'))

    return rating


def rate_evaluation_method(global_translation, local_translation, soup):
    match = soup.find(string=re.compile(
        "(sj(.{1, 6}|ä|&auml;|&#228;)lvskattning|intern[a]{0,1} kontroller|intern[a]{0,1} test(ning|er){0,1}]|utvärderingsmetod|tillgänglighetsexpert(er){0,1}|funka|etu ab|siteimprove|oberoende granskning|oberoende tillgänglighetsgranskning(ar){0,1}|tillgänglighetskonsult(er){0,1}|med hjälp av|egna tester|oberoende experter|Hur vi testat webbplats(en){0,1}|vi testat webbplatsen|intervjuer|rutiner|checklistor|checklista|utbildningar|automatiserade|automatisk|maskinell|kontrollverktyg)", flags=re.MULTILINE | re.IGNORECASE))
    rating = Rating(global_translation, review_show_improvements_only)
    if match:
        rating.set_overall(
            5.0, local_translation('TEXT_REVIEW_EVALUATION_METHOD_FOUND'))
    else:
        rating.set_overall(
            1.0, local_translation('TEXT_REVIEW_EVALUATION_METHOD_NOT_FOUND'))

    return rating


def rate_unreasonably_burdensome_accommodation(global_translation, local_translation, soup):
    match = soup.find(string=re.compile(
        "(Oskäligt betungande anpassning|12[ \t\r\n]§ lagen)", flags=re.MULTILINE | re.IGNORECASE))
    rating = Rating(global_translation, review_show_improvements_only)
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
    match_correct_url = soup.find(href=digg_url)

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

    rating = Rating(global_translation, review_show_improvements_only)
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
    element = soup.find(string=re.compile(
        "(?P<test>helt|delvis|inte) förenlig", flags=re.MULTILINE | re.IGNORECASE))
    rating = Rating(global_translation, review_show_improvements_only)
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
    return item[1]["precision"]


def get_sort_on_weight(item):
    return item["weight"]


def get_interesting_urls(content, org_url_start, depth):
    urls = {}

    soup = BeautifulSoup(content, 'lxml')
    links = soup.find_all("a")

    for link in links:
        if not link.find(string=re.compile(
                r"(om [a-z]+|(tillg(.{1,6}|ä|&auml;|&#228;)nglighet(sredog(.{1,6}|ö|&ouml;|&#246;)relse){0,1}))", flags=re.MULTILINE | re.IGNORECASE)):
            continue

        url = f"{link.get('href')}"

        if url is None:
            continue
        elif url.endswith('.pdf'):
            continue
        elif url.startswith('//'):
            continue
        elif url.startswith('/'):
            url = f'{org_url_start}{url}'
        elif url.startswith('#'):
            continue

        if not url.startswith(org_url_start):
            continue

        text = link.get_text().strip()

        precision = 0.0
        if re.match(r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog(.{1,6}|ö|&ouml;|&#246;)relse$', text, flags=re.MULTILINE | re.IGNORECASE) is not None:
            precision = 0.55
        elif re.match(r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog(.{1,6}|ö|&ouml;|&#246;)relse', text, flags=re.MULTILINE | re.IGNORECASE) is not None:
            precision = 0.5
        elif re.match(r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighet$', text, flags=re.MULTILINE | re.IGNORECASE) is not None:
            precision = 0.4
        elif re.match(r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighet', text, flags=re.MULTILINE | re.IGNORECASE) is not None:
            precision = 0.35
        elif re.match(r'tillg(.{1,6}|ä|&auml;|&#228;)nglighet', text, flags=re.MULTILINE | re.IGNORECASE) is not None:
            precision = 0.3
        elif re.search(r'om webbplats', text, flags=re.MULTILINE | re.IGNORECASE) is not None:
            precision = 0.29
        elif re.match(r'^[ \t\r\n]*om [a-z]+$', text, flags=re.MULTILINE | re.IGNORECASE) is not None:
            precision = 0.25
        elif re.match(r'^[ \t\r\n]*om [a-z]+', text, flags=re.MULTILINE | re.IGNORECASE) is not None:
            precision = 0.2
        else:
            precision = 0.1

        info = get_default_info(
            url, text, 'url.text', precision, depth)
        if url not in checked_urls:
            urls[url] = info

    if len(urls) > 0:
        urls = dict(
            sorted(urls.items(), key=get_sort_on_precision, reverse=True))
        return urls
    return urls
