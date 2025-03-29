from helpers.setting_helper import get_config

def get_chromium_browser():
    browser = get_config('tests.sitespeed.browser')
    if browser in ('chrome', 'edge'):
        return browser
    return 'chrome'
