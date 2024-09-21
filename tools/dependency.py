import json
import os
import getopt
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime
import packaging.version

def test_cmd(command):
    process_failsafe_timeout = 600
    process = None
    result = None
    try:
        with subprocess.Popen(
            command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            output, error = process.communicate(timeout=process_failsafe_timeout)
            if output is not None:
                result = str(output)
            if error is not None and error != b'':
                error = str(error)
            return result, error
        return result
    except FileNotFoundError:
        if process is not None:
            process.terminate()
            process.kill()
        return result, 'Not found.'

def check_python():
    result, error = test_cmd('python -V')
    # if python_error is not None or python_error != b'':
    #     print('\t- Python:', 'ERROR:', python_error)
    #     return
    if result is None:
        print('\t- Python:', 'ERROR: Unknown return')
        return

    version = None
    regex = r"Python (?P<version>[0-9\.]+)"
    matches = re.finditer(
        regex, result, re.MULTILINE)
    for _, match in enumerate(matches, start=1):
        version = match.group('version')

    if version is None:
        print('\t- Python:', 'ERROR: Unable to get version')
        return

    version = packaging.version.Version(version)
    repo_version = packaging.version.Version("3.12")
    if version.major is not repo_version.major:
        print('\t- Python:', 'WARNING: wrong major version')
        return

    if version.minor is not repo_version.minor:
        print('\t- Python:', 'WARNING: wrong minor version')
        return

    print('\t- Python:', 'OK')

def check_java():
    _, result = test_cmd('java -version')

    version = None
    regex = r"java version \"(?P<version>[0-9\.\_]+)\""
    matches = re.finditer(
        regex, result, re.MULTILINE)
    for _, match in enumerate(matches, start=1):
        version = match.group('version')

    if version is None:
        print('\t- Java:', 'ERROR: Unable to get version')
        return

    # TODO: Check java version

    print('\t- Java:', 'OK')

def check_node():
    result, error = test_cmd('node -v')
    # if python_error is not None or python_error != b'':
    #     print('\t- Python:', 'ERROR:', python_error)
    #     return
    if result is None:
        print('\t- Node:', 'ERROR: Unknown return')
        return

    version = None
    regex = r"v(?P<version>[0-9\.]+)"
    matches = re.finditer(
        regex, result, re.MULTILINE)
    for _, match in enumerate(matches, start=1):
        version = match.group('version')

    if version is None:
        print('\t- Node:', 'ERROR: Unable to get version')
        return

    version = packaging.version.Version(version)
    repo_version = packaging.version.Version("20.17")
    if version.major is not repo_version.major:
        print('\t- Node:', 'WARNING: wrong major version')
        return

    if version.minor < repo_version.minor:
        print('\t- Node:', 'WARNING: wrong minor version')
        return

    print('\t- Node:', 'OK')


def check_package():
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent
    webperf_dir = base_directory.resolve()

    with open(os.path.join(webperf_dir, 'package.json'), encoding='utf-8') as json_input_file:
        package_info = json.load(json_input_file)

        if 'dependencies' in package_info:
            for dependency_name, dependency_version in package_info['dependencies'].items():
                base_directory = Path(os.path.dirname(
                    os.path.realpath(__file__)) + os.path.sep).parent
                webperf_dir = base_directory.resolve()
                dependency_package_path = os.path.join(
                    webperf_dir,
                    'node_modules',
                    dependency_name,
                    'package.json')
                if not os.path.exists(dependency_package_path):
                    print(f"\t\t- {dependency_name} v{dependency_version}: Not found")
                    continue

                with open(dependency_package_path, encoding='utf-8') as dependency_json_input_file:
                    dependency_package_info = json.load(dependency_json_input_file)
                    if 'version' not in dependency_package_info:
                        print((
                            f"\t\t- {dependency_name} "
                            f"v{dependency_version}: Invalid package.json format"))
                        continue

                    dependency_installed_version = dependency_package_info['version']
                    if dependency_version != dependency_installed_version:
                        dependency_version = packaging.version.Version(dependency_version)
                        dependency_installed_version = packaging.version.Version(
                            dependency_installed_version)
                        if dependency_version.major is not dependency_installed_version.major:
                            print(
                                f'\t\t- {dependency_name}:',
                                'WARNING: wrong major version (',
                                dependency_version,
                                'vs',
                                dependency_installed_version, ')')
                            continue

                        if dependency_version.minor is not dependency_installed_version.minor:
                            print(
                                f'\t\t- {dependency_name}:',
                                'WARNING: wrong minor version (',
                                dependency_version,
                                'vs',
                                dependency_installed_version, ')')
                            continue

                        if dependency_version.micro is not dependency_installed_version.micro:
                            print(
                                f'\t\t- {dependency_name}:',
                                'WARNING: wrong micro version (',
                                dependency_version,
                                'vs',
                                dependency_installed_version, ')')
                            continue

                        print(
                            f"\t\t- {dependency_name}: Wrong version used (",
                            dependency_version,
                            'vs',
                            dependency_installed_version, ')')
                        continue

                print(f"\t\t- {dependency_name}: OK")





def main(argv):
    """
    Verifies required dependencies for webperf-core
    """
    try:
        opts, _ = getopt.getopt(argv, "hl:u:t:", [
                                   "help", "last=", "update="])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)


    for opt, arg in opts:
        if opt in ('-h', '--help'):  # help
            print(main.__doc__)
            sys.exit(0)

    if len(opts) == 0:
        print(main.__doc__)
        # TODO: Check webperf_core version
        check_python()
        # TODO: Check requirement.txt dependencies
        check_node()
        check_package()
        check_java()
        # TODO: Check Chrome dependency
        # TODO: Check Firefox dependency
        # TODO: Check data files dependencies
        # TODO: Check Internet access (for required sources like MDN Web Reference)


    # No match for command so return error code to fail verification
    sys.exit(0)


if __name__ == '__main__':
    main(sys.argv[1:])
