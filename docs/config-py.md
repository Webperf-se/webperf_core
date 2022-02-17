# Why config.py and what does it do?

Write more about this configuration file and what you control from it.


## Why rename SAMPLE-config.py?

The reason for this is because if you download a new version of the code, your settings or data should not be overwritten by accident.

Because of this you need to copy `SAMPLE-config.py` and name the new version `config.py`.

## What do every configuration do?


### useragent

This variable is used as user agent in the following tests:

- CSS Validation (used against W3C service)
- HTML Validation (used against W3C service)
- 404 (Page Not Found, used against your website)
- Standard Files (used against your website)
- HTTP Test (used against your website)
- Google Lighthouse based test  (used against service when using test in that mode)


### googlePageSpeedApiKey

You can read more about this variable on the [Google Lighthouse Based test section](tests/google-lighthouse-based.md).
This variable is only used when `lighthouse_use_api` variable is set to `True`.

### http_request_timeout

This variable is used as request timeout in the following tests:

- CSS Validation (used against W3C service)
- HTML Validation (used against W3C service)
- 404 (Page Not Found, used against your website)
- Users’ integrity test against Webbkoll (used against service)
- Standard Files (used against your website)
- HTTP Test (used against your website)
- Google Lighthouse based test (used against service when using test in that mode)

### webbkoll_sleep

This variable is used as sleep time between checking status against service following tests:

- Users’ integrity test against Webbkoll (used against service)
- Frontend quality against Yellow Lab Tools (used against service when using test in that mode)

### css_review_group_errors

Groups error messages in the CSS Validation review by removing variable names and replacing them with `X`.
This is usefull if you want to get a first overview or if you have a lot of errors of the same type.

### review_show_improvements_only

Setting this variable to true will result in only showing reviews that has a rating below 5.0.
This is good if you only want to show reviews that you can improve.

### ylt_use_api

NOTE: This should probably be removed, it tells Frontend quality against Yellow Lab Tools
to be using https://yellowlab.tools/ api:s instead of a local version.

### lighthouse_use_api

This variable tells Google Lighthouse based test(s)
to be using Google API version instead of local version.
Please note that if you set this to true, you need to supply `googlePageSpeedApiKey` also.

### sitespeed_use_docker

This variable tells sitespeed based test(s) to use docker image version instead of NPM version.
Please read more about this on [SiteSpeed test section](tests/sitespeed.md).

### sitespeed_iterations

This variable tells sitespeed based test(s) how many iterations it should do against the url to get the best measurement.
Please read more about this on [SiteSpeed test section](tests/sitespeed.md).

### locales

Who knows what this is for... :)

