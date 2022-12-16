# -*- coding: utf-8 -*-
from engines.utils import use_item
import sqlite3


def db_tables(output_filename):
    conn = sqlite3.connect(output_filename)
    c = conn.cursor()

    sql_command = """SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"""
    c.execute(sql_command)
    print(c.fetchall())
    conn.commit()

    conn.close()


def add_site(input_filename, url, input_skip, input_take):
    conn = sqlite3.connect(input_filename)
    c = conn.cursor()
    format_str = """INSERT INTO sites (title, website)
    VALUES ("{title}", "{website}");\n"""
    sql_command = format_str.format(title=url, website=url)

    c.execute(sql_command)
    conn.commit()

    conn.close()

    print(_('TEXT_WEBSITE_URL_ADDED').format(url))

    return read_sites(input_filename, input_skip, input_take)


def delete_site(input_filename, url, input_skip, input_take):
    conn = sqlite3.connect(input_filename)
    c = conn.cursor()
    format_str = """DELETE FROM sites WHERE website="{website}";\n"""
    sql_command = format_str.format(website=url)

    c.execute(sql_command)
    conn.commit()

    conn.close()

    print(_('TEXT_WEBSITE_URL_DELETED').format(url))

    return read_sites(input_filename, input_skip, input_take)


def read_sites(input_filename, input_skip, input_take):
    sites = list()
    order_by = 'title ASC'

    conn = sqlite3.connect(input_filename)
    c = conn.cursor()

    current_index = 0
    for row in c.execute('SELECT id, website FROM sites WHERE active=1 ORDER BY {0}'.format(order_by)):
        if use_item(current_index, input_skip, input_take):
            sites.append([row[0], row[1]])
        current_index += 1
    conn.close()
    return sites


def write_tests(output_filename, siteTests):
    conn = sqlite3.connect(output_filename)
    c = conn.cursor()

    try:
        for test in siteTests:
            # set previous testresult as not latest
            format_str = """UPDATE sitetests SET most_recent=0 WHERE site_id="{siteid}" AND type_of_test="{testtype}" AND most_recent=1;\n"""
            sql_command = format_str.format(
                siteid=test["site_id"], testtype=test["type_of_test"])

            c.execute(sql_command)
            conn.commit()

            # update testresult for all sites
            format_str = """INSERT INTO sitetests (site_id, test_date, type_of_test,
             check_report, check_report_sec, check_report_perf, check_report_a11y, check_report_stand,
             json_check_data, most_recent, rating, rating_sec, rating_perf, rating_a11y, rating_stand)
            VALUES ("{siteid}", "{testdate}", "{testtype}", "{report}", "{report_sec}", "{report_perf}", "{report_a11y}", "{report_stand}", "{json}", "{recent}", "{rating}", "{rating_sec}", "{rating_perf}", "{rating_a11y}", "{rating_stand}");\n"""
            sql_command = format_str.format(siteid=test["site_id"], testdate=test["date"], testtype=test["type_of_test"],
                                            report=test["report"],
                                            report_sec=test["report_sec"], report_perf=test["report_perf"], report_a11y=test[
                                                "report_a11y"], report_stand=test["report_stand"],
                                            json=test["data"], recent=1, rating=test["rating"], rating_sec=test["rating_sec"], rating_perf=test["rating_perf"], rating_a11y=test["rating_a11y"], rating_stand=test["rating_stand"])

            #print("WRITE TEST SQL COMMAND:\r\n {0}".format(sql_command))
            c.execute(sql_command)
            conn.commit()
        conn.close()
    except Exception as ex:
        if 'rating_sec' in str(ex) or 'rating_perf' in str(ex) or 'rating_a11y' in str(ex) or 'rating_stand' in str(ex) or 'check_report_sec' in str(ex) or 'check_report_perf' in str(ex) or 'check_report_a11y' in str(ex) or 'check_report_stand' in str(ex):
            # automatically update database
            print('db -', str(ex))
            ensure_latest_db_version(output_filename)
            write_tests(output_filename, siteTests)

            print('db - upgrading db')
        else:
            print('db exception', str(ex))


def ensure_latest_db_version(output_filename):
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
