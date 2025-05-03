# Translation

Following is copied from slack community threads.
Right now the info is only in swedish.


All hjälp med att skriva texter mottages tacksamt :smiley: 

Ingen kodkunskap behövs, allt kan göras direkt i webbläsaren på GitHub :slightly_smiling_face: 

Följande filer behöver uppdateras:
 404 Test (engelska) https://github.com/Webperf-se/webperf_core/blob/main/locales%2Fen%2FLC_MESSAGES%2F404.po
 A11y Statement Test (engelska) https://github.com/Webperf-se/webperf_core/blob/main/locales%2Fen%2FLC_MESSAGES%2Fa11y-statement.po
 CSS Test https://github.com/Webperf-se/webperf_core/blob/main/locales%2Fen%2FLC_MESSAGES%2Fcss.po
 HTML Test (engelska)  https://github.com/Webperf-se/webperf_core/blob/main/locales%2Fen%2FLC_MESSAGES%2Fhtml.po
 Javascript Test https://github.com/Webperf-se/webperf_core/blob/main/locales%2Fen%2FLC_MESSAGES%2Fjavascript.po
 Lighthouse Test https://github.com/Webperf-se/webperf_core/blob/main/locales%2Fen%2FLC_MESSAGES%2Flighthouse.po

I denna tråd kommer jag berätta för varje text hur ni tar reda på vilken text som bör vara där.

Generellt för alla .po filer gäller:
Texterna i varje fil ovan fungerar på följande sätt.
Det finns en text för avklarade regler (resolved) och en text för regler som fortfarande behöver åtgärdas (unresolved).
Det är texten mellan de två " på varje rad som börjar med msgstr som behöver få en mer lättförståelig text.

På rader där texten i msgstr börjar med samma text som msgid är helt oöversatta.

Första delen i msgid innan mellanrum (på bild två inringat med grönt) är regel id, detta är bra att ha koll på för att få mer info om vilken text som är vettig att skriva. Mer om det i text specifikt för varje fil.

Generellt för alla tester är att de har språkstöd, vi börjar men engelska men sedan skulle de även behöva översättas till svenska.
Det som skiljer de engelska och svenska filerna är att de ligger i olika kataloger.
en för engelska och sv för svenska.

För CSS Test kan ni få reda på mer om reglen genom att gå till stylelint på följande adress:
            https://stylelint.io/user-guide/rules/{rule-id}

Ersätt {rule-id} med den regel id ni vill få mer information om.

Tex: 
För unit-no-unkown är adressen:
https://stylelint.io/user-guide/rules/unit-no-unkown