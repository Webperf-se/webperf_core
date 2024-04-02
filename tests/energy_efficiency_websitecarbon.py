# -*- coding: utf-8 -*-
from datetime import datetime
import json
from decimal import Decimal
from models import Rating
from tests.utils import get_http_content, get_translation

def run_test(global_translation, lang_code, url):
    """
    Analyzes URL with Website Carbon Calculator API.
    API documentation: https://api.websitecarbon.com
    https://gitlab.com/wholegrain/carbon-api-2-0
    """

    local_translation = get_translation('energy_efficiency_websitecarbon', lang_code)

    print(local_translation("TEXT_RUNNING_TEST"))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    result_json = get_http_content(
        f'https://api.websitecarbon.com/site?url={url}')
    result_dict = json.loads(result_json)

    # print(result_json)

    green = str(result_dict['green'])
    #print("Grön?", green)

    co2 = Decimal(result_dict['statistics']['co2']['grid']['grams'])
    #print('Co2', round(co2, 2), 'gram')

    cleaner_than = int(Decimal(result_dict['cleanerThan']) * 100)
    #print("Renare än:", cleaner_than, "%")

    review = ''

    # handicap points
    co2_with_handicap = float(co2) - 0.8
    points = 5 - co2_with_handicap

    points = float("{points:.2f}")

    # print(points)

    if points <= 5:
        review = local_translation("TEXT_WEBSITE_IS_VERY_GOOD")
    elif points >= 4:
        review = local_translation("TEXT_WEBSITE_IS_GOOD")
    elif points >= 3:
        review = local_translation("TEXT_WEBSITE_IS_OK")
    elif points >= 2:
        review = local_translation("TEXT_WEBSITE_IS_BAD")
    elif points <= 1:
        review = local_translation("TEXT_WEBSITE_IS_VERY_BAD")

    review += local_translation("TEXT_GRAMS_OF_CO2").format(round(co2, 2))
    review += local_translation("TEXT_BETTER_THAN").format(cleaner_than)
    if 'false' in green.lower():
        review += local_translation("TEXT_GREEN_ENERGY_FALSE")
    elif 'true' in green.lower():
        review += local_translation("TEXT_GREEN_ENERGY_TRUE")

    rating = Rating(global_translation)
    rating.set_overall(points, review)

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)
