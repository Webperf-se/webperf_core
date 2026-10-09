# Test name

Copy this file to `docs/tests/<test-name>.md`, add the test to the list in [README.md](README.md) and replace every section below. Keep the headings: readers and the unit test that checks the list rely on them. Write what is true for this test, with numbers taken from the code, and skip sections that do not apply rather than leaving a placeholder.

One or two sentences on what the test does and how it runs: a Python test in `tests/<file>.py`, or a sitespeed.io plugin in its own repository.

## What is being tested?

The checks the test makes, in the order they run. For an issue based test, a table with every rule, its severity, its category and when it fails. For a test with its own logic, the sub checks.

## How are rating being calculated?

Which of the five rating fields the test sets, and the points per outcome. Link to [How ratings are calculated](../rating.md) for the shared model and only describe what is specific. Say what happens when data is missing or the site cannot be reached.

## Read more

Specifications, laws or tools the test is built on, one line each on why the link is there.

## How to setup?

What the test needs beyond the general setup: npm packages, a browser, Docker, a data file in `data/`, a setting, network access to a service. Link to [sitespeed.md](sitespeed.md) for sitespeed.io based tests instead of repeating it. Say which settings under `tests.<name>.*` change the result.

## FAQ

Only if there are real questions. Delete the section otherwise.
