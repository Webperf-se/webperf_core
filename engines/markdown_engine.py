# -*- coding: utf-8 -*-

from models import Rating


def write_tests(output_filename, testresults, sites):
    """
    Writes site test results to a CSV formated file from a given list of site tests.
    Compared to csv engine it is optimized for goverment reports and is missing some fields

    Args:
        output_filename (str): The name of the output file.
        site_tests (list): A list of site tests.
        sites (list) : A list of sites.

    Returns:
        None
    """

    site_url = ''
    data = {}
    for testresult in testresults:
        if testresult["site_id"] not in data:
            tmp_sites = dict(sites)
            site_url = tmp_sites.get(testresult['site_id'])

            data[testresult["site_id"]] = {
                "url": site_url,
                "date": testresult["date"],
                "report": testresult["report"],
                "report_sec": testresult["report_sec"],
                "report_perf": testresult["report_perf"],
                "report_a11y": testresult["report_a11y"],
                "report_stand": testresult["report_stand"],
                "rating": to_rating(testresult["rating"]),
                "rating_sec": to_rating(testresult["rating_sec"]),
                "rating_perf": to_rating(testresult["rating_perf"]),
                "rating_a11y": to_rating(testresult["rating_a11y"]),
                "rating_stand": to_rating(testresult["rating_stand"])
            }
        else:
            data[testresult["site_id"]]["report"] += testresult["report"]
            data[testresult["site_id"]]["report_sec"] += testresult["report_sec"]
            data[testresult["site_id"]]["report_perf"] += testresult["report_perf"]
            data[testresult["site_id"]]["report_a11y"] += testresult["report_a11y"]
            data[testresult["site_id"]]["report_stand"] += testresult["report_stand"]
            data[testresult["site_id"]]["rating"] += to_rating(testresult["rating"])
            data[testresult["site_id"]]["rating_sec"] += to_rating(testresult["rating_sec"])
            data[testresult["site_id"]]["rating_perf"] += to_rating(testresult["rating_perf"])
            data[testresult["site_id"]]["rating_a11y"] += to_rating(testresult["rating_a11y"])
            data[testresult["site_id"]]["rating_stand"] += to_rating(testresult["rating_stand"])

    markdown = []
    for _, site_data in data.items():
        markdown.extend(create_markdown_for_url(site_data))

    with open(output_filename, 'w', encoding='utf-8') as outfile:
        outfile.write('\n'.join(markdown))

def to_rating(points):
    rating = Rating(None, True)
    rating.set_overall(points)
    return rating

def create_markdown_for_url(site_data):
    markdown = [
       "# WebPerf_core Result(s)",
       f"Website: {site_data['url']}",
       f"Date: {site_data['date']}",
       "",
       "# Rating:",
       f"- Overall: {site_data['rating'].get_overall()}",
       f"- A11y: {site_data['rating_a11y'].get_overall()}",
       f"- Integrity & Security: {site_data['rating_sec'].get_overall()}",
       f"- Performance: {site_data['rating_perf'].get_overall()}",
       f"- Standards: {site_data['rating_stand'].get_overall()}",
       "",
       "# Review"
    ]

    if site_data['report']:
        markdown.append("## Overall:")
        markdown.append(site_data['report'].replace('\r\n', '\n'))

    if site_data['report_a11y']:
        markdown.append("## A11y:")
        markdown.append(site_data['report_a11y'].replace('\r\n', '\n'))

    if site_data['report_sec']:
        markdown.append("## Integrity & Security:")
        markdown.append(site_data['report_sec'].replace('\r\n', '\n'))

    if site_data['report_perf']:
        markdown.append("## Performance:")
        markdown.append(site_data['report_perf'].replace('\r\n', '\n'))

    if site_data['report_stand']:
        markdown.append("## Standards:")
        markdown.append(site_data['report_stand'].replace('\r\n', '\n'))

    return markdown
