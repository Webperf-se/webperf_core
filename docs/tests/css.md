# CSS Validation
[![Regression Test - CSS Validation Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-css.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-css.yml)

This test is validating all used CSS on the url specified.
We are currently sending following sources to [W3C CSS Validation](https://validator.w3.org/nu/) for validation:
- Inline CSS in `style`-element
- Inline CSS in `style`-attribute
- CSS referenced using `link`-element

Addition to test all of above sources (compared to only test inline styles that [W3C CSS Validation](https://validator.w3.org/nu/) do) we are also adding support for:
- Draft CSS properties by using [MDN Web Docs - CSS reference](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference) as guidance.
- `100%` as valid value of `font-stretch`
- Draft CSS functions by using [MDN Web Docs - CSS reference](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference) as guidance.

## How are rating being calculated?

For every source (see above) we are calculating rating based on:
- Number of different error types
- Number of total number of errors

we are then combining the results.

Math used are:
- `rating_number_of_error_types = 5.0 - (number_of_error_types / 5.0)`
- `rating_number_of_errors = 5.0 - ((number_of_errors / 2.0) / 5.0)`

As always, minimum rating are 1.0.

## Read more

## How to setup?

### Prerequirements

* Fork this repository
* As we are using external service ( https://validator.w3.org/nu/ and https://developer.mozilla.org/en-US/docs/Web/CSS/Reference ) your site needs to be publicly available and the machine running
this test needs to be able to access external service.

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)
* Next steps depends on what mode you want to runt test in

#### Call service

By settings `w3c_use_website = True` in `config.py` you tell the test
you want to use w3c service to test url.
This means that you can ONLY test public facing websites.

* Beside making sure to set above value to `True` you dont need to do anything more.

#### Jar

By settings `w3c_use_website = False` in `config.py` you tell the test
you want to use a version able to test privat websites like a test environment not open for public.

* Download and install Java (JDK 8 or above)
* [Download latest vnu.jar](https://github.com/validator/validator/releases/download/latest/vnu.jar) and place it in your webperf-core directory
* Set `w3c_use_website = False` in `config.py`

## FAQ

No frequently asked questions yet :)

