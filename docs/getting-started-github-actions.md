# Gettings started with Github Actions

The easiest method to setup webperf-core are by using GitHub Actions for public facing websites.

If you want to test/verify private websites you should probably look at one of the other methonds.

## How to setup
- [Fork webperf-core repository](https://github.com/Webperf-se/webperf_core/fork?fragment=1)
- You may need to activate the workflow "Manual xxxxx" in your new repository.
- Remember, you need to update you repository from time to time to get updates

### Manually trigger new test

1. **Navigate to your GitHub repository**: First things first, you need to go to the main page of your repository (at https://github.com) where your GitHub Action is located.

2. **Go to the 'Actions' tab**: On the top of your repository page, you'll see several tabs like 'Code', 'Issues', 'Pull requests', etc. Click on the 'Actions' tab.

3. **Select the workflow**: You'll see a list of workflow files on the left side of the screen. Click on the one you want to run manually.

4. **Run workflow**: After selecting the workflow, you'll see a 'Run workflow' dropdown on the right side of the workflow. Click on it.

5. **Choose the branch**: A dropdown menu will appear where you can select the branch where your changes are.
Usually, you'd choose the 'main' branch.

6. **Trigger the workflow**: After selecting your branch, just click the 'Run workflow' button and you're good to go!

And that's it! Your workflow should now be running. You later check the progress/result of the run by clicking on it in the 'Actions' tab. Remember, it's all about trial and error, so don't worry if you don't get it right the first time.
