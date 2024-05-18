config = {}

config_mapping = {
    ("useragent", "general.useragent", "agent", "ua"): "string|USERAGENT",
    (
        "details",
        "general.review.details",
        "use_detailed_report"): "bool|USE_DETAILED_REPORT",
    (
        "improve-only",
        "general.review.improve-only",
        "review_show_improvements_only"): "bool|REVIEW_SHOW_IMPROVEMENTS_ONLY",
    (
        "timeout",
        "general.request.timeout",
        "http_request_timeout"): "int|HTTP_REQUEST_TIMEOUT",
    (
        "cache",
        "general.cache.use",
        "cache_when_possible"): "bool|CACHE_WHEN_POSSIBLE",
    (
        "cachetime",
        "general.cache.time",
        "cache_time_delta"): "int|CACHE_TIME_DELTA",
    (
        "dnsserver",
        "general.dns.address",
        "dns_server"): "string|DNS_SERVER",
    (
        "githubkey",
        "github.api.key",
        "github_api_key"): "string|GITHUB_API_KEY",
    (
        "googleapikey",
        "tests.lighthouse.api.key",
        "googlepagespeedapikey"): "string|GOOGLEPAGESPEEDAPIKEY",
    (
        "googleuseapi",
        "tests.lighthouse.api.use",
        "lighthouse_use_api"): "bool|LIGHTHOUSE_USE_API",
    (
        "webbkollsleep",
        "tests.webbkoll.sleep",
        "webbkoll_sleep"): "int|WEBBKOLL_SLEEP",
    (
        "tests.w3c.group",
        "tests.css.group",
        "css_review_group_errors"): "bool|CSS_REVIEW_GROUP_ERRORS",
    (
        "yellowlabtoolskey",
        "tests.ylt.api.key",
        "ylt_use_api"): "bool|YLT_USE_API",
    (
        "yellowlabtoolsaddress",
        "tests.ylt.api.address",
        "ylt_server_address"): "string|YLT_SERVER_ADDRESS",
    (
        "sitespeeddocker",
        "tests.sitespeed.docker.use",
        "sitespeed_use_docker"): "bool|SITESPEED_USE_DOCKER",
    (
        "sitespeedtimeout",
        "tests.sitespeed.timeout",
        "sitespeed_timeout"): "int|SITESPEED_TIMEOUT",
    (
        "sitespeediterations",
        "tests.sitespeed.iterations",
        "sitespeed_iterations"): "int|SITESPEED_ITERATIONS",
    (
        "csponly",
        "tests.http.csp-only",
        "csp_only"): "bool|CSP_ONLY",
    (
        "stealth",
        "tests.software.stealth.use",
        "software_use_stealth"): "bool|SOFTWARE_USE_STEALTH",
    (
        "advisorydatabase",
        "tests.software.advisory.path",
        "software_github_adadvisory_database_path"
    ): "string|SOFTWARE_GITHUB_ADADVISORY_DATABASE_PATH",
    (
        "browser",
        "tests.software.browser",
        "software_browser"): "string|SOFTWARE_BROWSER",
    (
        "mailport25",
        "tests.email.support.port25",
        "email_network_support_port25_traffic"): "bool|EMAIL_NETWORK_SUPPORT_PORT25_TRAFFIC",
    (
        "mailipv6",
        "tests.email.support.ipv6",
        "email_network_support_ipv6_traffic"): "bool|EMAIL_NETWORK_SUPPORT_IPV6_TRAFFIC"
}


def get_config(name):
    """
    Retrieve a configuration value based on the specified name.

    Args:
        name (str): The name of the configuration setting.

    Returns:
        The configuration value if found, otherwise None.
    """
    # Lets see if we have it from terminal or in cache
    name = name.lower()
    if name in config:
        return config[name]

    # Try get config from our configuration file
    value = get_config_from_module(name, 'config')
    if value is not None:
        config[name] = value
        return value

    name = name.upper()
    value = get_config_from_module(name, 'config')
    if value is not None:
        config[name] = value
        return value

    # do we have fallback value we can use in our defaults/config.py file?
    value = get_config_from_module(name, 'defaults.config')
    if value is not None:
        config[name] = value
        return value

    return None

def set_config(name, value):
    """
    Set a configuration value.

    Args:
        name (str): The name of the configuration setting.
        value: The value to set for the specified configuration.
    """
    name = name.lower()
    config[name] = value

def get_config_from_module(config_name, module_name):
    """
    Retrieves the configuration value for a given name from the specified module file.
    
    Parameters:
    config_name (str): The name of the configuration value to retrieve.
    module_name (str): The name of the module the values should be retrieved from.

    Returns:
    The configuration value associated with the given config_name and module_name.
    """
    # do we have fallback value we can use in our defaults/config.py file?
    try:
        from importlib import import_module # pylint: disable=import-outside-toplevel
        tmp_config = import_module(module_name) # pylint: disable=invalid-name
        if hasattr(tmp_config, config_name):
            return getattr(tmp_config, config_name)
    except ModuleNotFoundError:
        _ = 1

    return None

def set_config_from_cmd(arg):
    """
    Set configuration settings based on user input.

    Parses the input argument to determine the setting name and value.
    If the input is not in the correct format, it displays available settings.
    Otherwise, it sets the specified configuration value.

    Args:
        arg (str): Input argument in the format "<setting_name>=<value>".
    """
    pair = arg.split('=')
    nof_pair = len(pair)
    if nof_pair > 2:
        return False
    name = pair[0].lower()
    value = 'true'

    if nof_pair > 1:
        value = pair[1]

    config_name = None

    for aliases, setting_name in config_mapping.items():
        if name in aliases:
            config_name = setting_name
            break

    if config_name is None:
        return False

    config_name_pair = config_name.split('|')
    config_name_type = config_name_pair[0]
    config_name = config_name_pair[1]

    config_value = None
    value_type_handlers = {
        "bool": handle_cmd_bool_value,
        "int": handle_cmd_int_value,
        "str": handle_cmd_str_value,
    }
    for value_type, handler in value_type_handlers.items():
        if config_name_type in value_type:
            config_value = handler(config_name, value)
            set_config(config_name.lower(), config_value)
            return True
    return False


def handle_cmd_bool_value(setting_name, value):
    """
    Converts a string value to a boolean based on common true/false representations.

    Args:
        setting_name (str): The name of the setting.
        value (str): The input value to be converted.

    Returns:
        bool or None: The converted boolean value if valid, otherwise None.
    """
    setting_value = None
    if value in ('true', 'True', 'yes', 'Y', 'y'):
        setting_value = True
    elif value in ('false', 'False', 'no', 'N', 'n'):
        setting_value = False
    else:
        print(
            'Warning: Ignoring setting,'
            f'"{setting_name}":s value has to be true or false.')
    return setting_value

def handle_cmd_int_value(setting_name, value):
    """
    Converts a string value to an integer.

    Args:
        setting_name (str): The name of the setting.
        value (str): The input value to be converted.

    Returns:
        int or None: The converted integer value if valid, otherwise None.
    """
    setting_value = None
    try:
        setting_value = int(value)
    except TypeError:
        print(f'Warning: Ignoring setting, "{setting_name}":s value has to be a number.')
    return setting_value

def handle_cmd_str_value(_, value):
    """
    Returns the input string value without any modification.

    Args:
        _ (Any): Placeholder for an unused argument.
        value (str): The input string value.

    Returns:
        str: The original input string value.
    """
    return value
