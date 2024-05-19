# Why settings.json and what does it do?

With your own `settings.json` file you are able to use the same settings
every time you run webperf core, unlike using `--settings` that only affect current run.

# Why copy and rename defaults/config.py?

You *ONLY* need to copy defaults/settings.json IF you want to permanently change any settings.
Most people can use the default settings and only use `--settings` for when temporarly changing settings.
You should not change settings directly in defaults/config.py,
the reason for this is because if you download a new version of the code, your settings or data should not be overwritten by accident.

Because of this you need to copy `defaults/settings.json` and name the new version `settings.json` and place it in root folder.
Best practise is to only keep settings you want to activaly change in your `settings.json` file,
this way you will use default settings for everything else and when/if they change it is changes for you as well.

If you for example want to permanently change to activate details your own `settings.json` should look like:

```json
{
    "general": {
        "review": {
            "details": false,
        }
    }
}
```

# What do every configuration do?



## general
This section indicate the settings affects many test.

### general.dns.address `(Default = 8.8.8.8)`

Address to nameserver used for DNS lookups.
Good if you for example have your own nameserver internally.

### general.request.timeout `(Default = 60)`

This variable is used as request timeout where a single request is only needed and not a full browser simulation.
Example in the following tests:

- 404 (Page Not Found, used against your website)
- Users’ integrity test against Webbkoll (used against service)
- Standard Files (used against your website)
- HTTP Test (used against your website)

### general.review.details `(Default = false)`

Setting this variable to true will result showing a more detailed review when available.
It is for example used in software test to show exactly what CVE and software you got less points to.
This is good todo when it is time to actually fix some of the issues and not only track where you are.

### general.review.improve-only `(Default = true)`

Setting this variable to false will result in showing all reviews (not only review that points to possible improvements).
This is good if you want to look back on much you have improved over time.

### general.useragent `(Default = latest Firefox on Ubuntu)`

This variable is used as user agent where a single request is only needed and not a full browser simulation.
Example in the following tests:

- 404 (Page Not Found, used against your website)
- Standard Files (used against your website)
- HTTP Test (used against your website)

### general.cache.use `(Default = false)`
Changing this to `true` will make webperf-core use local cache where available.
This is perfect if you run more test as many tests can reuse data from previous test
resulting in less requests and strain on the url you are testing.

See `general.cache.max-age` setting to determine how long.

### general.cache.max-age `(Default = 60 minutes)`
This tells webperf-core how long to use cached resources in minutes.
This take no effect unless `general.cache.use` is set to `true`.




## github

Section for github specific settings.

### github.api.key `(Default = "")`

Only required if you use GitHub Actions, it is required for workflows to be allowed to change content and create pull request.



## tests

Section for test specific settings.

### tests.email.support.port25 `(Default = false)`

Tells email test if it should do a operation email test (most consumer ISP don't allow this)

### tests.email.support.ipv6 `(Default = false)`

Tells email test if it should do a operation over ipv6 also in email test (GitHub Actions doesn't support it).

### tests.http.csp-only `(Default = false)`

Tells HTTP test to ignore everything except the CSP subtest in the HTTP test (great if you run it against sitemap to get CSP recommendation)

### tests.sitespeed.docker.use `(Default = false)`

This variable tells sitespeed based test(s) to use docker image version instead of NPM version.
Please read more about this on [SiteSpeed test section](tests/sitespeed.md).

### tests.sitespeed.timeout `(Default = 300 ms)`

This variable tells sitespeed based test(s) how long it should wait for a url to load.
Setting this to a lower value may improve overall test speed if many urls are being tested and
it is not important if one or two tests fail.
Please read more about this on [SiteSpeed test section](tests/sitespeed.md).

### tests.sitespeed.iterations `(Default = 2)`

This variable tells sitespeed based test(s) how many iterations it should do against the url to get the best measurement.
Please read more about this on [SiteSpeed test section](tests/sitespeed.md).

### test.software.advisory.path `(Default = "")`
This variable is ONLY used to generate a CVE and security related info for software.
Tell software update tool the path to where you have repo of: https://github.com/github/advisory-database

### test.software.browser `(Default = "chrome")`
For now this is more or less useless for none developers.
In the future the goal is to make it possible to decide what browser to use when running tests.
Valid values are:
- chrome
- firefox
- edge

### test.software.stealth.use `(Default = true)`
Tell software test to use stealth mode or not.
Do *NOT* set this to `false` on urls you do not own, doing so might get you into legal issues or blocked.
The reason for this is that it might request resources not required for a visit
that someone might think is a hacking attempt.



### tests.webbkoll.sleep `(Default = 20 s)`

This variable is used as sleep time between checking status against service following tests:
- Users’ integrity test against Webbkoll (used against service).
