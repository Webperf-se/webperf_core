#-*- coding: utf-8 -*-
import requests
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from sqlalchemy import text
import config

app = Flask(__name__)# mysql stuff
app.config['SQLALCHEMY_DATABASE_URI'] = config.mysqlString
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def getGzipedContentFromUrl(url):
    """
    Fetching a gziped file from Internet, unpacks it and returns its contents.
    """
    unique_id = getUniqueId(5)
    file_name = 'tmp/file-{0}.gz'.format(unique_id)

    try:
        r = requests.get(url, stream=True)
        with open(file_name, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)

        with gzip.open(file_name, 'rb') as f:
            file_content = f.read()

        return file_content
    except SSLError:
        if 'http://' in url: # trying the same URL over SSL/TLS
            return getGzipedContentFromUrl(url.replace('http://', 'https://'))
        else:
            return None
    except:
        print(
            'Error! Unfortunately the request for URL "{0}" either timed out or failed for other reason(s). The timeout is set to {1} seconds.\nMessage:\n{2}'.format(
                url, timeout_in_seconds, sys.exc_info()[0]))
        return None

def mysql_query(query):
    """
    Executes INSERT, DELETE and UPDATE queries
    """
    sql = text(query)
    result = db.engine.execute(sql)

    # print(query)
    result.close() #NY
    return None

def mysql_query_single_value(query):
    """
    Returns a single value from a dbase
    """
    sql = text(query)
    result = db.engine.execute(sql)

    for row in result:
        return row[0]

    result.close() #NY
    return None

def send_email(mail_recipient, subject, body, mail_user = 'reports@webperf.se', mail_password = 'uvvq%;~Y&X-f'):
    import smtplib
    from email.mime.text import MIMEText

    FROM = mail_user
    TO = mail_recipient if type(mail_recipient) is list else [mail_recipient]
    SUBJECT = subject
    # TODO: escapa innehållet
    TEXT = body

    # Prepare actual message
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP_SSL("hachiman.oderland.com", 465)
        server.ehlo()
        #server.starttls()
        server.login(mail_user, mail_password)
        server.sendmail(FROM, TO, message)
        server.close()
        print('successfully sent the mail')
    except Exception as e:
        print("failed to send mail", e)

def httpRequestGetContent(url):
    """Trying to fetch the response content
    Attributes: url, as for the URL to fetch
    """
    if '.gz' in url or '.gzip' in url:
        # the url indicates that it is compressed using Gzip
        return getGzipedContentFromUrl(url)

    timeout_in_seconds = 30

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

"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    send_email('m@tba.nu', 'Testrubrik', 'Testinnehall Ny rad')

