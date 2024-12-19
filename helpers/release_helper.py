import json
import os
import getopt
from pathlib import Path
import sys
from datetime import datetime
import packaging.version

def get_new_version(last_version):
    """
    Generates a new version number based on the current date and the last version number.

    Args:
        last_version (packaging.version.Version): The last version number.

    Returns:
        packaging.version.Version: The new version number.
    """
    print('last_version', last_version)
    new_version = packaging.version.Version(f"{datetime.now().year}.{datetime.now().month}.0")
    if new_version <= last_version:
        if last_version.major != new_version.major:
            print('major new_version', new_version)
            return new_version
        if last_version.minor != new_version.minor:
            print('minor new_version', new_version)
            return new_version

        new_version = packaging.version.Version(
            f"{new_version.major}.{new_version.minor}.{(last_version.micro + 1)}")

        print('micro new_version', new_version)
    else:
        print('new_version', new_version)
    return new_version

def set_new_release_version_in_env(argv):
    last_version = packaging.version.Version(argv)
    new_version= get_new_version(last_version)

    current_version = None
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent
    with open(
                f'{base_directory}{os.path.sep}package.json',
                encoding='utf-8'
            ) as json_input_file:
        package_info = json.load(json_input_file)
        if 'version' in package_info:
            current_version = packaging.version.Version(package_info['version'])

    if current_version != new_version:
        print((
            'last and current version(s) do not match'
            f'new version={new_version}',
            f'package.json version={current_version}'
            ))
        return

    env_file = os.getenv('GITHUB_ENV')
    with open(env_file, "a", encoding="utf-8") as myfile:
        myfile.write(f"NEW_VERSION={new_version}")

def update_package_lock_json():
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent
    with open(
                f'{base_directory}{os.path.sep}package-lock.json',
                encoding='utf-8'
            ) as json_input_file:
        package_info = json.load(json_input_file)
        if 'packages' not in package_info:
            print('packages object is missing')
            return False

        if 'node_modules/sitespeed.io/node_modules/chokidar' not in package_info['packages']:
            print('chokidar object is missing in packages')
            return True

        if 'optionalDependencies' not in package_info['packages']['node_modules/sitespeed.io/node_modules/chokidar']:
            print('optionalDependencies object is missing in node_modules/sitespeed.io/node_modules/chokidar')
            return True

        package_info['packages']['node_modules/sitespeed.io/node_modules/chokidar']['optionalDependencies'] = {}

        if 'node_modules/sitespeed.io/node_modules/fsevents' not in package_info['packages']:
            print('node_modules/sitespeed.io/node_modules/fsevents object is missing in packages')
            return True

        del package_info['packages']['node_modules/sitespeed.io/node_modules/fsevents']

    with open(
                f'{base_directory}{os.path.sep}package-lock.json',
                'w',
                encoding='utf-8'
            ) as json_output_file:
        json.dump(package_info, json_output_file, indent=2)
    return True


def update_release_version(argv):
    last_version = packaging.version.Version(argv)
    package_info = None

    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent
    with open(
                f'{base_directory}{os.path.sep}package.json',
                encoding='utf-8'
            ) as json_input_file:
        package_info = json.load(json_input_file)
        package_version = packaging.version.Version(package_info['version'])
        last_version = max(last_version, package_version)
        new_version= get_new_version(last_version)
        package_info['version'] = f'{new_version}'

    with open(
                f'{base_directory}{os.path.sep}package.json',
                'w',
                encoding='utf-8'
            ) as json_output_file:
        json.dump(package_info, json_output_file, indent=2)

    env_file = os.getenv('GITHUB_ENV')
    with open(env_file, "a", encoding="utf-8") as myfile:
        myfile.write(f"NEW_VERSION={new_version}")

