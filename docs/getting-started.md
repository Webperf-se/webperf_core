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
| -t/--test <test number> | run ONE test (use ? to list available tests) |
| -r/--review | show reviews in terminal |
| -i/--input <file path> | input file path (.json/.sqlite/.csv/.xml) |
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

List available test:
`python default.py -t ?`

```shell
Valid arguments for option -t/--test:
-t 2    : 404 (Page not Found)
-t 6    : HTML Validation
-t 7    : CSS Validation
-t 9    : Standard files
-t 15   : Performance (Sitespeed.io)
-t 18   : Accessibility (Pa11y)
-t 20   : Integrity & Security (Webbkoll)
-t 21   : HTTP & Network
-t 22   : Energy Efficiency (Website Carbon Calculator)
-t 23   : Tracking and Privacy (Beta)
-t 24   : Email (Beta)
-t 25   : Software
-t 26   : Accessibility Statement (Alfa)
```

Run only `Standard files` test with review against one specific url ([https://webperf.se/](https://webperf.se/)):
`python default.py -r -t 9 -u https://webperf.se/`

```shell
###############################################
# Testing website https://webperf.se/

## Test: 9 - Standard files

Started: 2024-05-19 14:58:59
Finished: 2024-05-19 14:59:03

### Rating:
- Overall: 4.94
- Integrity & Security: 5.0
- Standards: 4.92

### Review:

#### Overall:
#### Standards:
- The Sitemap is good. ( 4.75 rating )
```

Run only `Standard files` test with review, show all reviews against one specific url ([https://webperf.se/](https://webperf.se/)):
`python default.py -r -t 9 --setting improve-only=false -u https://webperf.se/`

```shell
###############################################
# Testing website https://webperf.se/

## Test: 9 - Standard files

Started: 2024-05-19 15:00:43
Finished: 2024-05-19 15:00:48

### Rating:
- Overall: 4.94
- Integrity & Security: 5.0
- Standards: 4.92

### Review:

#### Overall:
- RSS subscription found in webpage metadata. ( 5.00 rating )
#### Integrity & Security:
- security.txt seems to work. ( 5.00 rating )
#### Standards:
- robots.txt seems ok. ( 5.00 rating )
- The Sitemap is good. ( 4.75 rating )
- security.txt seems to work. ( 5.00 rating )
```


Run ALL test except tests `18` and `20` with review, show all reviews against one specific url ([https://webperf.se/](https://webperf.se/)):
`python default.py -r -t -18,-20 -u https://webperf.se/`

```shell
###############################################
# Testing website https://webperf.se/

## Test: 1 - Performance (Google Lighthouse)

Started: 2024-05-25 22:18:52
Finished: 2024-05-25 22:19:25

### Rating:
- Overall: 3.5
- Performance: 4.24
- Standards: 5.0

### Review:

#### Overall:
- About average speed.
#### Performance:
- Total Blocking Time: 510 ms ( 2.85 rating )
- Cumulative Layout Shift: 0.244 ( 2.55 rating )
- Largest Contentful Paint: 2.6 s ( 4.40 rating )
- First Contentful Paint: 2.0 s ( 4.20 rating )
- Minimize main-thread work ( 1.00 rating )
- Largest Contentful Paint element ( 1.00 rating )
- Avoid large layout shifts ( 1.00 rating )
- Eliminate render-blocking resources ( 1.00 rating )
- Avoid an excessive DOM size ( 1.00 rating )
- Max Potential First Input Delay: 260 ms ( 2.30 rating )
- Ensure text remains visible during webfont load:  ( 2.50 rating )
- Image elements do not have explicit `width` and `height`:  ( 2.50 rating )
- Serve static assets with an efficient cache policy: 1 resource found ( 2.50 rating )
- Defer offscreen images: Potential savings of 23 KiB ( 2.50 rating )
- Time to Interactive: 3.4 s ( 4.65 rating )
- First Meaningful Paint: 2.0 s ( 4.75 rating )

...

## Test: 26 - Accessibility Statement

Started: 2024-05-25 22:26:23
Finished: 2024-05-25 22:26:52

### Rating:
- Overall: 3.0
- A11y: 3.0

### Review:

#### Overall:
- Accessibility statement: https://webperf.se/webbanalys/kap3/#om-statistik-och-vanliga-misstag
- Missing or has an incorrect link to DIGG's report function ( 1.00 rating )
- Link to the accessibility statement was found on a deeper link level than it should ( 3.00 rating )
- Unable to find when the accessibility statement was updated ( 1.00 rating )
#### A11y:
- Self-indicates that website is not compliant with legal requirements ( 1.00 rating )

```
