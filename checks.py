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

from common import httpRequestGetContent, mysql_query
import config

### DEFAULTS
request_timeout = config.http_request_timeout
googlePageSpeedApiKey = config.googlePageSpeedApiKey

def check_four_o_four(url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    points = 0
    review = ''
    result_dict = {}

    ## kollar koden
    o = urllib.parse.urlparse(url)
    url = '{0}://{1}/{2}-{3}.html'.format(o.scheme, o.netloc, 's1d4-f1nns-1nt3', get_guid(5))
    headers = {'user-agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
    request = requests.get(url, allow_redirects=False, headers=headers, timeout=request_timeout)
    code = request.status_code
    if code == 404:
        points += 2
    else:
        review = review + '* Fel statuskod. Fick {0} när 404 vore korrekt.\n'.format(request.status_code)

    result_dict['status_code'] = code

    soup = BeautifulSoup(request.text, 'lxml')
    try:
        result_dict['page_title'] = soup.title.text
    except:
        print('Error!\nMessage:\n{0}'.format(sys.exc_info()[0]))

    try:
        result_dict['h1'] = soup.find('h1').text
    except:
        print('Error!\nMessage:\n{0}'.format(sys.exc_info()[0]))

    #print(code)

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
    text_from_page = request.text.lower()
    found_match = False

    #print(text_from_page)

    for item in four_o_four_strings:
        if item in text_from_page:
            points += 1.5
            found_match = True
            break

    if found_match is False:
        review = review + '* Verkar sakna text som beskriver att ett fel uppstått (på svenska).\n'

    #if 'saknas' in request.text.lower() or 'finns inte' in request.text.lower() or 'inte hittas' in request.text.lower() or 'kunde inte' in request.text.lower() or 'kunde ej' in request.text.lower() or 'hittades inte' in request.text.lower() or 'tagits bort' in request.text.lower() or 'fel adress' in request.text.lower() or 'trasig' in request.text.lower() or 'inte hitta' in request.text.lower():
    #    points += 1.5
    #else:
    #    review = review + '* Verkar sakna text som beskriver att ett fel uppstått (på svenska).\n'

    ## hur långt är inehållet
    soup = BeautifulSoup(request.text, 'html.parser')
    if len(soup.get_text()) > 150:
        points += 1.5
    else:
        review = review + '* Information är under 150 tecken, vilket tyder på att användaren inte vägleds vidare.\n'

    if len(review) == 0:
        review = 'Inga anmärkningar.'

    if points is 0:
      points = 1

    return (points, review, result_dict)

def check_w3c_valid(url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    points = 0
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
        points = 5
        review = '* Inga fel i HTML-koden.\n'
    elif errors <= 5:
        points = 4
        review = '* Den testade sidan har {0} st fel i sin HTML-kod.\n'.format(errors)
    elif errors <= 15:
        points = 3
        review = '* Den testade sidan har {0} st fel i sin HTML-kod.\n'.format(errors)
    elif errors <= 30:
        points = 2
        review = '* Den testade sidan har {0} st fel i sin HTML-kod. Det är inte så bra.\n'.format(errors)
    elif errors > 30:
        points = 1
        review = '* Den testade sidan har massor med fel i sin HTML-kod. Hela {0} st. \n'.format(errors)

    return (points, review)

def check_w3c_valid_css(url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    points = 0
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
        points = 5
        review = '* Inga fel i CSS-koden.\n'
    elif errors <= 5:
        points = 4
        review = '* Den testade sidan har {0} st fel i sin CSS-kod.\n'.format(errors)
    elif errors <= 10:
        points = 3
        review = '* Den testade sidan har {0} st fel i sin CSS-kod.\n'.format(errors)
    elif errors <= 20:
        points = 2
        review = '* Den testade sidan har {0} st fel i sin CSS-kod. Det är inte så bra.\n'.format(errors)
    elif errors > 20:
        points = 1
        review = '* Den testade sidan har massor med fel i sin CSS-kod. Hela {0} st. \n'.format(errors)

    return (points, review)

def check_http_status_code(url):
    headers = {'user-agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
    request = requests.get(url, allow_redirects=False, headers=headers, timeout=request_timeout)
    return request.status_code

def check_encoding(url):
    r = requests.get(url, timeout = request_timeout)

    return r.encoding

def check_content_type(url):
    r = requests.get(url, timeout = request_timeout)

    return r.headers.get('content-type')

def http_status_code_check(url):
    r = requests.get(url, timeout = request_timeout)
    return r.status_code

def check_redirection(url):
    """
    Kollar om servern vill skicka runt användaren. Kolla dels redirs men också om HTTP->HTTPS är korrekt
    """
    r = requests.head(url, allow_redirects=True, timeout = request_timeout)
    return (r.url, r.history)
    # r.url
    # 'https://github.com/'

    # r.history
    # [<Response [301]>]

def check_google_pagespeed(url, strategy='mobile'):
    """Checks the Pagespeed Insights with Google
    In addition to the 'mobile' strategy there is also 'desktop' aimed at the desktop user's preferences
    Returns a dictionary of the results.

    attributes: check_url, strategy
    """
    check_url = url.strip()

    # urlEncodedURL = parse.quote_plus(check_url)	# making sure no spaces or other weird characters f*cks up the request, such as HTTP 400
    pagespeed_api_request = 'https://www.googleapis.com/pagespeedonline/v4/runPagespeed?url={}&strategy={}&key={}'.format(check_url, strategy, googlePageSpeedApiKey)
    #print('HTTP request towards GPS API: {}'.format(pagespeed_api_request))

    get_content = ''

    try:
        get_content = httpRequestGetContent(pagespeed_api_request)
        get_content = BeautifulSoup(get_content, "html.parser")
        get_content = str(get_content.encode("ascii"))
    except:  # breaking and hoping for more luck with the next URL
        print(
            'Error! Unfortunately the request for URL "{0}" failed, message:\n{1}'.format(
                check_url, sys.exc_info()[0]))
        pass
    # try:
    get_content = get_content[2:][:-1]  # removes two first chars and the last one
    get_content = get_content.replace('\\n', '\n').replace("\\'",
                                                           "\'")  # .replace('"', '"') #.replace('\'', '\"')
    get_content = get_content.replace('\\\\"', '\\"').replace('""', '"')

    json_content = ''
    try:
        json_content = json.loads(get_content)
    except:  # might crash if checked resource is not a webpage
        print('Error! JSON failed parsing for the URL "{0}"\nMessage:\n{1}'.format(
            check_url, sys.exc_info()[0]))
        pass

    return_dict = {}
    try:
        # overall score
        for key in json_content['ruleGroups'].keys():
            # print('Key: {0}, value {1}'.format(key, json_content['ruleGroups'][key]['score']))
            return_dict[key] = json_content['ruleGroups'][key]['score']

        # page statistics
        for key in json_content['pageStats'].keys():
            # print('Key: {0}, value {1}'.format(key, json_content['pageStats'][key]))
            return_dict[key] = json_content['pageStats'][key]

        # page potential
        for key in json_content['formattedResults']['ruleResults'].keys():
            # print('Key: {0}, value {1}'.format(key, json_content['formattedResults']['ruleResults'][key]['ruleImpact']))
            return_dict[key] = json_content['formattedResults']['ruleResults'][key]['ruleImpact']

        g_pagespeed = return_dict["SPEED"]
        if  g_pagespeed >= 84:
            points = 5
            review = '* Webbplatsen är riktigt snabb!\n'
        elif g_pagespeed >= 76:
            points = 4
            review = '* Webbplatsen är snabb.\n'
        elif g_pagespeed >= 70:
            points = 3
            review = '* Genomsnittligt men inte så värst bra.\n'
        elif g_pagespeed >= 60:
            points = 2
            review = '* Webbplatsen är rätt långsam.\n'
        elif g_pagespeed < 60:
            points = 1
            review = '* Webbplatsen har väldigt dåliga prestanda enligt Google Pagespeed!\n'

        review += '* Antal resurser: {} st\n'.format(return_dict["numberResources"])
        review += '* Antal värdar: {} st\n'.format(return_dict["numberHosts"])
        review += '* Storlek på förfrågan: {} bytes\n'.format(return_dict["totalRequestBytes"])
        review += '* Statiska filer: {} st\n'.format(return_dict["numberStaticResources"])
        review += '* Storlek på HTML: {} bytes\n'.format(return_dict["htmlResponseBytes"])
        review += '* Storlek på sidvisning: {} bytes\n'.format(return_dict["overTheWireResponseBytes"])
        review += '* Storlek på CSS: {} bytes\n'.format(return_dict["cssResponseBytes"])
        review += '* Storlek på bilder: {} bytes\n'.format(return_dict["imageResponseBytes"])
        review += '* Storlek på Javascript: {} bytes\n'.format(return_dict["javascriptResponseBytes"])
        review += '* Antal Javascriptfiler: {} st\n'.format(return_dict["numberJsResources"])
        review += '* Antal CSS-filer: {} st\n'.format(return_dict["numberCssResources"])

        # potential
        review += '* Antal roundtrips: {} st\n'.format(return_dict["numTotalRoundTrips"])
        review += '* Antal blockerande roundtrips: {} st\n'.format(return_dict["numRenderBlockingRoundTrips"])
        review += '* Undvik hänvisningar: {}\n'.format("Ok" if int(return_dict["AvoidLandingPageRedirects"]) < 2 else "Behöver förbättras")
        review += '* Aktivera GZIP-komprimering: {}\n'.format("Ok" if int(return_dict["EnableGzipCompression"]) < 2 else "Behöver förbättras")
        review += '* Använd webbläsarens cache: {}\n'.format("Ok" if int(return_dict["LeverageBrowserCaching"]) < 2 else "Behöver förbättras")
        review += '* Är webbservern snabb: {}\n'.format("Ok" if int(return_dict["MainResourceServerResponseTime"]) < 2 else "Behöver förbättras")
        review += '* Behöver CSS-filer minimeras: {}\n'.format("Ok" if int(return_dict["MinifyCss"]) < 2 else "Behöver förbättras")
        review += '* Behöver HTML-filen minimeras: {}\n'.format("Ok" if int(return_dict["MinifyHTML"]) < 2 else "Behöver förbättras")
        review += '* Behöver Javascript-filer minimeras: {}\n'.format("Ok" if int(return_dict["MinifyJavaScript"]) < 2 else "Behöver förbättras")
        review += '* Blockeras sidvisningen: {}\n'.format("Ok" if int(return_dict["MinimizeRenderBlockingResources"]) < 2 else "Behöver förbättras")
        review += '* Behöver bilderna optimeras för webben: {}\n'.format("Ok" if int(return_dict["OptimizeImages"]) < 2 else "Behöver förbättras")
        review += '* Behöver synligt innehåll prioriteras: {}\n'.format("Ok" if int(return_dict["PrioritizeVisibleContent"]) < 2 else "Behöver förbättras")

    except:
        print('Error! Request for URL "{0}" failed.\nMessage:\n{1}'.format(check_url, sys.exc_info()[0]))
        pass

    return (points, review, return_dict)

def check_google_usability(url, strategy='mobile'):
    """Checks the Pagespeed Insights with Google
    In addition to the 'mobile' strategy there is also 'desktop' aimed at the desktop user's preferences
    Returns a dictionary of the results.

    attributes: check_url, strategy
    """
    check_url = url.strip()

    # urlEncodedURL = parse.quote_plus(check_url)	# making sure no spaces or other weird characters f*cks up the request, such as HTTP 400
    pagespeed_api_request = 'https://www.googleapis.com/pagespeedonline/v2/runPagespeed?url={}&strategy={}&key={}'.format(check_url, strategy, googlePageSpeedApiKey)
    #print('HTTP request towards GPS API: {}'.format(pagespeed_api_request))

    get_content = ''

    try:
        get_content = httpRequestGetContent(pagespeed_api_request)
        get_content = BeautifulSoup(get_content, "html.parser")
        get_content = str(get_content.encode("ascii"))
    except:  # breaking and hoping for more luck with the next URL
        print(
            'Error! Unfortunately the request for URL "{0}" failed, message:\n{1}'.format(
                check_url, sys.exc_info()[0]))
        pass
    # try:
    get_content = get_content[2:][:-1]  # removes two first chars and the last one
    get_content = get_content.replace('\\n', '\n').replace("\\'",
                                                           "\'")  # .replace('"', '"') #.replace('\'', '\"')
    get_content = get_content.replace('\\\\"', '\\"').replace('""', '"')

    json_content = ''
    try:
        json_content = json.loads(get_content)
    except:  # might crash if checked resource is not a webpage
        print('Error! JSON failed parsing for the URL "{0}"\nMessage:\n{1}'.format(
            check_url, sys.exc_info()[0]))
        pass

    #print(json_content)

    return_dict = {}
    try:
        # overall score
        for key in json_content['ruleGroups'].keys():
            # print('Key: {0}, value {1}'.format(key, json_content['ruleGroups'][key]['score']))
            if key == 'USABILITY':
                return_dict['Usability'] = json_content['ruleGroups'][key]['score']

        # page potential
        for key in json_content['formattedResults']['ruleResults'].keys():
            # print('Key: {0}, value {1}'.format(key, json_content['formattedResults']['ruleResults'][key]['ruleImpact']))
            if key == 'ConfigureViewport' or key == 'AvoidPlugins' or key == 'SizeContentToViewport' or key == 'SizeTapTargetsAppropriately' or key == 'UseLegibleFontSizes':
                return_dict[key] = json_content['formattedResults']['ruleResults'][key]['ruleImpact']

    except:
        print('Error! Request for URL "{0}" failed.\nMessage:\n{1}'.format(check_url, sys.exc_info()[0]))
        pass

    g_usability = return_dict["Usability"]
    if  g_usability > 99:
        points = 5
        review = '* Väldigt användbar design!\n'
    elif g_usability >= 98:
        points = 4
        review = '* Webbplatsen är användbar.\n'
    elif g_usability >= 97:
        points = 3
        review = '* Genomsnittlig användbarhet, men inte så värst bra.\n'
    elif g_usability >= 96:
        points = 2
        review = '* Webbplatsen behöver bli bättre på användbarhet.\n'
    elif g_usability < 96:
        points = 1
        review = '* Stora brister i användbarheten!\n'

    review += '* Usability: {} av 100\n'.format(return_dict["Usability"])
    review += '* Mobil viewport konfigurerad: {}\n'.format("Ok" if float(return_dict["ConfigureViewport"]) < 0.01 else "Behöver förbättras")
    review += '* Bredd på innehåll & viewport: {}\n'.format("Ok" if float(return_dict["SizeContentToViewport"]) < 0.01 else "Behöver förbättras")
    review += '* Träffytor eller mellanrum för knappar/länkar: {}\n'.format("Ok" if float(return_dict["SizeTapTargetsAppropriately"]) < 0.01 else "Behöver förbättras")
    review += '* Textens läsbarhet: {}\n'.format("Ok" if float(return_dict["UseLegibleFontSizes"]) < 0.01 else "Behöver förbättras")
    review += '* Undvik plugins: {}\n'.format("Ok" if float(return_dict["AvoidPlugins"]) < 0.01 else "Behöver förbättras")

    return (points, review, return_dict)

def check_privacy_webbkollen(url):
    import time
    points = 0
    errors = 0
    review = ''

    ## kollar koden
    #try:

    url = 'https://webbkoll.dataskydd.net/sv/check?url={0}'.format(url.replace('/', '%2F').replace(':', '%3A'))
    headers = {'user-agent': 'Mozilla/5.0 (compatible; Webperf; +https://webperf.se)'}
    request = requests.get(url, allow_redirects=False, headers=headers, timeout=request_timeout*2)

    time.sleep(20)

    ## hämta det faktiska resultatet
    soup = BeautifulSoup(request.text, 'html.parser')
    final_url = None
    for link in soup.find_all('a'):
        final_url = 'https://webbkoll.dataskydd.net{0}'.format(link.get('href'))



    if final_url is not None:
        request2 = requests.get(final_url, allow_redirects=True, headers=headers, timeout=request_timeout*2)
        soup2 = BeautifulSoup(request2.text, 'html.parser')
        #soup2 = BeautifulSoup(exempelkod, 'html.parser')
        summary = soup2.find_all("div", class_="summary")
        """
        success = len(soup2.find_all("i", class_="icon-check success"))
        fails = len(soup2.find_all("i", class_="icon-times alert"))

        return_dict = dict()
        return_dict['lyckade_test'] = success
        return_dict['missade_test'] = fails

        if success is 0 and fails is 0:
            raise ValueError('FEL: Verkar inte ha genomförts något test!')
        else:
            success_rate = success / fails
            return_dict['success_rate'] = success

        print('* Lyckade test: ', success)
        print('* Saker att åtgärda: ', fails)
        print('* Success rate: ', success_rate)
        """

        h3 = soup2.find_all("h3")
        points = 0.0
        i = 0
        return_dict = dict()

        for h3a in h3:
            i += 1
            status_bild = h3a.find('i')
            #print(type(status_bild))

            #print(len(h3a.find_all("i", class_="success")))
            #print(len(h3a.find_all("i", class_="warning")))

            #print(type(h3a.contents))
            if len(h3a.find_all("i", class_="success")) > 0:
                # 1 poäng
                #print('success')
                points += 1
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
            #print('*', re.sub(' +', ' ', line.text.strip()).replace('\n', ' ').replace('    ', '\n* ').replace('Kolla upp', '').replace('  ', ' '))
            #print('\n')

        """if  success_rate > 0.84999:
            points = 5
            review = '* Webbplatsen är bra på integritet!\n'
        elif success_rate > 0.64999:
            points = 4
            review = '* Webbplatsen kan bli bättre, men är helt ok.\n'
        elif success_rate > 0.4999:
            points = 3
            review = '* Genomsnittlig integritet men borde bli bättre.\n'
        elif success_rate > 0.2999:
            points = 2
            review = '* Dålig integritet.\n'
        else:
            points = 1
            review = '* Väldigt dålig integritet!\n'"""

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


def get_guid(length):
    """
    Generates a unique string in specified length
    """
    return str(uuid.uuid4())[0:length]

def is_sitemap(content):
    """Check a string to see if its content is a sitemap or siteindex.

    Attributes: content (string)
    """
    if 'http://www.sitemaps.org/schemas/sitemap/' in content or '<sitemapindex' in content:
        return True

    return False

"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    #print(check_google_usability('https://polismuseet.se'))
    print(check_google_pagespeed('https://webperf.se'))