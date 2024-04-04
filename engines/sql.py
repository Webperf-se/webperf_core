# -*- coding: utf-8 -*-
from engines.utils import use_item

def write_tests(output_filename, site_tests, input_skip, input_take, _):
    """
    Writes site test results to a file from a given list of site tests.

    Args:
        output_filename (str): The name of the output file.
        site_tests (list): A list of site tests.
        input_skip (int): The number of tests to skip before starting to take.
        input_take (int): The number of tests to take after skipping.
        _ : Unused parameter.

    Returns:
        None
    """
    with open(output_filename, 'w', encoding='utf-8') as outfile:
        current_index = 0
        for test in site_tests:
            if use_item(current_index, input_skip, input_take):
                # update testresult for all sites
                format_str = """INSERT INTO sitetests (site_id, test_date, type_of_test,
                check_report, check_report_sec, check_report_perf, check_report_a11y, check_report_stand,
                json_check_data, most_recent, rating, rating_sec, rating_perf, rating_a11y, rating_stand)
                VALUES ("{siteid}", "{testdate}", "{testtype}", "{report}", "{report_sec}",
                  "{report_perf}", "{report_a11y}", "{report_stand}", "{json}", "{recent}",
                  "{rating}", "{rating_sec}", "{rating_perf}", "{rating_a11y}",
                  "{rating_stand}");\n"""
                sql_command = format_str.format(
                    siteid=test["site_id"],
                    testdate=test["date"],
                    testtype=test["type_of_test"],
                    report=test["report"],
                    report_sec=test["report_sec"],
                    report_perf=test["report_perf"],
                    report_a11y=test["report_a11y"],
                    report_stand=test["report_stand"],
                    json=test["data"],
                    recent=1,
                    rating=test["rating"],
                    rating_sec=test["rating_sec"],
                    rating_perf=test["rating_perf"],
                    rating_a11y=test["rating_a11y"],
                    rating_stand=test["rating_stand"]
                )
            current_index += 1
            outfile.write(sql_command)
