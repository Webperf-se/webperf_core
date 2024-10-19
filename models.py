# -*- coding: utf-8 -*-
from datetime import datetime

class DefaultInfo: # pylint: disable=missing-class-docstring
    def __init__(self, domain, method, precision, category, name, version): # pylint: disable=too-many-arguments
        self.info = {}
        self.info['domain'] = domain
        self.info['method'] = method
        self.info['precision'] = precision
        self.info['category'] = category
        self.info['name'] = name
        self.info['version'] = version
        self.info['issues'] = []

    def __str__(self) -> str:
        return f"DefaultInfo(name={self.info['name']}, version={self.info['version']})"

    def __setitem__(self, key, value):
        self.info[key] = value

    def __getitem__(self, key):
        return self.info[key]

    def __contains__(self, key):
        return key in self.info

    def __eq__(self, other):
        if isinstance(other, DefaultInfo):
            return self.info['domain'] == other.info['domain'] and \
                self.info['method'] == other.info['method'] and \
                self.info['precision'] == other.info['precision'] and \
                self.info['category'] == other.info['category'] and \
                self.info['name'] == other.info['name'] and \
                self.info['version'] == other.info['version']
        return self.__eq__(other)

    def __hash__(self):
        return hash((self.info['domain'],
                      self.info['method'],
                      self.info['precision'],
                      self.info['category'],
                      self.info['version']))

class Sites: # pylint: disable=missing-class-docstring
    __tablename__ = 'sites'

    id = 0
    title = ""
    website = ""
    active = 1

    def __init__(self, site_id, website):
        self.id = site_id
        self.website = website

    def todata(self):
        """
        Convert the Site object to a dictionary.

        Returns:
            dict: A dictionary with 'id' and 'website' as keys.
        """
        result = {
            'id': self.id,
            'website': self.website
        }
        return result

    @staticmethod
    def fieldnames():
        """
        Get the field names for the Site class.

        Returns:
            list: A list containing the field names 'id' and 'website'.
        """
        result = ['id', 'website']
        return result

    def __repr__(self):
        return f'<Site {self.title}>'


class Rating: # pylint: disable=too-many-instance-attributes,missing-class-docstring
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

    translation = False
    is_set = False

    def __init__(self, translation=None, review_show_improvements_only=False):
        # don't know anything we want todo yet
        self.overall = -1
        self.translation = translation
        self.review_show_improvements_only = review_show_improvements_only

    def get_translation_text(self, translation_text):
        """
        Returns the translated text if a translation function is defined,
        otherwise returns the original text.

        This method checks if a translation function is defined for the instance.
        If not, it returns the original text. If a translation function is defined,
        it applies the function to the original text and returns the translated text.

        Parameters:
        translation_text (str): The text to be translated.

        Returns:
        str: The translated text if a translation function is defined, otherwise the original text.
        """
        if self.translation in (None, False):
            return translation_text
        return self.translation(translation_text)

    def ensure_correct_points_range(self, points):
        """
        Ensure the points are within the correct range [1.0, 5.0].

        Args:
            points (float): The points to be checked.

        Returns:
            float: The points adjusted to be within the range [1.0, 5.0].
        """
        if points < 1.0:
            points = 1.0
        elif points > 5.0:
            points = 5.0
        return points

    def set_overall(self, points, review=''):
        """
        Set the overall points and review.

        Args:
            points (float): The points to be set.
            review (str, optional): The review text.
        """
        review = review.replace('GOV-IGNORE', '')

        self.overall = self.ensure_correct_points_range(points)
        self.is_set = True

        if review == '':
            return

        if self.review_show_improvements_only and points == 5.0:
            return

        trans_str = 'TEXT_TEST_REVIEW_RATING_ITEM'
        self.overall_review = self.get_translation_text(trans_str).format(
                review, points)

    def get_overall(self):
        """
        Get the average overall points.

        Returns:
            float: The average overall points.
        """
        return self.transform_value(self.overall / self.overall_count)

    def set_integrity_and_security(self, points, review=''):
        """
        Set the integrity and security points and review.

        Args:
            points (float): The points to be set.
            review (str, optional): The review text.
        """
        review = review.replace('GOV-IGNORE', '')

        self.integrity_and_security = self.ensure_correct_points_range(points)
        self.is_set = True

        if review == '':
            return

        if self.review_show_improvements_only and points == 5.0:
            return

        trans_str = 'TEXT_TEST_REVIEW_RATING_ITEM'
        self.integrity_and_security_review = self.get_translation_text(trans_str).format(
                review, points)

    def get_integrity_and_security(self):
        """
        Get the average integrity and security points.

        Returns:
            float: The average integrity and security points.
        """
        return self.transform_value(self.integrity_and_security / self.integrity_and_security_count)

    def set_performance(self, points, review=''):
        """
        Set the performance points and review.

        Args:
            points (float): The points to be set.
            review (str, optional): The review text.
        """
        review = review.replace('GOV-IGNORE', '')

        self.performance = self.ensure_correct_points_range(points)
        self.is_set = True

        if review == '':
            return

        if self.review_show_improvements_only and points == 5.0:
            return

        trans_str = 'TEXT_TEST_REVIEW_RATING_ITEM'
        self.performance_review = self.get_translation_text(trans_str).format(
                review, points)


    def get_performance(self):
        """
        Get the average performance points.

        Returns:
            float: The average performance points.
        """
        return self.transform_value(self.performance / self.performance_count)

    def set_standards(self, points, review=''):
        """
        Set the standards points and review.

        Args:
            points (float): The points to be set.
            review (str, optional): The review text.
        """
        review = review.replace('GOV-IGNORE', '')

        self.standards = self.ensure_correct_points_range(points)
        self.is_set = True

        if review == '':
            return

        if self.review_show_improvements_only and points == 5.0:
            return

        trans_str = 'TEXT_TEST_REVIEW_RATING_ITEM'
        self.standards_review = self.get_translation_text(trans_str).format(
                review, points)



    def get_standards(self):
        """
        Get the average standards points.

        Returns:
            float: The average standards points.
        """
        return self.transform_value(self.standards / self.standards_count)

    def set_a11y(self, points, review=''):
        """
        Set the accessibility (a11y) points and review.

        Args:
            points (float): The points to be set.
            review (str, optional): The review text.
        """
        review = review.replace('GOV-IGNORE', '')

        self.a11y = self.ensure_correct_points_range(points)
        self.is_set = True

        if review == '':
            return

        if self.review_show_improvements_only and points == 5.0:
            return

        trans_str = 'TEXT_TEST_REVIEW_RATING_ITEM'
        self.a11y_review = self.get_translation_text(trans_str).format(
                review, points)



    def get_a11y(self):
        """
        Get the average accessibility (a11y) points.

        Returns:
            float: The average accessibility (a11y) points.
        """
        return self.transform_value(self.a11y / self.a11y_count)

    def isused(self):
        """
        Gets info if this rating has any usefull info in it or not.
        """
        return self.is_set

    def transform_value(self, value):
        """
        Transforms the input value into a float with two decimal places.

        This method takes a numerical input and converts it into a float,
        rounded to two decimal places. It's useful for standardizing numerical
        inputs to a consistent format.

        Args:
            value (int or float): The numerical value to be transformed.

        Returns:
            float: The input value transformed into a float with two decimal places.

        Example:
            >>> transform_value(3.14159)
            3.14
        """
        return float(f"{value:.2f}")

    def get_reviews(self):
        """
        Constructs a review text based on the various review categories.

        This method generates a review text by concatenating the reviews of
        different categories such as integrity and security, performance,
        accessibility (a11y), and standards.
        Each category's review is added to the text only if its value is not -1 and
        the review is not an empty string.
        The final review text is returned after removing any 'GOV-IGNORE' strings.

        Returns:
            str: The constructed review text.
        """
        text = self.get_translation_text('TEXT_TEST_REVIEW_OVERVIEW').format(self.overall_review)
        if (self.get_integrity_and_security() != -1 and self.integrity_and_security_review != ''):
            text += self.get_translation_text('TEXT_TEST_REVIEW_INTEGRITY_SECURITY').format(
                self.integrity_and_security_review)
        if (self.get_performance() != -1 and self.performance_review != ''):
            text += self.get_translation_text('TEXT_TEST_REVIEW_PERFORMANCE').format(
                self.performance_review)
        if (self.get_a11y() != -1 and self.a11y_review != ''):
            text += self.get_translation_text('TEXT_TEST_REVIEW_ALLY').format(self.a11y_review)
        if (self.get_standards() != -1 and self.standards_review != ''):
            text += self.get_translation_text('TEXT_TEST_REVIEW_STANDARDS').format(
                self.standards_review)

        return text.replace('GOV-IGNORE', '')

    def todata(self):
        """
        Converts the ratings into a dictionary.

        This method takes the ratings of various categories such as overall,
        integrity and security, performance, standards, and
        accessibility (a11y), and converts them into a dictionary.
        The keys of the dictionary are the names of the categories and
        the values are the corresponding ratings.

        Returns:
            dict: A dictionary containing the ratings of various categories.

        Example:
            >>> todata()
            {
                'rating_overall': 4.5,
                'rating_security': 4.7,
                'rating_performance': 4.2,
                'rating_standards': 4.8,
                'rating_a11y': 4.3
            }
        """
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
        """
        Get the field names for the Rating class.
        """
        result = ['rating_overall', 'rating_integrity_and_security',
                  'rating_performance', 'rating_standards', 'rating_a11y']
        return result

    def __add__(self, other):
        if not isinstance(other, Rating):
            raise TypeError

        if self.translation is not None:
            tmp = Rating(self.translation, self.review_show_improvements_only)
        else:
            tmp = Rating(other.translation, other.review_show_improvements_only)

        tmp_value = tmp.get_combined_value(
            self.overall, self.overall_count, other.overall, other.overall_count)
        if tmp_value[0] != -1:
            tmp.is_set = True
            tmp.overall = tmp_value[0]
            tmp.overall_count = tmp_value[1]
        tmp.overall_review = self.overall_review + \
            other.overall_review

        tmp_value = tmp.get_combined_value(
            self.integrity_and_security,
            self.integrity_and_security_count,
            other.integrity_and_security,
            other.integrity_and_security_count)

        if tmp_value[0] != -1:
            tmp.is_set = True
            tmp.integrity_and_security = tmp_value[0]
            tmp.integrity_and_security_count = tmp_value[1]
        tmp.integrity_and_security_review = self.integrity_and_security_review + \
            other.integrity_and_security_review

        tmp_value = tmp.get_combined_value(
            self.performance,
            self.performance_count,
            other.performance,
            other.performance_count)

        if tmp_value[0] != -1:
            tmp.is_set = True
            tmp.performance = tmp_value[0]
            tmp.performance_count = tmp_value[1]
        tmp.performance_review = self.performance_review + other.performance_review

        tmp_value = tmp.get_combined_value(
            self.standards, self.standards_count, other.standards, other.standards_count)

        if tmp_value[0] != -1:
            tmp.is_set = True
            tmp.standards = tmp_value[0]
            tmp.standards_count = tmp_value[1]
        tmp.standards_review = self.standards_review + other.standards_review

        tmp_value = tmp.get_combined_value(
            self.a11y, self.a11y_count, other.a11y, other.a11y_count)

        if tmp_value[0] != -1:
            tmp.is_set = True
            tmp.a11y = tmp_value[0]
            tmp.a11y_count = tmp_value[1]
        tmp.a11y_review = self.a11y_review + other.a11y_review
        return tmp

    def get_combined_value(self, val1, val1_count, val2, val2_count):
        """
        Combines two values and their counts based on their validity.
        This method takes two values and their counts.
        If both values are valid (not equal to -1),
        it returns the sum of the values and the sum of the counts.
        If neither value is valid, it returns -1 and 1.
        If only one value is valid, it returns that value and its count.

        Args:
            val1 (int or float): The first value.
            val1_count (int): The count of the first value.
            val2 (int or float): The second value.
            val2_count (int): The count of the second value.

        Returns:
            tuple: A tuple containing the combined value and the combined count.
        """
        val1_has_value = val1 != -1
        val2_has_value = val2 != -1

        if val1_has_value and val2_has_value:
            return (val1 + val2, val1_count + val2_count)

        if not val1_has_value and not val2_has_value:
            return (-1, 1)

        if val1_has_value:
            return (val1, val1_count)
        return (val2, val2_count)

    def __repr__(self):
        text = self.get_translation_text('TEXT_TEST_RATING_OVERVIEW').format(self.get_overall())
        if self.get_integrity_and_security() != -1:
            text += self.get_translation_text('TEXT_TEST_RATING_INTEGRITY_SECURITY').format(
                self.get_integrity_and_security())
        if self.get_performance() != -1:
            text += self.get_translation_text('TEXT_TEST_RATING_PERFORMANCE').format(
                self.get_performance())
        if self.get_a11y() != -1:
            text += self.get_translation_text('TEXT_TEST_RATING_ALLY').format(
                self.get_a11y())
        if self.get_standards() != -1:
            text += self.get_translation_text('TEXT_TEST_RATING_STANDARDS').format(
                self.get_standards())

        return text


class SiteTests: # pylint: disable=too-many-instance-attributes,missing-class-docstring
    __tablename__ = 'sitetests'

    site_id = 0
    id = 0
    test_date = datetime.now()
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

    def __init__(self, site_id, type_of_test, rating, test_date, json_check_data): # pylint: disable=too-many-arguments
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
        """
        Encodes the given review into UTF-8 format after removing 'GOV-IGNORE' from it.
        This method is designed to solve encoding problems that might occur when handling reviews.

        Parameters:
        review (str): The review text to be encoded.

        Returns:
        bytes: The encoded review in UTF-8 format.
        """
        review_encoded = str(review).replace('GOV-IGNORE', '').encode(
            'utf-8')  # för att lösa encoding-probs
        return review_encoded

    def todata(self):
        """
        Converts the object's data into a list of dictionaries.
        This method takes the data of the object and
        converts it into a list of dictionaries.
        Each dictionary contains the site id, type of test,
        ratings, date, reports, and data.
        The reports and data are decoded from utf-8 format.

        Returns:
            list: A list containing a dictionary of the object's data.
        """
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
            'data': self.json_check_data
        }]
        return result

    @staticmethod
    def fieldnames():
        """
        Get the field names for the SiteTests class.
        """
        result = ['site_id', 'type_of_test',
                  'rating', 'rating_sec', 'rating_perf',
                  'rating_a11y', 'rating_stand',
                  'date', 'report', 'report_sec',
                  'report_perf', 'report_a11y', 'report_stand',
                  'data']
        return result

    def __repr__(self):
        return f'<SiteTest {self.test_date}>'
