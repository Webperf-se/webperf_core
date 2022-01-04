# -*- coding: utf-8 -*-
import datetime
import json
import gettext


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
    overall_count = 1
    overall_review = ''
    integrity_and_security = -1
    integrity_and_security_count = 1
    integrity_and_security_review = ''
    performance = -1
    performance_count = 1
    performance_review = ''
    standards = -1
    standards_count = 1
    standards_review = ''
    a11y = -1
    a11y_count = 1
    a11y_review = ''
    review_show_improvements_only = False

    _ = False
    is_set = False

    def __init__(self, _=None, review_show_improvements_only=False):
        # don't know anything we want todo yet
        self.overall = -1
        self._ = _
        self.review_show_improvements_only = review_show_improvements_only

    def set_overall(self, points, review=''):
        if(points < 1.0):
            self.overall = 1.0
        elif(points > 5.0):
            self.overall = 5.0
        else:
            self.overall = points
        if review != '' and (not self.review_show_improvements_only or points < 5.0):
            self.overall_review = self._('TEXT_TEST_REVIEW_RATING_ITEM').format(
                review, points)
        self.is_set = True

    def get_overall(self):
        return self.transform_value(self.overall / self.overall_count)

    def set_integrity_and_security(self, points, review=''):
        if(points < 1.0):
            self.integrity_and_security = 1.0
        elif(points > 5.0):
            self.integrity_and_security = 5.0
        else:
            self.integrity_and_security = points
        if review != '' and (not self.review_show_improvements_only or points < 5.0):
            self.integrity_and_security_review = self._('TEXT_TEST_REVIEW_RATING_ITEM').format(
                review, points)
        self.is_set = True

    def get_integrity_and_security(self):
        return self.transform_value(self.integrity_and_security / self.integrity_and_security_count)

    def set_performance(self, points, review=''):
        if(points < 1.0):
            self.performance = 1.0
        elif(points > 5.0):
            self.performance = 5.0
        else:
            self.performance = points
        if review != '' and (not self.review_show_improvements_only or points < 5.0):
            self.performance_review = self._('TEXT_TEST_REVIEW_RATING_ITEM').format(
                review, points)
        self.is_set = True

    def get_performance(self):
        return self.transform_value(self.performance / self.performance_count)

    def set_standards(self, points, review=''):
        if(points < 1.0):
            self.standards = 1.0
        elif(points > 5.0):
            self.standards = 5.0
        else:
            self.standards = points
        if review != '' and (not self.review_show_improvements_only or points < 5.0):
            self.standards_review = self._('TEXT_TEST_REVIEW_RATING_ITEM').format(
                review, points)
        self.is_set = True

    def get_standards(self):
        return self.transform_value(self.standards / self.standards_count)

    def set_a11y(self, points, review=''):
        if(points < 1.0):
            self.a11y = 1.0
        elif(points > 5.0):
            self.a11y = 5.0
        else:
            self.a11y = points
        if review != '' and (not self.review_show_improvements_only or points < 5.0):
            self.a11y_review = self._('TEXT_TEST_REVIEW_RATING_ITEM').format(
                review, points)
        self.is_set = True

    def get_a11y(self):
        return self.transform_value(self.a11y / self.a11y_count)

    def isused(self):
        return self.is_set

    def transform_value(self, value):
        return float("{0:.2f}".format(value))

    def get_reviews(self):
        text = self._('TEXT_TEST_REVIEW_OVERVIEW').format(self.overall_review)
        if (self.get_integrity_and_security() != -1 and self.integrity_and_security_review != ''):
            text += self._('TEXT_TEST_REVIEW_INTEGRITY_SECURITY').format(
                self.integrity_and_security_review)
        if (self.get_performance() != -1 and self.performance_review != ''):
            text += self._('TEXT_TEST_REVIEW_PERFORMANCE').format(
                self.performance_review)
        if (self.get_a11y() != -1 and self.a11y_review != ''):
            text += self._('TEXT_TEST_REVIEW_ALLY').format(self.a11y_review)
        if (self.get_standards() != -1 and self.standards_review != ''):
            text += self._('TEXT_TEST_REVIEW_STANDARDS').format(
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
            if self._ != None:
                tmp = Rating(self._, self.review_show_improvements_only)
            else:
                tmp = Rating(other._, other.review_show_improvements_only)

            tmp_value = tmp.get_combined_value(
                self.overall, self.overall_count, other.overall, other.overall_count)
            if (tmp_value[0] != -1):
                tmp.is_set = True
                tmp.overall = tmp_value[0]
                tmp.overall_count = tmp_value[1]
            tmp.overall_review = self.overall_review + \
                other.overall_review

            tmp_value = tmp.get_combined_value(
                self.integrity_and_security, self.integrity_and_security_count, other.integrity_and_security, other.integrity_and_security_count)
            if (tmp_value[0] != -1):
                tmp.is_set = True
                tmp.integrity_and_security = tmp_value[0]
                tmp.integrity_and_security_count = tmp_value[1]
            tmp.integrity_and_security_review = self.integrity_and_security_review + \
                other.integrity_and_security_review

            tmp_value = tmp.get_combined_value(
                self.performance, self.performance_count, other.performance, other.performance_count)
            if (tmp_value[0] != -1):
                tmp.is_set = True
                tmp.performance = tmp_value[0]
                tmp.performance_count = tmp_value[1]
            tmp.performance_review = self.performance_review + other.performance_review

            tmp_value = tmp.get_combined_value(
                self.standards, self.standards_count, other.standards, other.standards_count)
            if (tmp_value[0] != -1):
                tmp.is_set = True
                tmp.standards = tmp_value[0]
                tmp.standards_count = tmp_value[1]
            tmp.standards_review = self.standards_review + other.standards_review

            tmp_value = tmp.get_combined_value(
                self.a11y, self.a11y_count, other.a11y, other.a11y_count)
            if (tmp_value[0] != -1):
                tmp.is_set = True
                tmp.a11y = tmp_value[0]
                tmp.a11y_count = tmp_value[1]
            tmp.a11y_review = self.a11y_review + other.a11y_review
            return tmp

    def get_combined_value(self, val1, val1_count, val2, val2_count):
        val1_has_value = val1 != -1
        val2_has_value = val2 != -1
        if (val1_has_value and val2_has_value):
            return (val1 + val2, val1_count + val2_count)
        elif (not val1_has_value and not val2_has_value):
            return (-1, 1)
        elif(val1_has_value):
            return (val1, val1_count)
        else:
            return (val2, val2_count)

    def __repr__(self):
        text = self._('TEXT_TEST_RATING_OVERVIEW').format(self.get_overall())
        if (self.get_integrity_and_security() != -1):
            text += self._('TEXT_TEST_RATING_INTEGRITY_SECURITY').format(
                self.get_integrity_and_security())
        if (self.get_performance() != -1):
            text += self._('TEXT_TEST_RATING_PERFORMANCE').format(self.get_performance())
        if (self.get_a11y() != -1):
            text += self._('TEXT_TEST_RATING_ALLY').format(self.get_a11y())
        if (self.get_standards() != -1):
            text += self._('TEXT_TEST_RATING_STANDARDS').format(
                self.get_standards())

        return text


class SiteTests(object):
    __tablename__ = 'sitetests'

    site_id = 0
    id = 0
    test_date = datetime.datetime.now()
    type_of_test = 0
    check_report = ""
    check_report_sec = ""
    check_report_perf = ""
    check_report_a11y = ""
    check_report_stand = ""
    json_check_data = ""
    most_recent = 1
    rating = -1  # rating from 1-5 on how good the results were
    rating_sec = -1  # rating from 1-5 on how good the results were
    rating_perf = -1  # rating from 1-5 on how good the results were
    rating_a11y = -1  # rating from 1-5 on how good the results were
    rating_stand = -1  # rating from 1-5 on how good the results were

    def __init__(self, site_id, type_of_test, rating, test_date, json_check_data):
        self.site_id = site_id
        self.type_of_test = type_of_test
        self.check_report = self.encode_review(rating.overall_review)
        self.check_report_sec = self.encode_review(
            rating.integrity_and_security_review)
        self.check_report_perf = self.encode_review(rating.performance_review)
        self.check_report_a11y = self.encode_review(rating.a11y_review)
        self.check_report_stand = self.encode_review(rating.standards_review)
        self.rating = rating.get_overall()
        self.rating_sec = rating.get_integrity_and_security()
        self.rating_perf = rating.get_performance()
        self.rating_a11y = rating.get_a11y()
        self.rating_stand = rating.get_standards()
        self.test_date = test_date
        self.json_check_data = json_check_data

    def encode_review(self, review):
        review_encoded = str(review).encode(
            'utf-8')  # för att lösa encoding-probs
        return review_encoded

    def todata(self):
        result = [{
            'site_id': self.site_id,
            'type_of_test': self.type_of_test,
            'rating': self.rating,
            'rating_sec': self.rating_sec,
            'rating_perf': self.rating_perf,
            'rating_a11y': self.rating_a11y,
            'rating_stand': self.rating_stand,
            'date': self.test_date.isoformat(),
            'report': self.check_report.decode('utf-8'),
            'report_sec': self.check_report_sec.decode('utf-8'),
            'report_perf': self.check_report_perf.decode('utf-8'),
            'report_a11y': self.check_report_a11y.decode('utf-8'),
            'report_stand': self.check_report_stand.decode('utf-8'),
            'data': self.json_check_data.decode('utf-8')
        }]
        return result

    @staticmethod
    def fieldnames():
        result = ['site_id', 'type_of_test',
                  'rating', 'rating_sec', 'rating_perf',
                  'rating_a11y', 'rating_stand',
                  'date', 'report', 'report_sec', 'report_perf', 'report_a11y', 'report_stand', 'data']
        return result

    def __repr__(self):
        return '<SiteTest %r>' % self.test_date
