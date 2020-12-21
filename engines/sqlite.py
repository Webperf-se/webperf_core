# -*- coding: utf-8 -*-
from engines.utils import use_website
import sqlite3


def db_tables(output_filename):
    conn = sqlite3.connect(output_filename)
    c = conn.cursor()

    sql_command = """SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"""
    c.execute(sql_command)
    print(c.fetchall())
    conn.commit()

    conn.close()


def add_site(input_filename, url):
    conn = sqlite3.connect(input_filename)
    c = conn.cursor()
    format_str = """INSERT INTO sites (title, website)
    VALUES ("{title}", "{website}");\n"""
    sql_command = format_str.format(title=url, website=url)

    c.execute(sql_command)
    conn.commit()

    conn.close()

    print(_('TEXT_WEBSITE_URL_ADDED').format(url))

    return read_sites(input_filename)


def delete_site(input_filename, url):
    conn = sqlite3.connect(input_filename)
    c = conn.cursor()
    format_str = """DELETE FROM sites WHERE website="{website}";\n"""
    sql_command = format_str.format(website=url)

    c.execute(sql_command)
    conn.commit()

    conn.close()

    print(_('TEXT_WEBSITE_URL_DELETED').format(url))

    return read_sites(input_filename, 0, -1)


def read_sites(input_filename, input_skip, input_take):
    sites = list()
    order_by = 'title ASC'

    conn = sqlite3.connect(input_filename)
    c = conn.cursor()

    current_index = 0
    for row in c.execute('SELECT id, website FROM sites WHERE active=1 ORDER BY {0}'.format(order_by)):
        if use_website(current_index, input_skip, input_take):
            sites.append([row[0], row[1]])
        current_index += 1
    conn.close()
    return sites


def write_tests(output_filename, siteTests):
    conn = sqlite3.connect(output_filename)
    c = conn.cursor()

    for test in siteTests:
        # set previous testresult as not latest
        format_str = """UPDATE sitetests SET most_recent=0 WHERE site_id="{siteid}" AND type_of_test="{testtype}" AND most_recent=1;\n"""
        sql_command = format_str.format(
            siteid=test["site_id"], testtype=test["type_of_test"])

        c.execute(sql_command)
        conn.commit()

        # update testresult for all sites
        format_str = """INSERT INTO sitetests (site_id, test_date, type_of_test, check_report, json_check_data, most_recent, rating)
        VALUES ("{siteid}", "{testdate}", "{testtype}", "{report}", "{json}", "{recent}", "{rating}");\n"""
        sql_command = format_str.format(siteid=test["site_id"], testdate=test["date"], testtype=test["type_of_test"],
                                        report=test["report"], json=test["data"], recent=1, rating=test["rating"])

        c.execute(sql_command)
        conn.commit()

    conn.close()
