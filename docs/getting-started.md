# Getting started

Nice that you are here looking how to set webperf-core up :)
There are three methods that we have test and know work when get started.
The easiest to setup are GitHub Actions for public facing websites.
If you want to test/verify private websites like acceptance test environments and more you are probably best to choose the local machine method.
You can read more about every method on the links below.

- [Using GitHub Actions](getting-started-github-actions.md)
- [Using Local Machine / Virtual Machine](getting-started-local.md)
- [Other hosting](getting-started-others.md)

After you have choosen then method to get started and followed the method specific instructions 
you can view more general information below.

## Options and arguments
|Argument|What happens|
|---|---|
| -h/--help | Help information on how to use script |
| -u/--url <site url> | website url to test against |
| -t/--test <test number> | run ONE test (use ? to list available tests) |
| -r/--review | show reviews in terminal |
| -i/--input <file path> | input file path (.json/.sqlite/.csv/.xml) |
| --input-skip <number> | number of items to skip |
| --input-take <number> | number of items to take |
| -o/--output <file path> | output file path (.json/.sqlite/.csv/.sql) |
| -a/--addUrl <site url> | website url (required in compination with -i/--input) |
| -d/--deleteUrl <site url> | website url (required in compination with -i/--input) |
| -L/--language <lang code> | language used for output(en = default/sv) |
