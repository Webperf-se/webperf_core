# -*- coding: utf-8 -*-
import datetime
import json


class Sites(object):
    __tablename__ = 'sites'

    id = 0
    title = ""
    website = ""
    active = 1

    def __init__(self, id, website):
        self.id = id
        self.website = website

    def todata(self):
        result = {
            'id': self.id,
            'website': self.website
        }
        return result

    @staticmethod
    def fieldnames():
        result = ['id', 'website']
        return result

    def __repr__(self):
        return '<Site %r>' % self.title


class Rating(object):
    overall = -1
    overall_review = ''
    integrity_and_security = -1
    integrity_and_security_review = ''
    performance = -1
    performance_review = ''
    standards = -1
    standards_review = ''
    a11y = -1
    a11y_review = ''

    is_set = False

    def __init__(self):
        # don't know anything we want todo yet
        self.overall = -1

    def set_overall(self, points, review=''):
        if(points < 1.0):
            self.overall = 1.0
        elif(points > 5.0):
            self.overall = 5.0
        else:
            self.overall = points
        self.overall_review = review
        self.is_set = True

    def get_overall(self):
        return self.transform_value(self.overall)

    def set_integrity_and_security(self, points, review=''):
        if(points < 1.0):
            self.integrity_and_security = 1.0
        elif(points > 5.0):
            self.integrity_and_security = 5.0
        else:
            self.integrity_and_security = points
        self.integrity_and_security_review = review
        self.is_set = True

    def get_integrity_and_security(self):
        return self.transform_value(self.integrity_and_security)

    def set_performance(self, points, review=''):
        if(points < 1.0):
            self.performance = 1.0
        elif(points > 5.0):
            self.performance = 5.0
        else:
            self.performance = points
        self.performance_review = review
        self.is_set = True

    def get_performance(self):
        return self.transform_value(self.performance)

    def set_standards(self, points, review=''):
        if(points < 1.0):
            self.standards = 1.0
        elif(points > 5.0):
            self.standards = 5.0
        else:
            self.standards = points
        self.standards_review = review
        self.is_set = True

    def get_standards(self):
        return self.transform_value(self.standards)

    def set_a11y(self, points, review=''):
        if(points < 1.0):
            self.a11y = 1.0
        elif(points > 5.0):
            self.a11y = 5.0
        else:
            self.a11y = points
        self.a11y_review = review
        self.is_set = True

    def get_a11y(self):
        return self.transform_value(self.a11y)

    def isused(self):
        return self.is_set

    def transform_value(self, value):
        return float("{0:.2f}".format(value))

    def get_reviews(self):
        text = '\r\n* Overall: {0}\r\n'.format(self.overall_review)
        if (self.integrity_and_security != -1):
            text += '-- Integrity & Security: {0}\r\n'.format(
                self.integrity_and_security_review)
        if (self.performance != -1):
            text += '-- Performance: {0}\r\n'.format(self.performance_review)
        if (self.a11y != -1):
            text += '-- A11y: {0}\r\n'.format(self.a11y_review)
        if (self.standards != -1):
            text += '-- Standards: {0}\r\n'.format(
                self.standards_review)

        return text

    def todata(self):
        result = {
            'rating_overall': self.get_overall(),
            'rating_security': self.get_integrity_and_security(),
            'rating_performance': self.get_performance(),
            'rating_standards': self.get_standards(),
            'rating_a11y': self.get_a11y()
        }
        return result

    @staticmethod
    def fieldnames():
        result = ['rating_overall', 'rating_integrity_and_security',
                  'rating_performance', 'rating_standards', 'rating_a11y']
        return result

    def __add__(self, other):
        if (not isinstance(other, Rating)):
            raise TypeError
        else:
            tmp = Rating()
            if (self.isused() and other.isused()):
                tmp.set_overall(tmp.get_combined_value(self.get_overall(
                ), other.get_overall()), self.overall_review + other.overall_review)
            elif (self.isused()):
                tmp.set_overall(self.get_overall(
                ), self.overall_review)
            elif (other.isused()):
                tmp.set_overall(other.get_overall(
                ), other.overall_review)
            else:
                return tmp

            tmp_value = tmp.get_combined_value(
                self.get_integrity_and_security(), other.get_integrity_and_security())
            if (tmp_value != -1):
                tmp.integrity_and_security = tmp_value
                tmp.integrity_and_security_review = self.integrity_and_security_review + \
                    other.integrity_and_security_review

            tmp_value = tmp.get_combined_value(self.get_performance(
            ), other.get_performance())
            if (tmp_value != -1):
                tmp.performance = tmp_value
                tmp.performance_review = self.performance_review + other.performance_review

            tmp_value = tmp.get_combined_value(self.get_standards(
            ), other.get_standards())
            if (tmp_value != -1):
                tmp.standards = tmp_value
                tmp.standards_review = self.standards_review + other.standards_review

            tmp_value = tmp.get_combined_value(
                self.get_a11y(), other.get_a11y())
            if (tmp_value != -1):
                tmp.a11y = tmp_value
                tmp.a11y_review = self.a11y_review + other.a11y_review
            return tmp

    def get_combined_value(self, val1, val2):
        val1_has_value = val1 != -1
        val2_has_value = val2 != -1
        if (val1_has_value and val2_has_value):
            return (val1 + val2) / 2
        elif (not val1_has_value and not val2_has_value):
            return -1
        elif(val1_has_value):
            return val1
        else:
            return val2

    def __repr__(self):
        text = '\r\n* Overall: {0}\r\n'.format(self.overall)
        if (self.integrity_and_security != -1):
            text += '-- Integrity & Security: {0}\r\n'.format(
                self.integrity_and_security)
        if (self.performance != -1):
            text += '-- Performance: {0}\r\n'.format(self.performance)
        if (self.a11y != -1):
            text += '-- A11y: {0}\r\n'.format(self.a11y)
        if (self.standards != -1):
            text += '-- Standards: {0}\r\n'.format(
                self.standards)

        return text


class SiteTests(object):
    __tablename__ = 'sitetests'

    site_id = 0
    id = 0
    test_date = datetime.datetime.now()
    type_of_test = 0
    check_report = ""
    json_check_data = ""
    most_recent = 1
    rating = -1  # rating from 1-5 on how good the results were

    def __init__(self, site_id, type_of_test, review_encoded, rating, test_date, json_check_data):
        self.site_id = site_id
        self.type_of_test = type_of_test
        self.check_report = review_encoded
        self.rating = rating
        self.test_date = test_date
        self.json_check_data = json_check_data

    def todata(self):
        result = {
            'site_id': self.site_id,
            'type_of_test': self.type_of_test,
            'rating': self.rating.get_overall(),
            'date': self.test_date.isoformat(),
            'report': self.check_report,
            'data': self.json_check_data.decode('utf-8')
        }
        return result

    @staticmethod
    def fieldnames():
        result = ['site_id', 'type_of_test',
                  'rating', 'date', 'report', 'data']
        return result

    def __repr__(self):
        return '<SiteTest %r>' % self.test_date
