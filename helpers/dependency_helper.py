import json
import os
import getopt
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime
import packaging.version

from helpers.setting_helper import get_config
from helpers.browser_helper import get_chromium_browser

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
    if result is None:
        print('\t- Python:', 'ERROR: Unknown return')
        return

    version = None
    regex = r"Python (?P<major>[0-9]+)\.(?P<minor>[0-9]+)"
    matches = re.finditer(regex, result, re.MULTILINE)
    for _, match in enumerate(matches, start=1):
        version = packaging.version.Version(f"{match.group('major')}.{match.group('minor')}")

    if version is None:
        print('\t- Python:', 'ERROR: Unable to get version')
        return

    # Define acceptable versions, only considering major and minor
    acceptable_versions = {packaging.version.Version('3.10'), packaging.version.Version('3.11'), 
                           packaging.version.Version('3.12'), packaging.version.Version('3.13')}

    if version not in acceptable_versions:
        print('\t- Python:', 'WARNING: version not in supported range (3.10-3.13)')
        return

    print('\t- Python:', 'OK')

def check_node():
    result, error = test_cmd('node -v')
    if result is None:
        print('\t- Node:', 'ERROR: Unknown return')
        return

    version = None
    regex = r"v(?P<version>[0-9\.]+)"
    matches = re.finditer(regex, result, re.MULTILINE)
    for _, match in enumerate(matches, start=1):
        version = match.group('version')

    if version is None:
        print('\t- Node:', 'ERROR: Unable to get version')
        return

    version = packaging.version.Version(version)
    repo_version = packaging.version.Version("20.17")

    # Check if the major version is between 20 and 24
    if not (20 <= version.major <= 24):
        print('\t- Node:', 'WARNING: Major version not between 20 and 22')
        return

    # Check if the minor version is at least as high as the repository's minor version
    if version.major == repo_version.major and version.minor < repo_version.minor:
        print('\t- Node:', 'WARNING: Minor version is below required')
        return

    print('\t- Node:', 'OK')

def check_requirements():
    requirements_content = None
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent
    webperf_dir = base_directory.resolve()
    requirements_path = os.path.join(webperf_dir, 'requirements.txt')

    if not os.path.exists(requirements_path):
        print('\t- PIP Requirements:', 'Unable to find requirements.txt')
        return

    with open(requirements_path, 'r', encoding='utf-8', newline='') as requirements_file:
        requirements_content = '\r\n'.join(requirements_file.readlines())

    requirements_dependencies = {}
    regex = r"^(?P<name>[a-zA-Z0-9\-]+)[=]+(?P<version>[0-9\.\_]+)"
    matches = re.finditer(
        regex, requirements_content, re.MULTILINE)
    for _, match in enumerate(matches, start=1):
        dependency_name = match.group('name').lower()
        dependency_version = match.group('version')
        requirements_dependencies[dependency_name] = dependency_version

    result, error = test_cmd('pip list')
    # if python_error is not None or python_error != b'':
    #     print('\t- Python:', 'ERROR:', python_error)
    #     return
    if result is None:
        print('\t- PIP Requirements:', 'ERROR: Unknown return')
        return

    installed_dependencies = {}
    regex = r"(?P<name>[a-zA-Z0-9\-]+)[ ]+(?P<version>[0-9\.\_]+)"
    matches = re.finditer(
        regex, result.replace('\\n', '\n').replace('\\r', '\r'), re.MULTILINE)
    for _, match in enumerate(matches, start=1):
        dependency_name = match.group('name').lower()
        dependency_version = match.group('version')
        installed_dependencies[dependency_name] = dependency_version

    print('\t- PIP Requirements:')
    for dependency_name, dependency_version in requirements_dependencies.items():
        if dependency_name not in installed_dependencies:
            print(f'\t\t- {dependency_name}:', 'ERROR: Not found')
            continue

        dependency_installed_version = installed_dependencies[dependency_name]
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

        print(
            f"\t\t- {dependency_name}: OK")

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
                if dependency_name == 'vnu-jar':
                    vnu_jar_path = os.path.join(
                        webperf_dir,
                        'node_modules',
                        dependency_name,
                        'build',
                        'dist',
                        'vnu.jar')
                    if os.path.exists(vnu_jar_path):
                        try:
                            import zipfile
                            archive = zipfile.ZipFile(vnu_jar_path, 'r')
                            manifest_content = archive.read('META-INF/MANIFEST.MF').decode()
                            if f'Implementation-Version: {dependency_version}' in manifest_content:
                                print(f"\t\t- {dependency_name}: OK")
                                continue
                        except Exception as ex:
                             print('ERROR', ex)
                             _ = 1
                        print(f"\t\t- {dependency_name}: Unknown version")
                        continue

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

def check_chromium():
    return check_browser(get_chromium_browser())

def check_firefox():
    return check_browser('firefox')

def check_browser(browser):
    sitespeed_iterations = 1
    sitespeed_arg = (
        '--plugins.remove screenshot '
        '--plugins.remove html '
        '--plugins.remove metrics '
        '--browsertime.screenshot false '
        '--screenshot false '
        '--screenshotLCP false '
        '--browsertime.screenshotLCP false '
        '--videoParams.createFilmstrip false '
        '--visualMetrics false '
        '--visualMetricsPerceptual false '
        '--visualMetricsContentful false '
        '--browsertime.headless true '
        # '--silent true '
        f'--utc true -n {sitespeed_iterations}')

    if 'firefox' in browser:
        sitespeed_arg = (
            '-b firefox '
            '--firefox.includeResponseBodies all '
            '--firefox.preference privacy.trackingprotection.enabled:false '
            '--firefox.preference privacy.donottrackheader.enabled:false '
            '--firefox.preference browser.safebrowsing.malware.enabled:false '
            '--firefox.preference browser.safebrowsing.phishing.enabled:false '
            f'{sitespeed_arg}')
    elif browser in ('chrome', 'edge'):
        sitespeed_arg = (
            f'-b {browser} '
            '--chrome.cdp.performance false '
            '--browsertime.chrome.timeline false '
            '--browsertime.chrome.includeResponseBodies all '
            '--browsertime.chrome.args ignore-certificate-errors '
            f'{sitespeed_arg}')

    sitespeed_arg = f'--shm-size=1g {sitespeed_arg}'

    if get_config('tests.sitespeed.xvfb'):
        sitespeed_arg += ' --xvfb'

    sitespeed_arg += ' https://webperf.se'

    command = (f"node node_modules{os.path.sep}sitespeed.io{os.path.sep}"
        f"bin{os.path.sep}sitespeed.js {sitespeed_arg}")

    result, error = test_cmd(command)

    if len(error) > 0:
        print(f'\t- {browser}:', 'ERROR: Exited with errors')
        print(f'\t\tSiteSpeed Arguments: {sitespeed_arg}')
        print(f'\t\tError Message: {error}')
        return

    if result is None:
        print(f'\t- {browser}:', 'ERROR: Exited with no result')
        return

    if 'Versions OS' not in result:
        print(f'\t- {browser}:', 'ERROR: Invalid result')
        return

    print(f'\t- {browser}:', 'OK')

def dependency():
    # TODO: Check webperf_core version
    check_python()
    check_requirements()
    check_node()
    check_package()
    check_chromium()
    check_firefox()
    # TODO: Check data files dependencies
    # TODO: Check Internet access (for required sources like MDN Web Reference)
