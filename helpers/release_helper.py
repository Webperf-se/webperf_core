import json
import os
import getopt
from pathlib import Path
import subprocess
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

        # Remove all development and optional dependencies
        print('Looks for npm packages with dev or optional dependencies to remove')
        for package_key, package in package_info['packages'].items():
            if 'devDependencies' in package:
                print('-', package_key, 'was using devDependencies')
                del package['devDependencies']
            if 'optionalDependencies' in package:
                print('-', package_key, 'was using optionalDependencies')
                del package['optionalDependencies']

        write_package_lock_json(base_directory, package_info)
        print('')

        # Remove unused packages
        print('Looks for npm packages we don\'t depend on')
        package_keys_to_remove = [] 
        for package_key, package in package_info['packages'].items():
            tmp_key = package_key
            test = True
            while test:
                node_modules_index = tmp_key.find('node_modules/')

                if node_modules_index != -1:
                    node_modules_index += len('node_modules/')
                    tmp_key = tmp_key[node_modules_index:]

                test = node_modules_index != -1
            # print(tmp_key)
            if tmp_key == '':
                continue
            if not is_package_used(tmp_key):
                print('-', tmp_key)
                # TODO: remove key from package-lock.json
                package_keys_to_remove.append(package_key)

    for key_to_remove in package_keys_to_remove:
        if key_to_remove in package_info['packages']:
            del package_info['packages'][key_to_remove]
            write_package_lock_json(base_directory, package_info)

    write_package_lock_json(base_directory, package_info)
    return True

def write_package_lock_json(base_directory, package_info):
    with open(
                f'{base_directory}{os.path.sep}package-lock.json',
                'w',
                encoding='utf-8'
            ) as json_output_file:
        json.dump(package_info, json_output_file, indent=2)

def is_package_used(package_name):
    info = get_package_info(package_name)
    if info == None:
        return False
    if 'dependencies' not in info:
        return False

    return True

def get_package_info(package_name):
    process = None
    timeout = 5
    process_failsafe_timeout = timeout * 10
    try:
        if 'nt' in os.name:
            command = (f"npm.cmd ls {package_name} --json")
        else:
            command = (f"npm ls {package_name} --json")
        with subprocess.Popen(
            command.split(), stdout=subprocess.PIPE) as process:
            output, error = process.communicate(timeout=process_failsafe_timeout)

            if error is not None:
                print('DEBUG get_package_info(error)', error)

            json_result = json.loads(output)
            # nice = json.dumps(json_result, indent=3)
            # print(package_name, nice)
            return json_result

    except subprocess.TimeoutExpired:
        if process is not None:
            process.terminate()
            process.kill()
        print('TIMEOUT!')
        return None
    return None


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

