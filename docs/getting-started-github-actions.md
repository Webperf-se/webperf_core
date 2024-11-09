# Gettings started with Github Actions

The easiest method to setup webperf-core are by using GitHub Actions for public facing websites.

If you want to test/verify private websites you should probably look at one of the other methonds.

## How to setup
[Fork webperf-core repository](https://github.com/Webperf-se/webperf_core/fork?fragment=1)
- Change `https://webperf.se/` in `defaults/sites.json` file to the url you want to test with.
  (If you want to test more then one, add them)
- Remove tests you don't need from your `./github/workflows/` folder
  (You only need: `close-inactive-issues.yml`, `codeql-analysis.yml`, `pylint.yml`, `regression-test-translations.yml` and `update-software.yml` if you are contributing and are working on a Pull Request).
- Rest of the steps depend on how you want to run/trigger the test, see below

### Manually trigger new test

1. **Navigate to your GitHub repository**: First things first, you need to go to the main page of your repository (at https://github.com) where your GitHub Action is located.

2. **Go to the 'Actions' tab**: On the top of your repository page, you'll see several tabs like 'Code', 'Issues', 'Pull requests', etc. Click on the 'Actions' tab.

3. **Select the workflow**: You'll see a list of workflow files on the left side of the screen. Click on the one you want to run manually.

4. **Run workflow**: After selecting the workflow, you'll see a 'Run workflow' dropdown on the right side of the workflow. Click on it.

5. **Choose the branch**: A dropdown menu will appear where you can select the branch where your changes are.
Usually, you'd choose the 'main' branch.

6. **Trigger the workflow**: After selecting your branch, just click the 'Run workflow' button and you're good to go!

And that's it! Your workflow should now be running. You later check the progress/result of the run by clicking on it in the 'Actions' tab. Remember, it's all about trial and error, so don't worry if you don't get it right the first time.

### Trigger on Push or Pull request

Choose this option if you want to [contribute](CONTRIBUTING.md) or have your own website you want the test to run against for every commit/change of your code.

#### How to setup:

- Now every time you push new changes or create a pull request all `.yml` tests will run.

### Trigger on a Schedule

1. **Access your GitHub repository**: The first step is to navigate to your GitHub repository where your GitHub Action is located.

2. **Locate your workflow file**: Within your repository, find the `.github/workflows` directory. This is where your workflow files (`.yml`) are stored.

3. **Edit your workflow file**: Open the workflow file you wish to schedule. You'll need to add or modify the `on:` field in your workflow file.

4. **Set up a schedule**: Under the `on:` field, add a `schedule:` field. This is where you'll specify when the GitHub Action should run. Here's an example:

```yaml
on:
  schedule:
    - cron:  '0 0 * * *'
```

   In this example, the cron syntax ‘0 0 * * *’ schedules the action to run at midnight every day. The cron syntax is quite flexible, allowing you to specify complex schedules.

5. **Commit your changes**: Once you’ve added your schedule, commit the changes to your workflow file. Make sure to write a clear commit message describing what you’ve changed.
6. **Push your changes**: Push your commit to the GitHub repository. If you’re working on a branch, you may also need to create a pull request and merge it into the main branch.

[Read more onf how to schedule testing](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onschedule)

### Trigger on issue

- Add info on what this is?
- Add steps on how to do this.
- Add read more / reference links


## Read more

- https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
