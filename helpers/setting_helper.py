config = {}

def get_config(name):
    """
    Retrieves the configuration value for a given name from the configuration file.
    If the name does not exist in the configuration file,
    it attempts to retrieve it from the defaults/config.py file.
    
    Parameters:
    name (str): The name of the configuration value to retrieve.

    Returns:
    The configuration value associated with the given name.

    Raises:
    ValueError: If the name does not exist in both the configuration file and
    the defaults/config.py file.

    Notes:
    - If the name exists in the defaults/config.py file but not in the configuration file,
      a warning message is printed.
    - If the name does not exist in both files,
      a fatal error message is printed and a ValueError is raised.
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
    name = name.lower()
    print('set config', name, '=', value)
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
