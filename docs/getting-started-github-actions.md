# Getting started with Github Actions

The easiest way to set up webperf-core is by using GitHub Actions for public facing websites.

If you want to test or verify private websites, you should consider one of the other methods.

## How to set up
- [Fork webperf-core repository](https://github.com/Webperf-se/webperf_core/fork?fragment=1)
- You may need to activate the workflow "Manual - Run test against url" in your new repository.
- Remember to update your repository from time to time to receive updates.

### Manually trigger a new test

1. **Navigate to your GitHub repository**: Go to the main page of your repository (at https://github.com) where your GitHub Action is located.

2. **Go to the 'Actions' tab**: On the top of your repository page, you'll see several tabs like 'Code', 'Issues', 'Pull requests', etc. Click on the 'Actions' tab.

3. **Select the workflow**: You'll see a list of workflows on the left side of the screen. Click on the one you want to run manually.
  - Select "Manual - Run test against url" to run a specific test on your URL.

4. **Run workflow**: After selecting the workflow, you'll see a 'Run workflow' dropdown on the right side of the workflow. Click on it.

5. **Choose the branch**: A dropdown menu will appear where you can select the branch where your changes are.
Usually, you'd choose the 'main' branch.
  - "Webpage url to test": Enter your URL here.
  - "Test to run, comma separated list of numbers": Choose which test or tests to run, separated by commas. [Here you can find a list of the testnumbers explained](tests/README.md).
  - "Setting general.review.details": If set to True, it will show a more detailed review when available. This is useful when it's time to actually fix some of the issues and not just track progress.
  - "Setting general.review.data": If set to True, it will include the test data as JSON, which is tech oriented and can be a useful tool for your IT department to help resolve any issues. 
  - "Setting general.review.improve-only": If set to True, it will only display areas that can be improved.

6. **Trigger the workflow**: After selecting your branch, just click the 'Run workflow' button and you're good to go! Once the workflow is triggered, it may take a few minutes to complete. Some tests run quickly, while others take longer. Running multiple tests simultaneously can significantly increase the total runtime.

And that's it! Your workflow should now be running successfully. You can later check the progress or result of the run by: 
  1. Clicking on it in the list on the main page under the 'Actions' tab.
  2. Click the "Build"-button.
  3. Expand the "Test [your test number] for [your URL]" section.
  4. Your test results will be displayed there.

Remember, it's all about trial and error, so don't worry if you don't get it right the first time.

## Update your fork
You should update your fork regularly to ensure you have the latest changes.
  1. Go to the main page of your webperf-core fork (https://github.com/[your username]/webperf_core)
  2. Find the button "Sync fork" and press it.
  3. When it opens it will tell you if your fork is out of date.
  4. Press "Update branch".
  5. Now your fork is updated.
  6. Extra tip: If you don't plan to contribute to the code, go to 'Actions' and disable all workflows except "Manual - Run test against url". This will make the updates faster and easier.
