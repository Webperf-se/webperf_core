#-*- coding: utf-8 -*-
import datetime

class Sites(object):
    __tablename__ = 'sites'

    id = 0
    title = ""
    website = ""
    active = 1

    def __repr__(self):
        return '<Site %r>' % self.title

class SiteTests(object):
    __tablename__ = 'sitetests'

    site_id = 0
    id = 0
    test_date = datetime.datetime.now()
    type_of_test = 0
    check_report = ""
    json_check_data = ""
    most_recent = 1
    rating = -1 #rating from 1-5 on how good the results were

    def __init__(self, site_id, type_of_test, check_report, rating, test_date, json_check_data):
        self.site_id = site_id
        self.type_of_test = type_of_test
        self.check_report = check_report
        self.rating = rating
        self.test_date = test_date
        self.json_check_data = json_check_data

    def __repr__(self):
        return '<SiteTest %r>' % self.test_date