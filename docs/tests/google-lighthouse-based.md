# Google Lighthouse based Tests
[![Regression Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-google-lighthouse-based.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-google-lighthouse-based.yml)

* [Google Lighthouse accessibility with Axe](google-lighthouse-based.md)
* [Google Lighthouse performance](google-lighthouse-based.md)
* [Google Lighthouse best practice](google-lighthouse-based.md)
* [Google Lighthouse progressive web apps](google-lighthouse-based.md)
* [Google Lighthouse SEO](google-lighthouse-based.md)
* [Energy efficiency](google-lighthouse-based.md)



Another thing you need to do is to open the *config.py* file and change one thing. The line that looks like the following is incomplete:  
*googlePageSpeedApiKey = “”*  
Between the quotation marks, enter your Google Pagespeed API key. See the following header for how to do this.

### Google Lighthouse API key
Google Lighthouse API requires an API key. You can get one like this:
1. Go to [Google Cloud Platform](https://console.cloud.google.com/apis).
2. Search for *Pagespeed Insights API*.
3. Click the button labelled *Manage*.
4. Click on *Credentials* (you may need to create a project first, if you do not already have one).
5. Click *+ Create Credentials*, then *API key*
6. In the dialogue box the key now appears below *Your API key*, it can look like this *AIzaXyCjEXTvAq7zAU_RV_vA7slvDO9p1weRfgW*

That code is your API key, that you should put in the *config.py* file in the source code, between the quotation marks on the line where you find *googlePageSpeedApiKey*.