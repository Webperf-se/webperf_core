# Why config.py and what does it do?

Write more about this configuration file and what you control from it.


## Why copy and rename defaults/config.py?

You *ONLY* need to copy defaults/config.py IF you want to change any settings.
Most people can use the default settings.
You should not change settings directly in defaults/config.py,
the reason for this is because if you download a new version of the code, your settings or data should not be overwritten by accident.

Because of this you need to copy `defaults/config.py` and name the new version `config.py` and place it in root folder.

## What do every configuration do?


### useragent

This variable is used as user agent in the following tests:

- CSS Validation (used against W3C service)
- HTML Validation (used against W3C service)
- 404 (Page Not Found, used against your website)
- Standard Files (used against your website)
- HTTP Test (used against your website)
- Google Lighthouse based test  (used against service when using test in that mode)


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

### general.review.improve-only

Setting this variable to true will result in only showing reviews that has a rating below 5.0.
This is good if you only want to show reviews that you can improve.

### sitespeed_use_docker

This variable tells sitespeed based test(s) to use docker image version instead of NPM version.
Please read more about this on [SiteSpeed test section](tests/sitespeed.md).

### sitespeed_iterations

This variable tells sitespeed based test(s) how many iterations it should do against the url to get the best measurement.
Please read more about this on [SiteSpeed test section](tests/sitespeed.md).

### cache_when_possible
Changing this to `True` will make webperf-core use local cache where available.
See other setting to determine how long.

### cache_time_delta
This tells webperf-core how long to use cached resources
See https://docs.python.org/3/library/datetime.html#timedelta-objects for possible values.
This take no effect unless `cache_when_possible` is set to `True`.

### software_use_stealth
Tell software test to use stealth mode or not, default is `True`
