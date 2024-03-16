# Contributing Guidelines
Welcome to our open-source project! We appreciate your interest in contributing. Before you get started, please take a moment to read through these guidelines to ensure a smooth and productive collaboration.

## Table of Contents
- Getting Started
- Submitting Issues
- Creating Pull Requests
- Code of Conduct
- License
- Contact



## Getting Started
- Fork this repository and clone it to your local machine.
- Install any necessary dependencies, you can read more about it in the [Getting Started on Local machine.](getting-started-local.md)
- Familiarize yourself with the project structure and coding conventions.

## Submitting Issues

### Bug Reports:
If you encounter a bug, please follow these steps to create an informative bug report:

1) **Check Existing Issues:** Before opening a new issue, search the existing issues to see if someone else has already reported the same problem.
2) **Describe the Issue:** Create a new issue with a clear description of the problem. Include the following details:
- **Summary:** A concise summary of the issue.
- **Steps to Reproduce:** Detailed steps to reproduce the bug.
- **Expected Behavior:** What you expected to happen.
- **Actual Behavior:** What actually happened (including any error messages or exceptions).
- **Environment Details:** Information about your operating system, browser, and any relevant software versions.
3) **Include** `failures.log`: If the bug is related to an error or exception, attach the `failures.log` file (if available). This log can provide valuable insights for debugging.

Remember that clear and detailed bug reports help maintainers understand and address the issue more effectively. Thank you for contributing to our project! 🙌

### Feature Requests:
If you have an idea for a new feature or enhancement, open an issue to discuss it.

### Questions and Discussions:
Feel free to ask questions or start discussions related to the project. We also have a [Slack channel](https://webperf.se/articles/webperf-pa-slack/)

## Creating Pull Requests
- **Branches:** Create a new branch for your work (e.g., feature/my-new-feature).
- **Commits:** Make concise, well-documented commits. Use descriptive commit messages.
- **Tests:** Ensure that your changes are covered by tests.
- **Documentation:** Update relevant documentation if needed.
- **Review Process:** Your pull request will be reviewed by maintainers. Be responsive to feedback.

## Code of Conduct
We expect all contributors to follow our Code of Conduct. Treat others with respect and kindness.

## License
What you are allowed to do with this code / repo.
The license used is the [MIT license](https://en.wikipedia.org/wiki/MIT_License). This means that you can do whatever you want with the source code, including using it in commercial software and contexts. However, there is no guarantee or liability for the code.

## Contact
[Slack channel](https://webperf.se/articles/webperf-pa-slack/)




## Translations

### Want to add another language? 

The multiple language support is built on `gettext` in Python.

#### How to support new language
You could either follow the more technical suggestions below, or you perhaps would like an application such as [Poedit](https://poedit.net) (available on Macos, Linux and Windows).

To create a new language source file:  
```python3 <your path to pygettext.py > -d webperf-core -o locales/webperf-core.pot default.py checks.py```
(or copy an existing one)

Copy the file to your locale, for Swedish it would be:  
```locales/sv/LC_MESSAGES/webperf-core.pot```

Rename the file extension from `.pot` to `.po`

After you have translated everything you should check it in, GitHub will take your change and generate .mo files when needed.
You now have support for a new language, please send it to the official repository using a pull request :)

#### How to find pygettext.py

Locate your pygettext.py file:  
```locate pygettext.py```

It might be as follows:  
```/Library/Frameworks/Python.framework/Versions/3.8/share/doc/python3.8/examples/Tools/i18n/pygettext.py```

### References

- https://phrase.com/blog/posts/translate-python-gnu-gettext/
- https://docs.python.org/3/library/gettext.html

