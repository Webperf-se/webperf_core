# Contributing Guidelines
Welcome to our open-source project! We appreciate your interest in contributing. Before you get started, please take a moment to read through these guidelines to ensure a smooth and productive collaboration.

## Table of Contents
- [Getting Started](#getting-started)
- [Translations](#translations)
- [Submitting Issues](#submitting-issues)
- [Creating Pull Requests](#creating-pull-requests)
- [Code of Conduct](#code-of-conduct)
- [License](#license)
- [Contact](#contact)



## Getting Started
- Fork this repository and clone it to your local machine.
- Install any necessary dependencies, you can read more about it in the [Getting Started on Local machine.](getting-started-local.md)
- Familiarize yourself with the project structure and coding conventions.

## Translations
### Want to add another language? 

The multiple language support is built on `gettext` in Python.

#### Change existing translation

For quick and easy changes we recommend doing it directly in your favorite browser, no coding knowledge needed or even a coding environment.

[read more on how to change texts here](translation.md)

#### How to support new language
You could either follow the more technical suggestions below, or you perhaps would like an application such as [Poedit](https://poedit.net) (available on Macos, Linux and Windows).

To create a new language source file: copy the english (en) one.
if this is the first test translated to the new language, copy all folders and files in the english (en) folder.

Copy the file to your locale, for Swedish it would be:  
```locales/sv/LC_MESSAGES/webperf-core.po```

After you have translated everything you should check it in, GitHub will take your change and generate .mo files when needed.
You now have support for a new language, please send it to the official repository using a pull request :)

### References

- https://phrase.com/blog/posts/translate-python-gnu-gettext/
- https://docs.python.org/3/library/gettext.html

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
- **big change or adding functionality**: Create Issue / Discuss in [Slack channel](https://webperf.se/articles/webperf-pa-slack/) before starting.
- **Branches:** Create a new branch for your work (e.g., feature/my-new-feature).
- **Commits:** Make concise, well-documented commits. Use descriptive commit messages.
- **Tests:** Ensure that your changes are covered by tests.
- **Documentation:** Update relevant documentation if needed.
- **Labels:** Use labels for better release notes (if applicable)
   - `breaking-change` - For breaking changes
   - `enhancement` - For highlighted features
   - `bug` - For highlighted features
- **Review Process:** Your pull request will be reviewed by maintainers. Be responsive to feedback.

## Code of Conduct
We expect all contributors to follow our Code of Conduct. Treat others with respect and kindness.

## License
What you are allowed to do with this code / repo.
The license used is the [MIT license](https://en.wikipedia.org/wiki/MIT_License). This means that you can do whatever you want with the source code, including using it in commercial software and contexts. However, there is no guarantee or liability for the code.

## Contact
**Let's Connect on Slack! 🚀**

Hey there! 👋 Got a question or just wanna chat about the project? Jump into our [Slack channel](https://webperf.se/articles/webperf-pa-slack/)! We've got a super chill community over at [Webperf on Slack](https://webperf.se/articles/webperf-pa-slack/), and we're all about helping each other out. Don't be shy, come say hi! 🎉

## Funding

We use some great libraries and tools to make webperf_core happen,
if you love it, please consider funding/supporting some of the projects we use either by
using the Sponsor button or by manually visiting one of them:
- [sitespeed.io](https://github.com/sitespeedio/sitespeed.io)

If we use your tool, library and you have started a funding/sponsor/support, please let us
know so we can add you :)