#-*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from sqlalchemy import text
import datetime

from checks import *

from models import Sites, SiteTests
import config

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.db_string
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


def testsites(test_type=None, only_test_untested_last_hours=24, order_by='title ASC'):
    """
    Executing the actual tests.
    Attributes:
    * test_type=num|None to execute all available tests
    """

    # TODO: implementera test_type=None

    print("###############################################")

    i = 1

    tmp_sql = 'SELECT id, website FROM sites WHERE active=1 ORDER BY {0}'.format(order_by)

    """if only_test_untested_last_hours is not None:
        tmp_sql += ' AND id NOT IN (SELECT site_id FROM sitetests WHERE most_recent=1 AND type_of_test={0} AND test_date >= date(\'now\',\'{1} HOURS\')'.format(test_type, only_test_untested_last_hours)

    tmp_sql += ' ORDER BY {0}'.format(order_by)"""

    sites_query = text(tmp_sql)

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
                #session.query(Clients).filter(Clients.id == client_id_list).update({'status': status})
                db.session.query(SiteTests).filter(SiteTests.type_of_test==test_type).filter(SiteTests.site_id == site_id).update({'most_recent': 0})
                
                #.where().where(SiteTests.most_recent==1).values(most_recent=0))
                #mysql_query('UPDATE sitetests SET most_recent=0 WHERE site_id = {0} AND type_of_test={1}'.format(site_id, test_type))
                site_test = SiteTests(site_id=site_id, type_of_test=test_type, check_report=checkreport, rating=the_test_result[0], test_date=datetime.datetime.now(), json_check_data=jsondata)
                db.session.add(site_test)
                db.session.commit()

                the_test_result = None # 190506 för att inte skriva testresultat till sajter när testet kraschat. Måste det sättas till ''?
        except Exception as e:
            print('FAIL!', website, '\n', e)
            pass

        i += 1

def testing():
    print('### {0} ###'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    ##############
    print('###############################\nKör test: 0 - Google Pagespeed')
    testsites(test_type=0)
    print('###############################\nKör test: 2 - 404-test')
    testsites(test_type=2)
    print('###############################\nKör test: 6 - HTML')
    testsites(test_type=6)
    print('###############################\nKör test: 7 - CSS')
    testsites(test_type=7)
    print('###############################\nKör test: 20 - Webbkoll')
    testsites(test_type=20)

"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    print('###############################')
    testing()
