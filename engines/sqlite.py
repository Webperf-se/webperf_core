# -*- coding: utf-8 -*-
import sqlite3
from engines.utils import use_item

def db_tables(output_filename):
    """
    Prints the names of all tables in a SQLite database.

    Args:
        output_filename (str): The name of the SQLite database file.
    """
    conn = sqlite3.connect(output_filename)
    c = conn.cursor()

    sql_command = """SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"""
    c.execute(sql_command)
    print(c.fetchall())
    conn.commit()

    conn.close()


def add_site(input_filename, url, input_skip, input_take):
    """
    Add a site for a SQLite database and returns all subset of the sites.

    Args:
        input_filename (str): The name of the SQLite database file.
        url (str): The website URL of the site to be deleted.
        input_skip (int): The number of sites to skip before starting to take.
        input_take (int): The number of sites to take after skipping.

    Returns:
        list: A list of sites,
              where each site is represented as a list with two elements - id and website.
    """
    conn = sqlite3.connect(input_filename)
    c = conn.cursor()
    format_str = """INSERT INTO sites (title, website)
    VALUES ("{title}", "{website}");\n"""
    sql_command = format_str.format(title=url, website=url)

    c.execute(sql_command)
    conn.commit()

    conn.close()

    return read_sites(input_filename, input_skip, input_take)


def delete_site(input_filename, url, input_skip, input_take):
    """
    Deletes a site from a SQLite database and returns a subset of the remaining sites.

    Args:
        input_filename (str): The name of the SQLite database file.
        url (str): The website URL of the site to be deleted.
        input_skip (int): The number of sites to skip before starting to take.
        input_take (int): The number of sites to take after skipping.

    Returns:
        list: A list of sites,
              where each site is represented as a list with two elements - id and website.
    """
    conn = sqlite3.connect(input_filename)
    c = conn.cursor()
    format_str = """DELETE FROM sites WHERE website="{website}";\n"""
    sql_command = format_str.format(website=url)

    c.execute(sql_command)
    conn.commit()

    conn.close()

    return read_sites(input_filename, input_skip, input_take)


def read_sites(input_filename, input_skip, input_take):
    """
    Reads active sites from a SQLite database and returns a subset of them.

    Args:
        input_filename (str): The name of the SQLite database file.
        input_skip (int): The number of sites to skip before starting to take.
        input_take (int): The number of sites to take after skipping.

    Returns:
        list: A list of sites,
              where each site is represented as a list with two elements - id and website.
    """
    sites = []
    order_by = 'title ASC'

    conn = sqlite3.connect(input_filename)
    c = conn.cursor()

    current_index = 0
    for row in c.execute(f'SELECT id, website FROM sites WHERE active=1 ORDER BY {order_by}'):
        if use_item(current_index, input_skip, input_take):
            sites.append([row[0], row[1]])
        current_index += 1
    conn.close()
    return sites


def write_tests(output_filename, site_tests, _):
    """
    This function writes site test results into a SQLite database.

    Parameters:
    output_filename (str): The name of the SQLite database file.
    site_tests (list): A list of dictionaries, each containing the results of a site test.

    The function updates the 'sitetests' table in the database,
    setting the 'most_recent' field of previous tests to 0,
    and then inserts the new test results. If a database error occurs,
    the function attempts to handle it and 
    re-run the tests.
    """
    conn = sqlite3.connect(output_filename)
    cursor = conn.cursor()

    try:
        for test in site_tests:
            # set previous testresult as not latest
            format_str = (
                "UPDATE sitetests SET most_recent=0 WHERE site_id='{siteid}' AND "
                "type_of_test='{testtype}' AND most_recent=1;\n"
            )
            sql_command = format_str.format(
                siteid=test["site_id"], testtype=test["type_of_test"]
            )

            cursor.execute(sql_command)
            conn.commit()

            # update testresult for all sites
            format_str = (
                "INSERT INTO sitetests (site_id, test_date, type_of_test, check_report, "
                "check_report_sec, check_report_perf, check_report_a11y, check_report_stand, "
                "json_check_data, most_recent, rating, rating_sec, rating_perf, rating_a11y, "
                "rating_stand) VALUES ('{siteid}', '{testdate}', '{testtype}', '{report}', "
                "'{report_sec}', '{report_perf}', '{report_a11y}', '{report_stand}', '{json}', "
                "'{recent}', '{rating}', '{rating_sec}', '{rating_perf}', '{rating_a11y}', "
                "'{rating_stand}');\n"
            )
            sql_command = format_str.format(
                siteid=test["site_id"], testdate=test["date"],
                testtype=test["type_of_test"],
                report=test["report"], report_sec=test["report_sec"],
                report_perf=test["report_perf"], report_a11y=test["report_a11y"],
                report_stand=test["report_stand"], json=test["data"],
                recent=1, rating=test["rating"], rating_sec=test["rating_sec"],
                rating_perf=test["rating_perf"], rating_a11y=test["rating_a11y"],
                rating_stand=test["rating_stand"]
            )

            cursor.execute(sql_command)
            conn.commit()
        conn.close()
    except (sqlite3.IntegrityError, sqlite3.OperationalError) as ex:
        str_ex = str(ex)
        is_rating = 'rating_sec' in str_ex or 'rating_perf' in str_ex or \
                    'rating_a11y' in str_ex or 'rating_stand' in str_ex
        is_report = 'check_report_sec' in str_ex or 'check_report_perf' in str_ex or \
                    'check_report_a11y' in str_ex or 'check_report_stand' in str_ex
        if is_rating or is_report:
            print('db -', str_ex)
            ensure_latest_db_version(output_filename)
            write_tests(output_filename, site_tests, _)
            print('db - upgrading db')
        else:
            print('db exception', str_ex)


def ensure_latest_db_version(output_filename):
    """
    This function updates the 'sitetests' table in the SQLite database to the latest version.

    Parameters:
    output_filename (str): The name of the SQLite database file.

    The function adds new columns to the 'sitetests' table if they do not exist,
    ensuring that the table schema is up-to-date.
    """
    conn = sqlite3.connect(output_filename)
    c = conn.cursor()

    sql_command = """ALTER TABLE sitetests ADD check_report_stand text;\n"""
    c.execute(sql_command)

    sql_command = """ALTER TABLE sitetests ADD check_report_a11y text;\n"""
    c.execute(sql_command)

    sql_command = """ALTER TABLE sitetests ADD check_report_perf text;\n"""
    c.execute(sql_command)

    sql_command = """ALTER TABLE sitetests ADD check_report_sec text;\n"""
    c.execute(sql_command)

    sql_command = """ALTER TABLE sitetests ADD rating_stand float NOT NULL DEFAULT -1;\n"""
    c.execute(sql_command)

    sql_command = """ALTER TABLE sitetests ADD rating_a11y float NOT NULL DEFAULT -1;\n"""
    c.execute(sql_command)

    sql_command = """ALTER TABLE sitetests ADD rating_perf float NOT NULL DEFAULT -1;\n"""
    c.execute(sql_command)

    sql_command = """ALTER TABLE sitetests ADD rating_sec float NOT NULL DEFAULT -1;\n"""
    c.execute(sql_command)

    conn.commit()
    conn.close()
