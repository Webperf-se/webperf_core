# -*- coding: utf-8 -*-

import re
from models import Rating


def write_tests(output_filename, testresults, sites, global_translation):
    """
    Writes site test results to a CSV formated file from a given list of site tests.
    Compared to csv engine it is optimized for goverment reports and is missing some fields

    Args:
        output_filename (str): The name of the output file.
        site_tests (list): A list of site tests.
        sites (list) : A list of sites.
        global_translation : GNUTranslations
        An object that handles the translation of text in the context of internationalization.

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
                "rating": to_rating(testresult["rating"], global_translation),
                "rating_sec": to_rating(testresult["rating_sec"], global_translation),
                "rating_perf": to_rating(testresult["rating_perf"], global_translation),
                "rating_a11y": to_rating(testresult["rating_a11y"], global_translation),
                "rating_stand": to_rating(testresult["rating_stand"], global_translation)
            }
        else:
            data[testresult["site_id"]]["report"] += testresult["report"]
            data[testresult["site_id"]]["report_sec"] += testresult["report_sec"]
            data[testresult["site_id"]]["report_perf"] += testresult["report_perf"]
            data[testresult["site_id"]]["report_a11y"] += testresult["report_a11y"]
            data[testresult["site_id"]]["report_stand"] += testresult["report_stand"]
            data[testresult["site_id"]]["rating"] += to_rating(
                testresult["rating"], global_translation)
            data[testresult["site_id"]]["rating_sec"] += to_rating(
                testresult["rating_sec"], global_translation)
            data[testresult["site_id"]]["rating_perf"] += to_rating(
                testresult["rating_perf"], global_translation)
            data[testresult["site_id"]]["rating_a11y"] += to_rating(
                testresult["rating_a11y"], global_translation)
            data[testresult["site_id"]]["rating_stand"] += to_rating(
                testresult["rating_stand"], global_translation)

    markdown_list = []
    for _, site_data in data.items():
        markdown_list.extend(create_markdown_for_url(site_data))

    markdown = '\n'.join(markdown_list)

    # Fix malformated markdown html entities
    regex = r"[^`]\<"
    subst = "`<"
    markdown = re.sub(regex, subst, markdown, 0, re.MULTILINE)
    regex = r"\>[^`]"
    subst = ">`"
    markdown = re.sub(regex, subst, markdown, 0, re.MULTILINE)

    # Fix GitHub Issues/PR references
    regex = r"([^`])(\#[0-9]+)([^`])"
    subst = r"\1`\2`\3"
    markdown = re.sub(regex, subst, markdown, 0, re.MULTILINE)

    # Fix header level from terminal format to markdown
    regex = r"^##### "
    subst = "### "
    markdown = re.sub(regex, subst, markdown, 0, re.MULTILINE)
    regex = r"^###### "
    subst = "#### "
    markdown = re.sub(regex, subst, markdown, 0, re.MULTILINE)

    # Make CSP Recommendation into code format
    regex = (
        r"(^- )"
        r"(default-src|base-uri|img-src|script-src|form-action|"
        r"style-src|child-src|object-src|frame-ancestors|connect-src|font-src)"
        r"( .*)$")
    subst = r"\1`\2\3`"
    markdown = re.sub(regex, subst, markdown, 0, re.MULTILINE)


    with open(output_filename, 'w', encoding='utf-8') as outfile:
        outfile.write(markdown)

def to_rating(points, global_translation):
    rating = Rating(global_translation, False)
    if points != -1.0:
        rating.set_overall(points)
    return rating

def create_markdown_for_url(site_data):
    markdown = [
       "# WebPerf_core Result(s)",
       f"Website: {site_data['url']}",
       f"Date: {site_data['date']}",
       "",
       "# Rating:"
    ]

    if site_data['rating'].isused():
        markdown.append(f"- Overall: {site_data['rating'].get_overall()}")
    if site_data['rating_a11y'].isused():
        markdown.append(f"- A11y: {site_data['rating_a11y'].get_overall()}")
    if site_data['rating_sec'].isused():
        markdown.append(f"- Integrity & Security: {site_data['rating_sec'].get_overall()}")
    if site_data['rating_perf'].isused():
        markdown.append(f"- Performance: {site_data['rating_perf'].get_overall()}")
    if site_data['rating_stand'].isused():
        markdown.append(f"- Standards: {site_data['rating_stand'].get_overall()}")


    markdown.append("")
    markdown.append("# Review")
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
