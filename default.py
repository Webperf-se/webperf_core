#-*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from sqlalchemy import text
import datetime

from checks import *
from crawler import harvest_links
from common import mysql_query, mysql_query_single_value

from models import Sites, SiteTests, TestData, SiteConfig, ErrorLog, Categories, Articles

app = Flask(__name__)# mysql stuff
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql://webperfs_client:32aqmMZTfvADjwvXOtQxyu5@hachiman.oderland.com/webperfs_wperf"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# global variables
week_limiter = 20
active_test_ids = set([0, 2, 3, 6, 7, 14, 15, 16, 17, 18, 19, 20])


def rating_summary(site_id = None, cat_id = None):
    # TODO: kan skrivas om så all beräkning sker först, alla uppdateringar lagras i en array som körs 100 i taget
    if site_id is None:
        sql = text('SELECT sites.id, AVG(sitetests.rating) as rating FROM sites LEFT JOIN sitetests on sites.id = sitetests.site_id WHERE most_recent=1 AND sitetests.test_date > NOW() - INTERVAL {0} WEEK GROUP BY sites.id'.format(week_limiter))
    elif cat_id is not None:
        sql = text('SELECT sites.id, AVG(sitetests.rating) as rating FROM sites LEFT JOIN sitetests on sites.id = sitetests.site_id WHERE most_recent=1 AND sitetests.test_date > NOW() - INTERVAL {0} WEEK AND category = {1} GROUP BY sites.id'.format(week_limiter, cat_id))
    else:
        sql = text('SELECT sites.id, AVG(sitetests.rating) as rating FROM sites LEFT JOIN sitetests on sites.id = sitetests.site_id WHERE most_recent=1 AND sitetests.test_date > NOW() - INTERVAL {0} WEEK AND sites.id = {1} GROUP BY sites.id'.format(week_limiter, site_id))

    result = db.engine.execute(sql)
    names = []
    for row in result:
        names.append(round(row[1], 1))
        sql_update = text('UPDATE sites SET rating_overall = \'{0}\' WHERE sites.id = {1}'.format(round(row[1], 1), row[0]))
        db.engine.execute(sql_update)

    print(names)
    result.close()
    return None

def rating_webstandard(site_id = None, cat_id = None):
    if site_id is None:
        sql = text('SELECT sites.id, AVG(sitetests.rating) as rating FROM sites LEFT JOIN sitetests on sites.id = sitetests.site_id WHERE (sitetests.type_of_test = 2 OR sitetests.type_of_test = 3 OR sitetests.type_of_test = 6 OR sitetests.type_of_test = 7 OR sitetests.type_of_test = 14) AND most_recent=1 AND sitetests.test_date > NOW() - INTERVAL {0} WEEK GROUP BY sites.id'.format(week_limiter))
    elif cat_id is not None:
        sql = text('SELECT sites.id, AVG(sitetests.rating) as rating FROM sites LEFT JOIN sitetests on sites.id = sitetests.site_id WHERE (sitetests.type_of_test = 2 OR sitetests.type_of_test = 3 OR sitetests.type_of_test = 6 OR sitetests.type_of_test = 7 OR sitetests.type_of_test = 14) AND most_recent=1 AND sitetests.test_date > NOW() - INTERVAL {0} WEEK AND category = {1} GROUP BY sites.id'.format(week_limiter, cat_id))
    else:
        sql = text('SELECT sites.id, AVG(sitetests.rating) as rating FROM sites LEFT JOIN sitetests on sites.id = sitetests.site_id WHERE (sitetests.type_of_test = 2 OR sitetests.type_of_test = 3 OR sitetests.type_of_test = 6 OR sitetests.type_of_test = 7 OR sitetests.type_of_test = 14) AND most_recent=1 AND sitetests.test_date > NOW() - INTERVAL {0} WEEK AND sites.id = {1} GROUP BY sites.id'.format(week_limiter, site_id))

    result = db.engine.execute(sql)
    #names = []
    for row in result:
        # names.append(round(row[1], 1))
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sql_update = text('UPDATE sites SET rating_webstandard = \'{0}\', date_modified = \'{1}\' WHERE sites.id = {2}'.format(round(row[1], 1), timestamp, row[0]))
        db.engine.execute(sql_update)

    # print(names)
    result.close()
    return None

def rating_perf(site_id = None, cat_id = None):
    if site_id is None:
        sql = text('SELECT sites.id, AVG(sitetests.rating) as rating FROM sites LEFT JOIN sitetests on sites.id = sitetests.site_id WHERE (sitetests.type_of_test = 0 OR sitetests.type_of_test = 1 OR sitetests.type_of_test = 15 OR sitetests.type_of_test = 17) AND most_recent=1 AND sitetests.test_date > NOW() - INTERVAL {0} WEEK GROUP BY sites.id'.format(week_limiter))
    elif cat_id is not None:
        sql = text('SELECT sites.id, AVG(sitetests.rating) as rating FROM sites LEFT JOIN sitetests on sites.id = sitetests.site_id WHERE (sitetests.type_of_test = 0 OR sitetests.type_of_test = 1 OR sitetests.type_of_test = 15 OR sitetests.type_of_test = 17) AND most_recent=1 AND sitetests.test_date > NOW() - INTERVAL {0} WEEK AND sites.category = {1} GROUP BY sites.id'.format(week_limiter, cat_id))
    else:
        sql = text('SELECT sites.id, AVG(sitetests.rating) as rating FROM sites LEFT JOIN sitetests on sites.id = sitetests.site_id WHERE (sitetests.type_of_test = 0 OR sitetests.type_of_test = 1 OR sitetests.type_of_test = 15 OR sitetests.type_of_test = 17) AND most_recent=1 AND sitetests.test_date > NOW() - INTERVAL {0} WEEK AND sites.id = {1} GROUP BY sites.id'.format(week_limiter, site_id))

    result = db.engine.execute(sql)
    #names = []
    for row in result:
        # names.append(round(row[1], 1))
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sql_update = text('UPDATE sites SET rating_pagespeed = \'{0}\', date_modified = \'{1}\' WHERE sites.id = {2}'.format(round(row[1], 1), timestamp, row[0]))
        db.engine.execute(sql_update)

    # print(names)
    result.close()
    return None

def rating_usability(site_id = None, cat_id = None):
    if site_id is None:
        sql = text('SELECT sites.id, st.rating FROM sites JOIN (SELECT MAX(id) max_id, site_id FROM sitetests WHERE type_of_test = 16 AND most_recent=1 GROUP BY site_id) test_max ON (test_max.site_id = sites.id) JOIN sitetests st ON (st.id = test_max.max_id) ORDER BY sites.id ASC, st.test_date DESC')
    elif cat_id is not None:
        sql = text('SELECT sites.id, st.rating FROM sites JOIN (SELECT MAX(id) max_id, site_id FROM sitetests WHERE type_of_test = 16 AND most_recent=1 GROUP BY site_id) test_max ON (test_max.site_id = sites.id) JOIN sitetests st ON (st.id = test_max.max_id) WHERE sites.category = {0} ORDER BY sites.id ASC, st.test_date DESC'.format(cat_id))
    else:
        sql = text('SELECT sites.id, st.rating FROM sites JOIN (SELECT MAX(id) max_id, site_id FROM sitetests WHERE type_of_test = 16 AND most_recent=1 AND sitetests.site_id = {0} GROUP BY site_id) test_max ON (test_max.site_id = sites.id) JOIN sitetests st ON (st.id = test_max.max_id) ORDER BY sites.id ASC, st.test_date DESC'.format(site_id))

    result = db.engine.execute(sql)
    #names = []
    for row in result:
        # names.append(round(row[1], 1))
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sql_update = text('UPDATE sites SET rating_usability = \'{0}\', date_modified = \'{1}\' WHERE sites.id = {2}'.format(row[1], timestamp, row[0]))
        db.engine.execute(sql_update)

    # print(names)
    result.close()
    return None

def rating_a11y(site_id = None, cat_id = None):
    if site_id is None:
        sql = text('SELECT sites.id, AVG(sitetests.rating) as rating FROM sites LEFT JOIN sitetests on sites.id = sitetests.site_id WHERE (sitetests.type_of_test = 18 OR sitetests.type_of_test = 19) AND most_recent=1 GROUP BY sites.id')
    elif cat_id is not None:
        sql = text('SELECT sites.id, AVG(sitetests.rating) as rating FROM sites LEFT JOIN sitetests on sites.id = sitetests.site_id WHERE (sitetests.type_of_test = 18 OR sitetests.type_of_test = 19) AND most_recent=1 AND sites.category = {0} GROUP BY sites.id'.format(cat_id))
    else:
        sql = text('SELECT sites.id, AVG(sitetests.rating) as rating FROM sites LEFT JOIN sitetests on sites.id = sitetests.site_id WHERE (sitetests.type_of_test = 18 OR sitetests.type_of_test = 19) AND most_recent=1 AND sites.id = {0} GROUP BY sites.id'.format(site_id))

    result = db.engine.execute(sql)

    for row in result:
        # names.append(round(row[1], 1))
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sql_update = text('UPDATE sites SET rating_a11y = \'{0}\', date_modified = \'{1}\' WHERE sites.id = {2}'.format(row[1], timestamp, row[0]))
        db.engine.execute(sql_update)

    # print(names)
    result.close()
    return None

def rating_summary_categories():
    sql = text('SELECT category, AVG(rating_overall) as rating, AVG(rating_a11y) as a_rating, AVG(rating_usability) as u_rating, AVG(rating_pagespeed) as p_rating, AVG(rating_webstandard) as standard_rating FROM sites GROUP BY sites.category')
    result = db.engine.execute(sql)
    #names = []
    for row in result:
        #names.append(round(row[1], 1))
        sql_update = text('UPDATE categories SET rating_overall = \'{0}\', rating_a11y = \'{1}\', rating_usability = \'{2}\', rating_pagespeed = \'{3}\', rating_webstandard = \'{4}\'  WHERE id = {5}'.format(round(row[1], 1), round(row[2], 1), round(row[3], 1), round(row[4], 1), round(row[5], 1), row[0]))
        db.engine.execute(sql_update)

    #print(names)
    result.close()
    return None

"""
def percentile_rating(num_array):
    import numpy as np
    # a = np.array([1,2,3,4,5])
    a = np.array(num_array)
    p80 = np.percentile(a, 80) # över får 5 i betyg, under får fyra, return 80th percentile, 80% is lower
    p60 = np.percentile(a, 60) # betyg 4
    p40 = np.percentile(a, 40) # betyg 3
    p20 = np.percentile(a, 20) # betyg 2, under får betyg 1
    print(p80, p60, p40, p20)

    return (p80, p60, p40, p20)
"""

def testsites(category_id=None, test_type=None, begin_with_id=None, only_test_id=False, only_test_untested_last_hours=24, order_by='title ASC'):
    """
    Executing the actual tests.
    Attributes:
    * category_id=None|number
    * test_type=num|None to execute all available tests
    * begin_with_id=None|number with the site.id to begin with
    * only_test_id=False|number with the single site.id to test
    """

    # TODO: implementera test_type=None

    print("################################################################################################################")

    i = 1

    if only_test_id is not False:
        # testa bara en sajt
        sites_query = text('SELECT id, website FROM sites WHERE id = {0}'.format(begin_with_id))
        #sites = Sites.query.filter_by(id=begin_with_id).order_by(Sites.id)
    else:
        tmp_sql = 'SELECT id, website FROM sites WHERE (timeout IS NULL OR timeout <= DATE_SUB(NOW(),INTERVAL 36 HOUR)) AND active=1'
        # tmp_sql = 'SELECT id, website FROM sites WHERE active=1'
        if category_id is not None and begin_with_id is not None:
            tmp_sql += ' AND category={0} AND id >= {1}'.format(category_id, begin_with_id)
        elif category_id is None and begin_with_id is not None:
            tmp_sql += ' AND id >= {0}'.format(begin_with_id)
        elif category_id is not None and begin_with_id is None:
            tmp_sql += ' AND category = {0}'.format(category_id)

        if only_test_untested_last_hours is not None:
            tmp_sql += ' AND id NOT IN (SELECT site_id FROM sitetests WHERE most_recent=1 AND type_of_test={0} AND test_date >= DATE_SUB(NOW(),INTERVAL {1} HOUR))'.format(test_type, only_test_untested_last_hours)

        tmp_sql += ' ORDER BY {0}'.format(order_by)

        sites_query = text(tmp_sql)
        #sites = Sites.query.filter_by(category=category_id).order_by(Sites.id) if category_id is not None else Sites.query.order_by(Sites.id)

    result = db.engine.execute(sites_query)
    items = list()
    for row in result:
        site_id = row[0]
        website = row[1]
        items.append([site_id, website])

    print('Webbadresser som testas:', len(items))
    result.close()

    for item in items:
        site_id = item[0]
        website = item[1]
        print('{}. Testar adress {}'.format(i, website))
        the_test_result = None

        try:
            if test_type is 2:
                the_test_result = check_four_o_four(website)
            elif test_type is 6:
                the_test_result = check_w3c_valid(website)
            elif test_type is 7:
                the_test_result = check_w3c_valid_css(website)
            elif test_type is 16:
                the_test_result = check_google_usability(website)
            elif test_type is 20:
                the_test_result = check_privacy_webbkollen(website)
            elif test_type is 0:
                the_test_result = check_google_pagespeed(website)

            if the_test_result is not None:
                print('Rating: ', the_test_result[0])
                #print('Review: ', the_test_result[1])

                json_data = ''
                try:
                    json_data = the_test_result[2]
                except:
                    json_data = ''
                    pass


                checkreport = str(the_test_result[1]).encode('utf-8') # för att lösa encoding-probs
                jsondata = str(json_data).encode('utf-8') # --//--
                mysql_query('UPDATE sitetests SET most_recent=0 WHERE site_id = {0} AND type_of_test={1}'.format(site_id, test_type))
                site_test = SiteTests(site_id=site_id, type_of_test=test_type, check_report=checkreport, rating=the_test_result[0], pages_checked=-1, test_date=datetime.datetime.now(), json_check_data=jsondata)
                db.session.add(site_test)
                db.session.commit()
                mysql_query('UPDATE sites SET date_modified=\'{0}\' WHERE id = {1}'.format(datetime.datetime.now(), site_id))


                the_test_result = None # 190506 för att inte skriva testresultat till sajter när testet kraschat. Måste det sättas till ''?
                # TODO: Klarmarkera skiten (vad då?)
                # TODO: uppdatera snittbetygen
        except Exception as e:
            print('FAIL!', website, '\n', e)
            pass

        i += 1

# behöver kunna ange flera tester att köra, ge array med tester?
#premium_tests(100, 0, False)"""

def update_rating(site_id = None, cat_id = None):
    rating_a11y(site_id, cat_id)
    rating_perf(site_id, cat_id)
    rating_usability(site_id, cat_id)
    rating_webstandard(site_id, cat_id)
    rating_summary(site_id, cat_id)
    rating_summary_categories()


def testing(category_id = None, site_id = None, type_of_test = None, retesting_in_hours=48, include_all_tests = False):
    iteration = 1
     # None är default
    #site_id = 3843 # 141 är VGR, 3843 är webperf, None är default
    #retesting_in_hours=336 # 72 är tre dygn, 168 är en vecka, 336 är två veckor, 504 är tre veckor (då alltid inom en månad gammalt)

    if site_id is None and type_of_test is None:
        while(True):
            print('###{0}###'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            ##############
            print('Kör test: 0 - Google Pagespeed')
            testsites(category_id, 0, only_test_untested_last_hours=retesting_in_hours, order_by='RAND()')
            print('Kör test: 2 - 404-test')
            testsites(category_id, 2, only_test_untested_last_hours=retesting_in_hours, order_by='RAND()')

            print('Kör test: 6 - HTML')
            testsites(category_id, 6, only_test_untested_last_hours=retesting_in_hours, order_by='RAND()')
            print('Kör test: 7 - CSS')
            testsites(category_id, 7, only_test_untested_last_hours=retesting_in_hours, order_by='RAND()')

            print('Kör test: 16 - Google Usability')
            testsites(category_id, 16, only_test_untested_last_hours=retesting_in_hours, order_by='RAND()')

            print('Kör test: 20 - Webbkoll')
            testsites(category_id, 20, only_test_untested_last_hours=504, order_by='RAND()') # deal om 1500 queries per månad, så...

            # uppdatera bara betyg vid udda körningar
            if (iteration % 2) != 0:
                update_rating(cat_id = category_id)

            iteration = iteration + 1
            break

    elif site_id is not None and type_of_test is None:
        print('###{0}###'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        print('Kör test: 0 - Google Pagespeed')
        testsites(None, 0, site_id, True, only_test_untested_last_hours=None)
        print('Kör test: 2 - 404-test')
        testsites(None, 2, site_id, True, only_test_untested_last_hours=None)
        print('Kör test: 6 - HTML')
        testsites(None, 6, site_id, True, only_test_untested_last_hours=None)
        print('Kör test: 7 - CSS')
        testsites(None, 7, site_id, True, only_test_untested_last_hours=None)

        print('Kör test: 16 - Google Usability')
        testsites(None, 16, site_id, True, only_test_untested_last_hours=None)

        print('Kör test: 20 - Webbkoll')
        testsites(None, 20, site_id, True, only_test_untested_last_hours=None)

        update_rating(site_id)


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    if len(sys.argv) > 1 and 'site' in sys.argv[1]:
        a,b = sys.argv[1].split("=")
        print('###############################')
        print('Kör site:', b)
        testing(site_id=b)
    elif len(sys.argv) > 1 and 'id' in sys.argv[1]:
        a,b = sys.argv[1].split("=")
        print('###############################')
        print('Kör site:', b)
        testing(site_id=b)
    elif len(sys.argv) > 1 and 'cat' in sys.argv[1]:
        a,b = sys.argv[1].split("=")
        print('###############################')
        print('Kör kategori:', b)
        testing(category_id=b)
    else:
        print('###############################')
        print('Inga argument, kör alla webbplatser')
        testing()
