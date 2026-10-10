# Translation

The following is copied from Slack community threads,translated from Swedish.

## Create Your Own Copy of Our Repository

- Sign up for a free account at [GitHub](https://github.com).
- Sign in with your new account.
- Go to [Webperf Core Repository](https://github.com/Webperf-se/webperf_core/).
- Press the "Fork" button.

You now have your own copy where you can make all your changes.

When you are done with all the changes,  
go to the "Pull requests" tab and press the button to create a new pull request.  
Once you do that, we will receive a notification and review your suggested changes.

## General Information About Translation

All help with writing texts is greatly appreciated! 😃  

No coding knowledge is required; everything can be done directly in the browser on GitHub. 🙂  

The following files need to be updated:  
- [404 Test (English)](https://github.com/Webperf-se/webperf_core/blob/main/locales%2Fen%2FLC_MESSAGES%2F404.po)  
- [A11y Statement Test (English)](https://github.com/Webperf-se/webperf_core/blob/main/locales%2Fen%2FLC_MESSAGES%2Fa11y-statement.po)  
- [CSS Test](https://github.com/Webperf-se/webperf_core/blob/main/locales%2Fen%2FLC_MESSAGES%2Fcss.po)  
- [HTML Test (English)](https://github.com/Webperf-se/webperf_core/blob/main/locales%2Fen%2FLC_MESSAGES%2Fhtml.po)  
- [Javascript Test](https://github.com/Webperf-se/webperf_core/blob/main/locales%2Fen%2FLC_MESSAGES%2Fjavascript.po)  
- [Lighthouse Test](https://github.com/Webperf-se/webperf_core/blob/main/locales%2Fen%2FLC_MESSAGES%2Flighthouse.po)  

In this thread, I will explain for each text how you can figure out what text should be there.

### General Notes for `.po` Files
The texts in each of the files above work as follows:  
There is a text for completed rules (resolved) and a text for rules that still need to be addressed (unresolved).  
The text between the two `"` on each line that starts with `msgstr` needs to be more understandable.  

On lines where the text in `msgstr` starts with the same text as `msgid`, it is completely untranslated.  

The first part of `msgid` before the space (in the second image circled in green) is the rule ID.  
This is useful for getting more information about what text makes sense to write.  
More on this in the text specific to each file.

### General Notes for All Tests
All tests have language support.  
English is the reference. Every test has one `.po` file per language under `locales/<lang>/LC_MESSAGES/`, and every language must have the same msgids as English.

Supported languages: `en` English, `sv` Swedish, `da` Danish, `no` Norwegian, `fi` Finnish, `is` Icelandic, `de` German, `fr` French, `es` Spanish, `it` Italian. Select one with `-L <code>` or `general.language`.

German, French, Spanish and Italian were machine translated in October 2026 and have not yet been reviewed by native speakers. Corrections are welcome as pull requests that change only the `.po` file and its compiled `.mo`:

```
python3 data/msgfmt.py -o locales/de/LC_MESSAGES/http_validator.mo locales/de/LC_MESSAGES/http_validator.po
```

## Test-Specific Notes About Translation

### CSS Test
For the CSS Test, you can find out more about the rule by visiting the Stylelint website at the following address:  
`https://stylelint.io/user-guide/rules/{rule-id}`  

Replace `{rule-id}` with the rule ID you want to get more information about.

For example:  
For `unit-no-unknown`, the address is:  
[https://stylelint.io/user-guide/rules/unit-no-unknown](https://stylelint.io/user-guide/rules/unit-no-unknown).

### Javascript Test
For the Javascript Test, the address is:  
`https://eslint.org/docs/latest/rules/{rule-id}`

### HTML Test
For the HTML Test, the address is:  
[https://html-validate.org/rules/{rule-id}.html](https://html-validate.org/rules/{rule-id}.html)
