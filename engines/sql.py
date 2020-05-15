#-*- coding: utf-8 -*-

def write_tests(output_filename, siteTests):
    with open(output_filename, 'w') as outfile:
        for test in siteTests:
            format_str = """INSERT INTO sitetests (site_id, test_date, type_of_test, check_report, json_check_data, most_recent, rating)
            VALUES ("{siteid}", "{testdate}", "{testtype}", "{report}", "{json}", "{recent}", "{rating}");\n"""
            sql_command = format_str.format(siteid=test["site_id"], testdate=test["date"], testtype=test["type_of_test"], report=test["report"], json=test["data"], recent=1, rating=test["rating"])
                    
            outfile.write(sql_command)