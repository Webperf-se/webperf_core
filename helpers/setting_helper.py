config = {}

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
