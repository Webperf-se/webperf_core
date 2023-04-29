# How to Contribute

Do you want to contribute?
You can contribute here at Github. By checking the code, trying the documentation, suggesting new tests, among other things.

* [Feature requests](#feature-requests)
* [Bug reports](#bug-reports)
* [Pull Requests](#pull-requests)
* [License](#license)
* [Translations](#translations)


## Feature requests
add ingress here


## Bug reports
add ingress here


## Pull Requests
add ingress here


## License
What you are allowed to do with this code / repo.
The license used is the [MIT license](https://en.wikipedia.org/wiki/MIT_License). This means that you can do whatever you want with the source code, including using it in commercial software and contexts. However, there is no guarantee or liability for the code.


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

