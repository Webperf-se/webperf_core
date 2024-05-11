# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import json
import os

def main(_):
    """
    WebPerf Core - Software update
    """

    collection = get_software_sources('software-unknown-sources.json')
    known_collection = get_software_sources('software-sources.json')

    names_to_remove = []
    for key in collection.keys():
        item = collection[key]

        if len(key) < 3:
            names_to_remove.append(key)
            continue

        if 'versions' not in item:
            names_to_remove.append(key)
            continue

        versions = item['versions']
        if 'unknown' in versions:
            del versions['unknown']

        if 'aliases' in known_collection and key in known_collection['aliases']:
            names_to_remove.append(key)

        if 'softwares' in known_collection and key in known_collection['softwares']:
            names_to_remove.append(key)

        # Change the below number to filter out how many versions should be minimum
        if len(item['versions'].keys()) < 2:
            names_to_remove.append(key)
            continue

    for key in names_to_remove:
        print(f'\t- {key}')
        if key in collection:
            del collection[key]

    set_softwares('software-unknown-sources-filtered.json', collection)


def set_softwares(filename, collection):
    """
    Writes a collection of software data to a JSON file.

    This function attempts to write a collection of
    software data to a JSON file in the 'data' directory or the base directory. 
    If the file is found, it writes the data to the file.
    If the file is not found, it prints an error message.

    Args:
        filename (str): The name of the JSON file to write to.
        collection (dict): The collection of software data to write.

    Returns:
        None
    """
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep)

    file_path = f'{base_directory}{os.path.sep}data{os.path.sep}{filename}'
    if not os.path.isfile(file_path):
        file_path = f'{base_directory}{os.path.sep}{filename}'
    if not os.path.isfile(file_path):
        print(f"ERROR: No {filename} file found!")

    print('set_software_sources', file_path)

    data = json.dumps(collection, indent=4)
    with open(file_path, 'w', encoding='utf-8', newline='') as file:
        file.write(data)

def get_software_sources(filename):
    """
    Loads and sorts software data from a JSON file.

    This function attempts to load a JSON file from a 'data' directory or the base directory. 
    If the file is found, it loads the JSON data into a dictionary, sorts it by software names, 
    and returns the sorted dictionary. If the file is not found, it returns an empty dictionary.

    Args:
        filename (str): The name of the JSON file to load.

    Returns:
        dict: A dictionary containing the sorted software data,
        or an empty dictionary if the file was not found.
    """
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep)

    file_path = f'{base_directory}{os.path.sep}data{os.path.sep}{filename}'
    if not os.path.isfile(file_path):
        file_path = f'{base_directory}{os.path.sep}{filename}'
    if not os.path.isfile(file_path):
        print(f"ERROR: No {filename} file found!")
        return {
        }

    print('get_software_sources', file_path)
    collection = {}
    with open(file_path, encoding='utf-8') as json_file:
        collection = json.load(json_file)

    # sort on software names
    if len(collection.keys())> 0:
        tmp = {}
        issue_keys = list(collection.keys())
        issue_keys_sorted = sorted(issue_keys, reverse=False)

        for key in issue_keys_sorted:
            tmp[key] = collection[key]

        collection = tmp

    return collection


if __name__ == '__main__':
    main(sys.argv[1:])
