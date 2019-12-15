# Webperf Core
Minimalistic client mainly running on PythonAnywhere.com, accessing different websites, or web-APIs, and scraping them.

## Dependencies
* Check the requirements.txt file. It was generated on Linux and is not yet tested on either Macos or Windows.
* Also need some MySQL stuff, but which libs differ on Macos and Linux. On PythonAnywhere.com it worked without any effort.

## Usage
Open the terminal, enter folder and type *python default.py*  
Also support arguments, *python default.py id=1* to only test the site with id 1, and *python default.py cat=1* to only test the sites with 'category' set to 1.
