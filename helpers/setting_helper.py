# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path

config = {}

config_mapping = {
    ("language", "general.language"): "string|general.language",
    ("useragent", "general.useragent", "USERAGENT"): "string|general.useragent",
    (
        "review",
        "general.review.show"): "bool|general.review.show",
    (
        "review-data",
        "general.review.data"): "bool|general.review.data",
    (
        "details",
        "general.review.details",
        "use_detailed_report",
        "USE_DETAILED_REPORT"): "bool|general.review.details",
    (
        "improve-only",
        "general.review.improve-only",
        "review_show_improvements_only",
        "REVIEW_SHOW_IMPROVEMENTS_ONLY"): "bool|general.review.improve-only",
    (
        "timeout",
        "general.request.timeout",
        "http_request_timeout",
        "HTTP_REQUEST_TIMEOUT"): "int|general.request.timeout",
    (
        "cache",
        "general.cache.use",
        "cache_when_possible",
        "CACHE_WHEN_POSSIBLE"): "bool|general.cache.use",
    (
        "cachetime",
        "general.cache.max-age",
        "CACHE_TIME_DELTA"
        ): "int|general.cache.max-age",
    (
        "dnsserver",
        "general.dns.address",
        "dns_server",
        "DNS_SERVER"): "string|general.dns.address",
    (
        "githubkey",
        "github.api.key",
        "github_api_key",
        "GITHUB_API_KEY"): "string|github.api.key",
    (
        "webbkollsleep",
        "tests.webbkoll.sleep",
        "webbkoll_sleep",
        "WEBBKOLL_SLEEP"): "int|tests.webbkoll.sleep",
    (
        "tests.w3c.group",
        "tests.css.group",
        "css_review_group_errors",
        "CSS_REVIEW_GROUP_ERRORS"): "bool|tests.css.group",
    (
        "browser",
        "tests.sitespeed.browser"): "string|tests.sitespeed.browser",
    (
        "sitespeeddocker",
        "tests.sitespeed.docker.use",
        "sitespeed_use_docker",
        "SITESPEED_USE_DOCKER"): "bool|tests.sitespeed.docker.use",
    (
        "mobile",
        "tests.sitespeed.mobile"): "bool|tests.sitespeed.mobile",
    (
        "sitespeedtimeout",
        "tests.sitespeed.timeout",
        "sitespeed_timeout",
        "SITESPEED_TIMEOUT"): "int|tests.sitespeed.timeout",
    (
        "sitespeediterations",
        "tests.sitespeed.iterations",
        "sitespeed_iterations",
        "SITESPEED_ITERATIONS"): "int|tests.sitespeed.iterations",
    (
        "sitespeedxvfb",
        "tests.sitespeed.xvfb"): "bool|tests.sitespeed.xvfb",
    (
        "sitespeedcustomcache",
        "general.cache.folder",
        "tests.sitespeed.cache.folder"): "string|general.cache.folder",
    (
        "csponly",
        "tests.http.csp-only",
        "csp_only",
        "CSP_ONLY"): "bool|tests.http.csp-only",
    (
        "csp-generate-hashes",
        "tests.http.csp-generate-hashes"): "bool|tests.http.csp-generate-hashes",
    (
        "csp-generate-strict-recommended-hashes",
        "tests.http.csp-generate-strict-recommended-hashes"): "bool|tests.http.csp-generate-strict-recommended-hashes",
    (
        "csp-generate-font-hashes",
        "tests.http.csp-generate-font-hashes"): "bool|tests.http.csp-generate-font-hashes",
    (
        "csp-generate-img-hashes",
        "tests.http.csp-generate-img-hashes"): "bool|tests.http.csp-generate-img-hashes",
    (
        "csp-generate-js-hashes",
        "tests.http.csp-generate-js-hashes"): "bool|tests.http.csp-generate-js-hashes",
    (
        "stealth",
        "tests.software.stealth.use",
        "software_use_stealth",
        "SOFTWARE_USE_STEALTH"): "bool|tests.software.stealth.use",
    (
        "advisorydatabase",
        "tests.software.advisory.path",
        "software_github_adadvisory_database_path",
        "SOFTWARE_GITHUB_ADADVISORY_DATABASE_PATH"
    ): "string|tests.software.advisory.path",
    (
        "mailport25",
        "tests.email.support.port25",
        "email_network_support_port25_traffic",
        "EMAIL_NETWORK_SUPPORT_PORT25_TRAFFIC"): "bool|tests.email.support.port25",
    (
        "mailipv6",
        "tests.email.support.ipv6",
        "email_network_support_ipv6_traffic",
        "EMAIL_NETWORK_SUPPORT_IPV6_TRAFFIC"): "bool|tests.email.support.ipv6",
    (
        "404url",
        "tests.page-not-found.override-url"): "bool|tests.page-not-found.override-url"
}


def get_config(name):
    """
    Retrieve a configuration value based on the specified name.

    Args:
        name (str): The name of the configuration setting.

    Returns:
        The configuration value if found, otherwise None.
    """

    if '.' not in name:
        # Try translate old settings name to new
        config_name = get_setting_name(name)
        if config_name is None:
            print(f'Warning: {name} uses old settings format and is not a known setting')
            return None

        config_name_pair = config_name.split('|')
        name = config_name_pair[1]

    # Lets see if we have it from terminal or in cache
    name = name.lower()
    if name in config:
        return config[name]

    # Try get config from our configuration file
    value = get_config_from_module(name, 'settings.json')
    if value is not None:
        config[name] = value
        return value

    # do we have fallback value we can use in our defaults/config.py file?
    value = get_config_from_module(name, f'defaults{os.path.sep}settings.json')
    if value is not None:
        config[name] = value
        return value

    return None

def update_config(name, value, module_name):
    """
    Updates the configuration for a specific module.

    This function takes a configuration name, its value, and the module name.
    It translates the old settings name to the new format if necessary,
    and updates the configuration for the specified module.

    Parameters:
    name (str): The name of the configuration setting.
                If the name is in the old format (i.e., does not contain a '.'),
                it will be translated to the new format.
    value (str): The new value for the configuration setting.
    module_name (str): The name of the module for which the configuration is being updated.
    """
    if '.' not in name:
        # Try translate old settings name to new
        config_name = get_setting_name(name)
        if config_name is None:
            print(f'Warning: {name} uses old settings format and is not a known setting')
            return

        config_name_pair = config_name.split('|')
        name = config_name_pair[1]

    name = name.lower()
    # Try set config for our configuration file
    update_config_for_module(name, value, module_name)

def set_runtime_config_only(name, value):
    """
    Set a configuration value.

    Args:
        name (str): The name of the configuration setting.
        value: The value to set for the specified configuration.
    """
    name = name.lower()
    config[name] = value

def set_config(module_name):
    """
    Sets the configuration for a given module.

    This function reads the global config variable, and writes a JSON file with the configuration
    specific to the provided module. The configuration is written to a file named after the module,
    located in the parent directory of this script.

    Args:
        module_name (str): The name of the module for which the configuration is to be set.

    Returns:
        None
    """
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    file_path = f'{base_directory}{os.path.sep}{module_name}'

    module_config = {}
    for config_name, config_value in config.items():
        config_path = config_name.split('.')
        config_path_length = len(config_path) - 1

        config_section = module_config
        config_section_index = 0
        for section_name in config_path:
            if section_name in config_section:
                tmp_config_section = config_section[section_name]
                if config_section_index == config_path_length:
                    config_section[section_name] = config_value
                config_section = tmp_config_section
            else:
                if config_section_index == config_path_length:
                    tmp_config_section = config_section[section_name] = config_value
                else:
                    tmp_config_section = config_section[section_name] = {}
                config_section = tmp_config_section
            config_section_index += 1

    with open(file_path, 'w', encoding='utf-8') as outfile:
        json.dump(module_config, outfile, indent=4)


def update_config_for_module(config_name, config_value, module_name):
    """
    Updates the configuration for a specific module in a JSON file.

    This function takes a configuration name, its value, and the module name.
    It reads the existing configuration from a JSON file,
    updates the specified configuration setting,
    and writes the updated configuration back to the file.

    Parameters:
    config_name (str): The name of the configuration setting.
                       The name should be in the format 'section.subsection.setting'.
    config_value (str): The new value for the configuration setting.
    module_name (str): The name of the module for which the configuration is being updated.
    """
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    file_path = f'{base_directory}{os.path.sep}{module_name}'
    if not os.path.isfile(file_path):
        return

    module_config = {}
    with open(file_path, encoding='utf-8') as json_file:
        module_config = json.load(json_file)

        config_path = config_name.split('.')
        config_section = module_config
        for section_name in config_path:
            if section_name in config_section:
                tmp_config_section = config_section[section_name]
                if not isinstance(tmp_config_section, dict):
                    config_section[section_name] = config_value
                    break
                config_section = tmp_config_section

    with open(file_path, 'w', encoding='utf-8') as outfile:
        json.dump(module_config, outfile, indent=4)

def get_config_from_module(config_name, module_name):
    """
    Retrieves the configuration value for a given name from the specified module file.
    
    Parameters:
    config_name (str): The name of the configuration value to retrieve.
    module_name (str): The name of the module the values should be retrieved from.

    Returns:
    The configuration value associated with the given config_name and module_name.
    """

    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    file_path = f'{base_directory}{os.path.sep}{module_name}'
    if not os.path.isfile(file_path):
        return None

    with open(file_path, encoding='utf-8') as json_file:
        module_config = json.load(json_file)

        config_path = config_name.split('.')
        config_section = module_config
        for section_name in config_path:
            if section_name in config_section:
                config_section = config_section[section_name]
                if not isinstance(config_section, dict):
                    return config_section
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

    config_name = get_setting_name(name)
    if config_name is None:
        return False

    config_name_pair = config_name.split('|')
    config_name_type = config_name_pair[0]
    config_name = config_name_pair[1]

    config_value = None
    value_type_handlers = {
        "bool": handle_cmd_bool_value,
        "int": handle_cmd_int_value,
        "string": handle_cmd_str_value,
    }
    for value_type, handler in value_type_handlers.items():
        if config_name_type in value_type:
            config_value = handler(config_name, value)
            set_runtime_config_only(config_name.lower(), config_value)
            return True
    return False

def get_setting_name(name):
    """
    Returns the setting name for a given alias.

    Parameters:
    name (str): The alias of the setting.

    Returns:
    str: The setting name if the alias is found, None otherwise.
    """
    config_name = None

    for aliases, setting_name in config_mapping.items():
        if name in aliases:
            config_name = setting_name
            break

    if config_name is None:
        return None
    return config_name


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

def get_used_configuration():
    """
    Returns a copy of the currently used configuration.

    This function retrieves the current configuration settings and returns a shallow copy
    of the configuration dictionary. The returned dictionary contains the same key-value pairs
    as the original configuration, allowing you to work with a snapshot of the configuration
    without modifying the original data.

    Returns:
        dict: A shallow copy of the configuration dictionary.
    """
    return config.copy()
