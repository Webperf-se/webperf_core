# -*- coding: utf-8 -*-
from models import Rating
import sys
import json
from tests.utils import *


def run_test(_, langCode, url, googlePageSpeedApiKey, strategy, category):
    """
    perf = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=performance&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    a11y = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=accessibility&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    practise = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=best-practices&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    pwa = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=pwa&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    seo = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=seo&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    """

    check_url = url.strip()

    pagespeed_api_request = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed?locale={4}&category={0}&url={1}&strategy={2}&key={3}'.format(
        category, check_url, strategy, googlePageSpeedApiKey, langCode)
    get_content = ''

    # print('pagespeed_api_request: {0}'.format(pagespeed_api_request))

    try:
        get_content = httpRequestGetContent(pagespeed_api_request)
    except:  # breaking and hoping for more luck with the next URL
        print(
            'Error! Unfortunately the request for URL "{0}" failed, message:\n{1}'.format(
                check_url, sys.exc_info()[0]))
        pass

    json_content = ''

    try:
        json_content = json.loads(get_content)
    except:  # might crash if checked resource is not a webpage
        print('Error! JSON failed parsing for the URL "{0}"\nMessage:\n{1}'.format(
            check_url, sys.exc_info()[0]))
        pass

    # look for words indicating item is insecure
    insecure_strings = ['security', 'säkerhet',
                        'insecure', 'osäkra', 'unsafe', 'insufficient security', 'otillräckliga säkerhetskontroller', 'HTTPS']

    standard_strings = ['gzip, deflate',
                        'Deprecated', 'Utfasade ', 'quirks-mode']

    review = ''
    return_dict = {}
    rating = Rating(_)

    # Service score (0-100)
    score = json_content['lighthouseResult']['categories'][category]['score']
    # change it to % and convert it to a 1-5 grading
    points = 5.0 * float(score)

    for item in json_content['lighthouseResult']['audits'].keys():
        try:
            if 'numericValue' in json_content['lighthouseResult']['audits'][item]:
                return_dict[item] = json_content['lighthouseResult']['audits'][item]['numericValue']

            local_score = int(
                json_content['lighthouseResult']['audits'][item]['score'])

            item_review = ''
            item_title = '- {0}'.format(
                json_content['lighthouseResult']['audits'][item]['title'])
            item_description = json_content['lighthouseResult']['audits'][item]['description']
            if 'displayValue' in json_content['lighthouseResult']['audits'][item]:
                item_displayvalue = json_content['lighthouseResult']['audits'][item]['displayValue']
                item_review = _(
                    "{0} - {1}").format(item_title, item_displayvalue)
            else:
                item_review = _(item_title)

            if local_score != 1:
                review += item_review + '\r\n'

            for insecure_str in insecure_strings:
                if insecure_str in item_review or insecure_str in item_description:
                    local_rating = Rating(_)
                    if local_score == 1:
                        local_rating.set_integrity_and_security(
                            5.0, '{0}: {1}\r\n'.format(item_title, 5.0))
                    else:
                        local_rating.set_integrity_and_security(
                            1.0, '{0}: {1}\r\n'.format(item_title, 1.0))
                    rating += local_rating
                    break
            for standard_str in standard_strings:
                if standard_str in item_review or standard_str in item_description:
                    local_rating = Rating(_)
                    if local_score == 1:
                        local_rating.set_standards(
                            5.0, '{0}: {1}\r\n'.format(item_title, 5.0))
                    else:
                        local_rating.set_standards(
                            1.0, '{0}: {1}\r\n'.format(item_title, 1.0))
                    rating += local_rating
                    break

        except:
            # has no 'numericValue'
            #print(item, 'har inget värde')
            pass

    rating.set_overall(points, review)
    if category == 'performance':
        rating.set_performance(points, review)

    return (rating, return_dict)
