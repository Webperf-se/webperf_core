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

def main(argv):
    """
    Release new version IF there is anything to release
    """
    try:
        opts, _ = getopt.getopt(argv, "hl:u:t:", [
                                   "help", "last=", "update="])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if len(opts) == 0:
        print(main.__doc__)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):  # help
            print(main.__doc__)
            sys.exit(0)
        elif opt in ("-l", "--last"):
            last_version = packaging.version.Version(arg)
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

        elif opt in ("-u", "--update"):
            last_version = packaging.version.Version(arg)
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


    # No match for command so return error code to fail verification
    sys.exit(0)


if __name__ == '__main__':
    main(sys.argv[1:])
