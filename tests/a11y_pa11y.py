# -*- coding: utf-8 -*-
# from urllib.parse import urlparse # https://docs.python.org/3/library/urllib.parse.html
import subprocess
import json
from models import Rating
import config

review_show_improvements_only = config.review_show_improvements_only


def run_test(_, langCode, url):
    """

    """

    import subprocess
    bashCommand = "pa11y-ci --reporter json {0}".format(url)
    process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()

    json_result = json.loads(output)

    result_list = list()
    if 'results' in json_result:
        result_list = json_result['results']

    num_errors = 0

    if 'errors' in json_result:
        num_errors = json_result['errors']

    return_dict = {}

    points = 0
    review_overall = ''
    review = ''

    if num_errors == 0:
        points = 5
        review_overall = '- Webbplatsen har inga uppenbara fel kring tillgänglighet!\n'
    elif num_errors == 1:
        points = 4
        review_overall = '- Webbplatsen kan bli mer tillgänglig, men är helt ok.\n'
    elif num_errors > 8:
        points = 1
        review_overall = '- Väldigt dålig tillgänglighet!\n'
    elif num_errors >= 4:
        points = 2
        review_overall = '- Dålig tillgänglighet.\n'
    elif num_errors >= 2:
        points = 3
        review_overall = '- Genomsnittlig tillgänglighet men kan bli bättre.\n'

    review += '- Antal tillgänglighetsproblem: {} st\n'.format(num_errors)
    return_dict['antal_problem'] = num_errors

    if num_errors > 0:
        review += '\nProblem:\n'

    i = 1
    old_error = ''

    errors = list()
    if url in result_list:
        errors = result_list[url]

    for error in errors:
        if 'message' in error:
            err_mess = error['message'].replace('This', 'A')
            if err_mess != old_error:
                old_error = err_mess
                review += '- {0}\n'.format(err_mess)
                if 'code' in error:
                    # '{0}-{1}'.format(error.get('code'), i)
                    key = error['code']
                    return_dict.update({key: err_mess})

            i += 1

        if i > 10:
            review += '- Info: För många unika problem för att lista alla\n'
            break

    rating = Rating(_, review_show_improvements_only)
    rating.set_overall(points, review_overall)
    rating.set_a11y(points)

    rating.a11y_review = rating.a11y_review + review

    return (rating, return_dict)


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    print(run_test('sv', 'https://webperf.se'))
