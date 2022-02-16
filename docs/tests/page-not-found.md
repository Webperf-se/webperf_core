# 404 (Page not Found)
[![Regression Test - 404 (Page not Found) Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-404.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-404.yml)

This test is checking if you have set up a 404 (page not found) page correctly.
We are doing this by calling a random url on your domain and verifying following:
- HTTP Status Code is 404
- The resource returned is HTML
- The HTML has a `title` element
- The HTML has a `h1` element header
- Text content are more then 150 chars
- One or more of the following strings exist on page (only swedish for now)
  - saknas
  - finns inte
  - inga resultat
  - inte hittas
  - inte hitta
  - kunde inte
  - kunde ej
  - hittades inte
  - hittar inte
  - hittade vi inte
  - hittar vi inte
  - hittades tyvärr inte
  - tagits bort
  - fel adress
  - trasig
  - inte hitta
  - ej hitta
  - ingen sida
  - borttagen
  - flyttad
  - inga resultat
  - inte tillgänglig
  - inte sidan
  - kontrollera adressen
  - kommit utanför
  - gick fel
  - blev något fel
  - kan inte nås
  - gammal sida
  - hoppsan
  - finns inte
  - finns ej
  - byggt om
  - inte finns
  - inte fungera
  - ursäkta
  - uppstått ett fel
  - gick fel

## How are rating being calculated?

You can get 1-5 in rating for every section:
- HTTP Status Code is 404
- The resource returned is HTML
- The HTML has a `title` element
- The HTML has a `h1` element header
- Text content are more then 150 chars
- One or more of the following strings exist on page

They are then combined.

## Read more

Links to other sources where you can test or read more

## How to setup?

### Prerequirements

* Fork this repository
* As we are using external service ( https://validator.w3.org/nu/ ) your site needs to be publicly available and the machine running
this test needs to be able to access external service.

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)

## FAQ

No frequently asked questions yet :)
