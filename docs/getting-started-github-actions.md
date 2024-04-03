# Gettings started with Github Actions

The easiest method to setup webperf-core are by using GitHub Actions for public facing websites.
If you want to test/verify private websites you should probably look at one of the other methonds.

## How to setup
- [Fork webperf-core repository](https://github.com/Webperf-se/webperf_core/fork?fragment=1)
- Remove tests you don't need from your `./github/workflows/` folder (You only need: `close-inactive-issues.yml`, `codeql-analysis.yml`, `pylint.yml`, `regression-test-translations.yml` and `update-software.yml` if you are contributing and are working on a Pull Request).
- Rest of the steps depend on how you want to run/trigger the test, see below

### Triggeron Push or Pull request

Choose this option if you want to [contribute](CONTRIBUTING.md) or have your own website you want the test to run against for every commit/change of your code.

#### How to setup:

- Change `https://webperf.se/` in `sites.json` file to the url you want to test with.
  (If you want to test more then one, add them)
- Now every time you push new changes or create a pull request all `.yml` tests will run.

### Trigger on a Schedule

- Add info on what this is?
- Add steps on how to do this.
- Add read more / reference links

[Read more onf how to schedule testing](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onschedule)

### Trigger on issue

- Add info on what this is?
- Add steps on how to do this.
- Add read more / reference links


## Read more

- https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
