# Gettings started with Github Actions

The easiest method to setup webperf-core are by using GitHub Actions for public facing websites.
If you want to test/verify private websites you should probably look at one of the other methonds.

## How to setup
- [Fork webperf-core repository](https://github.com/Webperf-se/webperf_core/fork?fragment=1)
- Remove tests you don't want from your `./github/workflows/` folder (You probably only want `codeql-analysis.yml` and `regression-test-translations.yml` if you are contributing).
- Rest of the steps depend on how you want to run/trigger the test, see below

### Triggeron Push or Pull request

Choose this option if you want to [contribute](CONTRIBUTING.md) or have your own website you want the test to run against for every commit/change of your code.

#### How to setup:

- Change `https://webperf.se/` in all `.yml` files to the url you want to test with.
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
