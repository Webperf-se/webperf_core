# -*- coding: utf-8 -*-

def append_domain_entry(domain, category, value, result):
    """
    Appends a value to a specific category within a domain in the given result dictionary.

    This function checks if the domain and category exist in the result dictionary. If not, 
    it creates them. It then checks if the value already exists within the category of the 
    domain. If it doesn't, the function appends the value.

    Parameters:
    domain (str): The domain to which the entry should be added.
    category (str): The category within the domain where the value should be added.
    value (str): The value to be added to the category within the domain.
    result (dict): The dictionary to which the domain, category, and value should be added.

    Returns:
    None: This function doesn't return anything; it modifies the result dictionary in-place.
    """
    if domain not in result:
        result[domain] = {}

    if category not in result[domain]:
        result[domain][category] = []

    if value not in result[domain][category]:
        result[domain][category].append(value)

def has_domain_entry(domain, category, value, result):
    """
    Checks if a specific value exists in a category within a domain in the given result dictionary.

    This function checks if the domain and category exist in the result dictionary. If not, 
    it returns False. It then checks if the value exists within the category of the domain. 
    If it doesn't, the function returns False. If all checks pass, the function returns True.

    Parameters:
    domain (str): The domain to be checked.
    category (str): The category within the domain to be checked.
    value (str): The value to be checked within the category of the domain.
    result (dict): The dictionary in which the domain, category, and value should be checked.

    Returns:
    bool: True if the value exists within the category of the domain in the result dictionary,
          False otherwise.
    """
    if domain not in result:
        return False

    if category not in result[domain]:
        return False

    if value not in result[domain][category]:
        return False

    return True
