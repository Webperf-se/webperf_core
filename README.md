The project goal is to help identify and improve the web over time, one improvment at a time.
It tries to do this by giving you a weighted list of improvment you can (and probably should do) to your website.


# Features

* Run same test(s) used by [WebPerf.se](https://webperf.se/) without [WebPerf Premium](https://webperf.se/erbjudande/)
* Verify that you have done the basics for your website in:
  * Security
  * User Integrity
  * Performance
  * Accessibility
  * Accessibility statement
  * SEO
  * Code Quality
  * Networking
  * World Wide Web Standards
  * Email Standards
  * Software being used
* Validate new release before going into production
* Test other/more pages then [WebPerf.se](https://webperf.se/) do


# Getting Started

Easiest setup for testing public websites are by using GitHub Actions
but you can run this project in many ways and what you choose depends on your needs.

[Read more about how to get started](./docs/getting-started.md)

- [Using GitHub Actions](./docs/getting-started-github-actions.md)
- [Using Local Machine](./docs/getting-started-local.md)
- [Using Docker](./docs/getting-started-docker.md)


# Tests

Webperf Core consists of many different tests. [Read general information about our tests](./docs/tests/README.md) or go directly to a specific test below.

* [Accessibility (Pa11y)](./docs/tests/pa11y.md)
* [Website performance (SiteSpeed)](./docs/tests/sitespeed.md)
* [Validate 404 page (by default checks for Swedish text, though)](./docs/tests/page-not-found.md)
* [Security, data-protecting & Integrity (Webbkoll)](./docs/tests/webbkoll.md)
* [Energy Efficiency](./docs/tests/energy-efficiency.md)
* [Standard files](./docs/tests/standard.md)
* [HTTP and Network](./docs/tests/http.md)
* [Tracking & Integrity](./docs/tests/tracking.md)
* [Email (Beta)](./docs/tests/email.md)
* [Software](./docs/tests/software.md)
* [Accessibility Statement (Alpha)](./docs/tests/a11y-statement.md)
* [CSS (StyleLint)](./docs/tests/css-linting.md)
* [HTML (html-validate)](./docs/tests/html-validate.md)
* [Javascript (ESlint)](./docs/tests/js-linting.md)
* [Accessibility, Best practice, Performance, SEO (Google Lighthouse)](./docs/tests/google-lighthouse.md)


# Contribute

Do you want to contribute?

[Read more about how to contribute](./docs/CONTRIBUTING.md)


# Need help?

It is often worthwhile to google/dockduckgo the error messages you get.
If you give up the search then you can always [check if someone on our Slack channel](https://webperf.se/articles/webperf-pa-slack/) have time to help you,
but don’t forget to paste your error message directly in the first post.
Or, if you think your error are common for more people than yourself, [post an issue here at Github](https://github.com/Webperf-se/webperf_core/issues/new/choose).


# Third party

Think this is cool and want to see more?
Why not look at third parties.

[Read more about third party](./docs/thirdparty.md)



# Credits

We could not do this without all help from contributors and other projects we use.

[Read more about them under credits](./CREDITS.md)