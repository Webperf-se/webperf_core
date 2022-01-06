# -*- coding: utf-8 -*-
from models import Rating
import sys
import json
from tests.utils import *


def run_test(_, langCode, url, googlePageSpeedApiKey, strategy, category, review_show_improvements_only):
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

    # look for words indicating items is related to standard
    standard_strings = ['gzip, deflate',
                        'Deprecated', 'Utfasade ', 'quirks-mode']

    return_dict = {}
    weight_dict = {}
    rating = Rating(_, review_show_improvements_only)

    # Service score (0-100)
    score = json_content['lighthouseResult']['categories'][category]['score']

    total_weight = 0
    for item in json_content['lighthouseResult']['categories'][category]['auditRefs']:
        total_weight += item['weight']
        weight_dict[item['id']] = item['weight']

    # change it to % and convert it to a 1-5 grading
    points = 5.0 * float(score)
    reviews = []

    for item in json_content['lighthouseResult']['audits'].keys():
        try:
            if 'numericValue' in json_content['lighthouseResult']['audits'][item]:
                return_dict[item] = json_content['lighthouseResult']['audits'][item]['numericValue']

            local_score = float(
                json_content['lighthouseResult']['audits'][item]['score'])

            local_points = 5.0 * local_score
            if local_points < 1.0:
                local_points = 1
            if local_points >= 4.95:
                local_points = 5.0

            item_review = ''
            item_title = '{0}'.format(
                json_content['lighthouseResult']['audits'][item]['title'])
            displayValue = ''
            item_description = json_content['lighthouseResult']['audits'][item]['description']
            if 'displayValue' in json_content['lighthouseResult']['audits'][item]:
                displayValue = json_content['lighthouseResult']['audits'][item]['displayValue']
            if local_score == 0:
                item_review = "- {0}".format(
                    _(item_title))
            elif local_points == 5.0:
                item_review = "- {0}".format(
                    _(item_title))
            else:
                item_review = "- {0}: {1}".format(
                    _(item_title), displayValue)

            reviews.append([local_points - weight_dict[item],
                            item_review, local_points])

            for insecure_str in insecure_strings:
                if insecure_str in item_review or insecure_str in item_description:

                    local_rating = Rating(_, review_show_improvements_only)
                    if local_score == 1:
                        local_rating.set_integrity_and_security(
                            5.0, '- {0}'.format(item_title))
                    else:
                        local_rating.set_integrity_and_security(
                            1.0, '- {0}'.format(item_title))
                    rating += local_rating
                    break
            for standard_str in standard_strings:
                if standard_str in item_review or standard_str in item_description:
                    local_rating = Rating(_, review_show_improvements_only)
                    if local_score == 1:
                        local_rating.set_standards(
                            5.0, '- {0}'.format(item_title))
                    else:
                        local_rating.set_standards(
                            1.0, '- {0}'.format(item_title))
                    rating += local_rating
                    break

        except:
            # has no 'numericValue'
            #print(item, 'har inget värde')
            pass

    reviews.sort()
    for review_item in reviews:
        review_rating = Rating(_, review_show_improvements_only)
        review_rating.set_overall(review_item[2], review_item[1])
        rating += review_rating
    review = rating.overall_review

    if category == 'performance':
        rating.set_overall(points)
        rating.set_performance(points)
        rating.performance_review = review
    elif category == 'accessibility':
        rating.set_overall(points)
        rating.set_a11y(points)
        rating.a11y_review = review
    else:
        rating.set_overall(points)
        rating.overall_review = review
    rating.overall_count = 1

    return (rating, return_dict)
