# Getting started

Nice that you are here looking how to set webperf-core up :)

There are three methods that we have test and know work when get started.

The easiest to setup are GitHub Actions for public facing websites.

If you want to test/verify private websites like acceptance test environments and more you are probably best to choose the docker or local machine method.
You can read more about every method on the links below.

- [Using GitHub Actions](getting-started-github-actions.md)
- [Using Docker](getting-started-docker.md)
- [Using Local Machine](getting-started-local.md)

After you have choosen then method to get started and followed the method specific instructions 
you can view more general information below.

## Options and arguments
|Argument|What happens|
|---|---|
| -h/--help | Help information on how to use script |
| -u/--url <site url> | website url to test against |
| -t/--test <test numbers> | test number(s) to run, comma separated (use ? to list available tests) |
| -r/--review | show reviews in terminal |
| -i/--input <file path> | input file path, see [input formats](#input-formats) |
| --input-skip <number> | number of items to skip |
| --input-take <number> | number of items to take |
| -o/--output <file path> | output file path (.json/.sqlite/.csv/.sql/.md) |
| -a/--addUrl <site url> | website url (required in compination with -i/--input) |
| -d/--deleteUrl <site url> | website url (required in compination with -i/--input) |
| -L/--language <lang code> | language used for output(en = default/sv) |
| -s/--setting <key>=<value> | override configuration for current run (use ? to list available settings) |


## Examples


Run all tests with review against one specific url ([https://webperf.se/](https://webperf.se/)):
`python default.py -r -u https://webperf.se/`

List available tests:
`python default.py -t ?`

```shell
Valid arguments for option -t/--test:
-t 2	: 404 (Page not Found)
-t 9	: Standard files
-t 15	: Performance (Sitespeed.io)
-t 18	: Accessibility (Pa11y)
-t 20	: Integrity & Security (Webbkoll)
-t 21	: HTTP & Network
-t 22	: Energy Efficiency (Website Carbon Calculator)
-t 23	: Tracking and Privacy
-t 24	: Email (Beta)
-t 25	: Software
-t 26	: Accessibility Statement (Alfa)
-t 27	: CSS Lint (Stylelint)
-t 28	: HTML Lint (html-validate)
-t 29	: JS Lint (ESLint)
-t 30	: Accessibility, Best Practice, Performance & SEO (Lighthouse)
-t 31	: Privacy (Webbkoll)
-t 32	: DNS (Zonemaster)
```

Run one test, here `Email`, with review against one URL:
`python default.py -r -t 24 -u https://webperf.se/`

```shell
###############################################
# Testing website https://webperf.se

Started: 2026-10-09 23:01:56
## Test: 24 - Email (Beta)

Started: 2026-10-09 23:01:56
Finished: 2026-10-09 23:02:57

### Rating: 
- Overall: 4.15
- Integrity & Security: 4.55
- Standards: 4.09

### Review:
 
#### Overall:
#### Integrity & Security:
- MX DNS IPv4 record redundance ( 5.00 rating )
- MX DNS IPv6 record redundance ( 5.00 rating )
- MX DNS servers in countries that are GDPR compliant: SE ( 5.00 rating )
- MTA-STS DNS record not found ( 1.00 rating )
- MTA-STS TXT looks good ( 5.00 rating )
- SPF DNS record found ( 5.00 rating )
- SPF DNS record uses hard fail ( 5.00 rating )
- SPF servers in countries that are GDPR compliant: SE ( 5.00 rating )
- DMARC DNS record found ( 5.00 rating )
- DMARC DNS record is using 'quarantine' for policy ( 4.00 rating )
- DMARC DNS record is using PCT ( 5.00 rating )
#### Standards:
- ...
```

Run two tests in one go and save the result as JSON. The file gets one entry per test and one combined entry, see [How ratings are calculated](rating.md):
`python default.py -t 21,24 -u https://webperf.se/ -o reports/webperf-se.json`

## Input formats

`-i` decides how to read the site list from the file ending:

| Ending | What is read |
|---|---|
| `.json` | A list of sites, the format `-A` writes. Also the default for any other ending. |
| `.csv` | A header row `id,website` followed by one site per row, or one URL per line without a header. |
| `.sqlite` | The `sites` table of a webperf-core SQLite database. |
| `.xml`, `.xml.gz` | A sitemap, every URL in it becomes a site. Can be a URL such as `https://example.com/sitemap.xml`. |
| `.result` | The URLs from earlier sitespeed.io runs stored under `general.cache.folder`. |

`--input-skip` and `--input-take` apply to every format.
