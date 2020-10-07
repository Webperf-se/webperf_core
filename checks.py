#-*- coding: utf-8 -*-
import sys
import socket
import ssl
import json
import requests
import urllib # https://docs.python.org/3/library/urllib.parse.html
import uuid
import re
from bs4 import BeautifulSoup

import gettext
langCode = 'en'
global _
language = gettext.translation('webperf-core', localedir='locales', languages=[langCode])
language.install()
_ = language.gettext

import config

### DEFAULTS
request_timeout = config.http_request_timeout
googlePageSpeedApiKey = config.googlePageSpeedApiKey

TEST_ALL = -1

(TEST_UNKNOWN_01, TEST_GOOGLE_LIGHTHOUSE, TEST_PAGE_NOT_FOUND, TEST_UNKNOWN_03, TEST_UNKNOWN_04, TEST_UNKNOWN_05, TEST_HTML, TEST_CSS, TEST_UNKNOWN_08, TEST_UNKNOWN_09, TEST_UNKNOWN_10, TEST_UNKNOWN_11, TEST_UNKNOWN_12, TEST_UNKNOWN_13, TEST_UNKNOWN_14, TEST_UNKNOWN_15, TEST_UNKNOWN_16, TEST_UNKNOWN_17, TEST_UNKNOWN_18, TEST_UNKNOWN_19, TEST_WEBBKOLL) = range(21)

def check_four_o_four(url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    points = 0.0
    review = ''
    result_dict = {}

    ## kollar koden
    o = urllib.parse.urlparse(url)
    url = '{0}://{1}/2020/{2}-{3}.html'.format(o.scheme, o.netloc, 's1d4-f1nns-1nt3', get_guid(5))
    headers = {'user-agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
    request = requests.get(url, allow_redirects=True, headers=headers, timeout=request_timeout)
    code = request.status_code
    if code == 404:
        points += 2.0
    else:
        review = review + _('TEST_404_REVIEW_WRONG_STATUS_CODE').format(request.status_code) #'* Fel statuskod. Fick {0} när 404 vore korrekt.\n'.format(request.status_code)

    result_dict['status_code'] = code

    # We use variable to validate it once
    requestText = ''
    hasRequestText = False
    found_match = False

    if request.text:
        requestText = request.text
        hasRequestText = True

    if hasRequestText:
        soup = BeautifulSoup(requestText, 'lxml')
        try:
            title = soup.find('title')
            if title:
                result_dict['page_title'] = title.string
            else:
                review = review + _('TEST_404_REVIEW_NO_TITLE') #'* hittade ingen titel på sidan\n'

        except:
            print('Error getting page title!\nMessage:\n{0}'.format(sys.exc_info()[0]))

        try:
            h1 = soup.find('h1')
            if h1:
                result_dict['h1'] = h1.string
            else:
                review = review + _('TEST_404_REVIEW_MAIN_HEADER') #'* hittade ingen huvud rubrik (h1)\n'

        except:
            print('Error getting H1!\nMessage:\n{0}'.format(sys.exc_info()[0]))

        ## kollar innehållet
        four_o_four_strings = []
        four_o_four_strings.append('saknas')
        four_o_four_strings.append('finns inte')
        four_o_four_strings.append('inga resultat')
        four_o_four_strings.append('inte hittas')
        four_o_four_strings.append('inte hitta')
        four_o_four_strings.append('kunde inte')
        four_o_four_strings.append('kunde ej')
        four_o_four_strings.append('hittades inte')
        four_o_four_strings.append('hittar inte')
        four_o_four_strings.append('hittade vi inte')
        four_o_four_strings.append('hittar vi inte')
        four_o_four_strings.append('hittades tyvärr inte')
        four_o_four_strings.append('tagits bort')
        four_o_four_strings.append('fel adress')
        four_o_four_strings.append('trasig')
        four_o_four_strings.append('inte hitta')
        four_o_four_strings.append('ej hitta')
        four_o_four_strings.append('ingen sida')
        four_o_four_strings.append('borttagen')
        four_o_four_strings.append('flyttad')
        four_o_four_strings.append('inga resultat')
        four_o_four_strings.append('inte tillgänglig')
        four_o_four_strings.append('inte sidan')
        four_o_four_strings.append('kontrollera adressen')
        four_o_four_strings.append('kommit utanför')
        four_o_four_strings.append('gick fel')
        four_o_four_strings.append('blev något fel')
        four_o_four_strings.append('kan inte nås')
        four_o_four_strings.append('gammal sida')
        four_o_four_strings.append('hoppsan')
        four_o_four_strings.append('finns inte')
        four_o_four_strings.append('finns ej')
        four_o_four_strings.append('byggt om')
        four_o_four_strings.append('inte finns')
        four_o_four_strings.append('inte fungera')
        four_o_four_strings.append('ursäkta')
        four_o_four_strings.append('uppstått ett fel')
        four_o_four_strings.append('gick fel')

        #print(four_o_four_strings)
        text_from_page = requestText.lower()

        #print(text_from_page)

        for item in four_o_four_strings:
            if item in text_from_page:
                points += 1.5
                found_match = True
                break


    if found_match == False:
        review = review + _('TEST_404_REVIEW_NO_SWEDISH_ERROR_MSG') #'* Verkar sakna text som beskriver att ett fel uppstått (på svenska).\n'
    
    ## hur långt är inehållet
    soup = BeautifulSoup(request.text, 'html.parser')
    if len(soup.get_text()) > 150:
        points += 1.5
    else:
        review = review + _('TEST_404_REVIEW_ERROR_MSG_UNDER_150') #'* Information är under 150 tecken, vilket tyder på att användaren inte vägleds vidare.\n'

    if len(review) == 0:
        review = _('TEST_REVIEW_NO_REMARKS')

    if points == 0:
      points = 1.0

    return (points, review, result_dict)

def check_w3c_valid(url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    points = 0.0
    review = ''

    ## kollar koden
    try:
        url = 'https://validator.w3.org/nu/?doc={0}'.format(url.replace('/', '%2F').replace(':', '%3A'))
        headers = {'user-agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
        request = requests.get(url, allow_redirects=False, headers=headers, timeout=request_timeout)

        ## hämta HTML
        soup = BeautifulSoup(request.text, 'html.parser')
        errors = len(soup.find_all("li", {"class": "error"}))
        # print(len(errors))
    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None

    if errors == 0:
        points = 5.0
        review = '* Inga fel i HTML-koden.\n'
    elif errors <= 5:
        points = 4.0
        review = '* Den testade sidan har {0} st fel i sin HTML-kod.\n'.format(errors)
    elif errors <= 15:
        points = 3.0
        review = '* Den testade sidan har {0} st fel i sin HTML-kod.\n'.format(errors)
    elif errors <= 30:
        points = 2.0
        review = '* Den testade sidan har {0} st fel i sin HTML-kod. Det är inte så bra.\n'.format(errors)
    elif errors > 30:
        points = 1.0
        review = '* Den testade sidan har massor med fel i sin HTML-kod. Hela {0} st. \n'.format(errors)

    return (points, review)

def check_w3c_valid_css(url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    points = 0.0
    review = ''

    ## kollar koden
    try:
        url = 'https://jigsaw.w3.org/css-validator/validator?uri={0}&profile=css3svg&usermedium=all&warning=1&vextwarning=&lang=en'.format(url.replace('/', '%2F').replace(':', '%3A'))
        headers = {'user-agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
        request = requests.get(url, allow_redirects=False, headers=headers, timeout=request_timeout*2)

        ## hämta HTML
        soup = BeautifulSoup(request.text, 'html.parser')
        errors = len(soup.find_all("tr", {"class": "error"}))
        # print(len(errors))
    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None

    if errors == 0:
        points = 5.0
        review = '* Inga fel i CSS-koden.\n'
    elif errors <= 5:
        points = 4.0
        review = '* Den testade sidan har {0} st fel i sin CSS-kod.\n'.format(errors)
    elif errors <= 10:
        points = 3.0
        review = '* Den testade sidan har {0} st fel i sin CSS-kod.\n'.format(errors)
    elif errors <= 20:
        points = 2.0
        review = '* Den testade sidan har {0} st fel i sin CSS-kod. Det är inte så bra.\n'.format(errors)
    elif errors > 20:
        points = 1.0
        review = '* Den testade sidan har massor med fel i sin CSS-kod. Hela {0} st. \n'.format(errors)

    return (points, review)


def check_lighthouse(url, strategy='mobile', category='performance'):
	"""
	perf = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=performance&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
	a11y = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=accessibility&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
	practise = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=best-practices&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
	pwa = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=pwa&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
	seo = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=seo&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
	"""
	check_url = url.strip()
	
	pagespeed_api_request = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category={0}&url={1}&strategy={2}&key={3}'.format(category, check_url, strategy, googlePageSpeedApiKey)
	
	get_content = ''
	
	try:
		get_content = httpRequestGetContent(pagespeed_api_request)
	except:  # breaking and hoping for more luck with the next URL
		print(
			'Error! Unfortunately the request for URL "{0}" failed, message:\n{1}'.format(
				check_url, sys.exc_info()[0]))
		pass
	
	json_content = ''

	try:
		json_content = json.loads(get_content)
	except:  # might crash if checked resource is not a webpage
		print('Error! JSON failed parsing for the URL "{0}"\nMessage:\n{1}'.format(
			check_url, sys.exc_info()[0]))
		pass
	
	return_dict = {}
	return_dict = json_content['lighthouseResult']['audits']['metrics']['details']['items'][0]
	
	for item in json_content['lighthouseResult']['audits'].keys():
		try:
			return_dict[item] = json_content['lighthouseResult']['audits'][item]['numericValue']
		except:
			# has no 'numericValue'
			#print(item, 'har inget värde')
			pass
	
	speedindex = int(return_dict['observedSpeedIndex'])
	review = ''
	
	if speedindex <= 500:
		points = 5
		review = '* Webbplatsen laddar in mycket snabbt!\n'
	elif speedindex <= 1200:
		points = 4
		review = '* Webbplatsen är snabb.\n'
	elif speedindex <= 2500:
		points = 3
		review = '* Genomsnittlig hastighet.\n'
	elif speedindex <= 3999:
		points = 2
		review = '* Webbplatsen är ganska långsam.\n'
	elif speedindex > 3999:
		points = 1
		review = '* Webbplatsen är väldigt långsam!\n'
	
	review += '* Observerad hastighet: {} sekunder\n'.format(convert_to_seconds(return_dict["observedSpeedIndex"], False))
	review += '* Första meningsfulla visuella ändring: {} sek\n'.format(convert_to_seconds(return_dict["firstMeaningfulPaint"], False))
	review += '* Första meningsfulla visuella ändring på 3G: {} sek\n'.format(convert_to_seconds(return_dict["first-contentful-paint-3g"], False))
	review += '* CPU vilar efter: {} sek\n'.format(convert_to_seconds(return_dict["firstCPUIdle"], False))
	review += '* Webbplatsen är interaktiv: {} sek\n'.format(convert_to_seconds(return_dict["interactive"], False))
	review += '* Antal hänvisningar: {} st\n'.format(return_dict["redirects"])
	review += '* Sidans totala vikt: {} kb\n'.format(int(return_dict["total-byte-weight"]/1000))
	
	return (points, review, return_dict)


def check_privacy_webbkollen(url):
    import time
    points = 0.0
    errors = 0
    review = ''

    url = 'https://webbkoll.dataskydd.net/sv/check?url={0}'.format(url.replace('/', '%2F').replace(':', '%3A'))
    headers = {'user-agent': 'Mozilla/5.0 (compatible; Webperf; +https://webperf.se)'}
    request = requests.get(url, allow_redirects=False, headers=headers, timeout=request_timeout*2)

    time.sleep(20)

    ## hämta det faktiska resultatet
    soup = BeautifulSoup(request.text, 'html.parser')
    final_url = None
    for link in soup.find_all('a'):
        final_url = 'https://webbkoll.dataskydd.net{0}'.format(link.get('href'))



    if final_url != None:
        request2 = requests.get(final_url, allow_redirects=True, headers=headers, timeout=request_timeout*2)
        soup2 = BeautifulSoup(request2.text, 'html.parser')
        summary = soup2.find_all("div", class_="summary")

        h3 = soup2.find_all("h3")
        points = 0.0
        i = 0
        return_dict = dict()

        for h3a in h3:
            i += 1
            
            #print(type(h3a.contents))
            if len(h3a.find_all("i", class_="success")) > 0:
                # 1 poäng
                #print('success')
                points += 1.0
            elif len(h3a.find_all("i", class_="warning")) > 0:
                # 0,5 poäng
                #print('warning')
                points += 0.5
            """elif len(h3a.find_all("i", class_="alert")) > 0:
                # 0 poäng
                #print('alert')
            """

        if i == 0:
            raise ValueError('FEL: Verkar inte ha genomförts något test!')

        mess = ''

        for line in summary:
            mess += '* {0}'.format(re.sub(' +', ' ', line.text.strip()).replace('\n', ' ').replace('    ', '\n* ').replace('Kolla upp', '').replace('  ', ' '))

        if  points == 5:
            review = '* Webbplatsen är bra på integritet!\n'
        elif points >= 4:
            review = '* Webbplatsen kan bli bättre, men är helt ok.\n'
        elif points >= 3:
            review = '* Ok integritet men borde bli bättre.\n'
        elif points >= 2:
            review = '* Dålig integritet.\n'
        else:
            review = '* Väldigt dålig integritet!\n'
            points = 1.0

        review += mess

        return (points, review, return_dict)

def httpRequestGetContent(url):
    """Trying to fetch the response content
    Attributes: url, as for the URL to fetch
    """

    try:
        a = requests.get(url)

        return a.text
    except requests.exceptions.SSLError:
        if 'http://' in url: # trying the same URL over SSL/TLS
            print('Info: Trying SSL before giving up.')
            return httpRequestGetContent(url.replace('http://', 'https://'))
    except requests.exceptions.ConnectionError:
        print(
            'Connection error! Unfortunately the request for URL "{0}" failed.\nMessage:\n{1}'.format(url, sys.exc_info()[0]))
        pass
    except:
        print(
            'Error! Unfortunately the request for URL "{0}" either timed out or failed for other reason(s). The timeout is set to {1} seconds.\nMessage:\n{2}'.format(url, timeout_in_seconds, sys.exc_info()[0]))
        pass

def get_guid(length):
    """
    Generates a unique string in specified length
    """
    return str(uuid.uuid4())[0:length]

def convert_to_seconds(millis, return_with_seconds=True):
    """
    Converts milliseconds to seconds.
    Arg: 'return_with_seconds' defaults to True and returns string ' sekunder' after the seconds
    """
    if return_with_seconds:
        return (millis/1000)%60 + " sekunder"
    else:
        return (millis/1000)%60

"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    print(check_google_pagespeed('https://webperf.se'))