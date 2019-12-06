-- MySQL dump --
-- ---------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
-- ---------------------------------------------------------

-- Dump data of "sites" ------------------------------------
INSERT INTO `sites`(`id`,`title`,`website`,`category`,`date_added`,`quota`,`public`,`rating_overall`,`rating_webstandard`,`rating_pagespeed`,`rating_usability`,`slug`,`date_modified`,`premium`,`rating_a11y`,`active`,`timeout`,`meta_keywords`,`public_sector`) VALUES 
( '1', 'Arvidsjaur', 'https://www.arvidsjaur.se', '2', '2018-07-09 23:20:22', '1', '1', '2.3', '2.1', '3.7', '1.0', 'arvidsjaur_se', '2019-12-06 19:55:44', '0', '2.0', '1', NULL, '', '1' ),
( '2', 'Bergs kommun', 'https://www.berg.se', '2', '2018-07-09 23:20:22', '1', '1', '2.8', '3.5', '3.0', '4.0', 'berg_se', '2019-12-06 19:55:44', '0', '1.5', '1', NULL, '', '1' ),
( '3', 'Bolagsverket', 'https://bolagsverket.se', '4', '2018-07-09 23:20:22', '1', '1', '3.5', '4.0', '4.0', '4.0', 'bolagsverket_se', '2019-12-06 19:55:44', '0', '3.0', '1', NULL, '', '1' ),
( '4', 'Bollebygd', 'https://bollebygd.se', '2', '2018-07-09 23:20:22', '1', '1', '2.8', '3.2', '3.3', '4.0', 'bollebygd_se', '2019-12-06 19:55:45', '0', '1.5', '1', NULL, '', '1' ),
( '5', 'Botkyrka', 'https://www.botkyrka.se', '2', '2018-07-09 23:20:22', '1', '1', '2.9', '4.0', '3.3', '1.0', 'botkyrka_se', '2019-12-06 19:55:45', '0', '2.0', '1', NULL, '', '1' );


-- Dump data of "categories" -------------------------------
INSERT INTO `categories`(`id`,`slug`,`title`,`description`,`rating_overall`,`rating_webstandard`,`rating_a11y`,`rating_usability`,`rating_pagespeed`,`cat_type`,`public`,`feat_img`,`feat_img_small`,`short_name`,`meta_long_name`,`meta_keywords`) VALUES 
( '1', 'politiska-partier', 'Politiska partier', 'De partier som sitter i Sveriges riksdag, får partistöd eller har representanter i Europa&shy;parlamentet, även de som haft representanter de två senaste EU-valen, samt de som i senaste landstingsvalet klarat treprocents&shy;spärren.', '2.5', '3.2', '1.4', '3.1', '2.8', '0', '1', '/static/upload/blog/kat-politiska-partier-(bildkredd-johannes-jansson).jpg', '/static/upload/blog/kat-politiska-partier-(bildkredd-johannes-jansson)-square.jpg', 'Politiska partier', '', '' ),
( '2', 'kommuner', 'Svenska kommuner', 'Alla Sveriges 290 kommuner, minus Gotland som istället redovisas som en region.', '2.7', '3.3', '1.9', '3.3', '2.8', '1', '1', '/static/upload/blog/kat-kommuner.jpg', '/static/upload/blog/kat-kommuner-square.jpg', 'Kommuner', '', '' ),
( '3', 'regioner', 'Sveriges regioner', 'Alla de regioner som finns i Sverige. Bedriver ofta vård, kollektivtrafik och regional utveckling.', '2.8', '3.3', '2.2', '3.1', '2.9', '1', '1', '/static/upload/blog/kat-regioner.jpg', '/static/upload/blog/kat-regioner-square.jpg', 'Regioner', '', '' ),
( '4', 'ovrig-offentlig-sektor', 'Övrig offentlig sektor', 'De myndigheter, nämnder, delegationer och andra verksamheter som finns inom svensk offentlig sektor.', '2.9', '3.0', '2.4', '3.4', '3.3', '1', '1', '/static/upload/blog/kat-ovrig-offentlig-sektor.jpg', '/static/upload/blog/kat-ovrig-offentlig-sektor-square.jpg', 'Övrig offentlig sektor', '', '' ),
( '5', 'off-sekt-webbtjanster', 'Offentlig sektors webbtjänster', 'Webbplatser som offentlig sektor tagit fram för att erbjuda medborgarna service på digital väg.', '3.1', '3.5', '2.4', '3.2', '3.4', '1', '1', '/static/upload/blog/kat-offsekt-tjanster.jpg', '/static/upload/blog/kat-offsekt-tjanster-square.jpg', 'Offentlig sektors webbtjänster', '', '' ),
( '6', 'medier', 'Medier', 'Medier har en viktig funktion i ett samhälle. De medier som 2017 fått mer än 100 kkr i distributionsstöd av Myndigheten för press radio och tv har kvalificerat sig till denna lista. Dessutom aktörer där offentlig sektor är avsändaren. Det vill säga att syftet är kommunikation framför journalistik.', '2.2', '2.5', '1.3', '3.6', '2.2', '2', '1', '/static/upload/blog/kat-medier.jpg', '/static/upload/blog/kat-medier-square.jpg', 'Medier', '', '' ),
( '7', 'halso-och-sjukvard', 'Offentligt finansierad hälso- och sjukvård', 'De organisationer vars verksamhet inom hälso- och sjukvård som finansieras via stat och landsting.', '2.8', '2.9', '2.4', '3.8', '3.2', '1', '1', '/static/upload/blog/kat-hos.jpg', '/static/upload/blog/kat-hos-square.jpg', 'Hälso- och sjukvård', '', '' ),
( '9', 'kultur', 'Kulturell verksamhet', 'Museér, operor och annan kulturell verksamhet av nationell eller regional angelägenhet.', '2.5', '3.1', '1.7', '3.1', '2.6', '0', '1', '/static/upload/blog/kat-kultur.jpg', '/static/upload/blog/kat-kultur-square.jpg', 'Kultur&shy;verksamhet', '', '' ),
( '10', 'patienter-organisationer', 'Patient&shy;organisationer', 'Patient&shy;föreningar och organisationer som bevakar individers rättigheter i samhället.', '2.7', '3.2', '1.8', '3.0', '2.7', '0', '1', '/static/upload/blog/kat-patientforeningar.jpg', '/static/upload/blog/kat-patientforeningar-square.jpg', 'Patient&shy;organisationer', '', 'patientorganisationer' ),
( '11', 'tankesmedjor', 'Tankesmedjor', 'Tankesmedjor är organisationer som jobbar med påverkan, att få samhället att förändras i en viss riktning, ofta politiska.', '2.7', '3.3', '1.8', '3.2', '2.4', '2', '1', '/static/upload/blog/kat-tankesmedjor.jpg', '/static/upload/blog/kat-tankesmedjor-square.jpg', 'Tankesmedjor', '', 'tankesmedja, tanke smedja' ),
( '12', 'insamlingsorg', 'Insamlings&shy;organisationer', 'De insamlings&shy;organisationer som ha ett 90-konto. Några listas istället bland patient&shy;organisationerna.', '2.4', '2.9', '1.6', '3.4', '2.5', '2', '1', '/static/upload/blog/kat-insamling.jpg', '/static/upload/blog/kat-insamling-square.jpg', 'Insamlings&shy;organisationer', '', 'insamlingsorganisationer' ),
( '13', 'fackforeningar', 'Fack&shy;föreningar', 'Fackliga och arbets&shy;rättsliga organisationer.', '2.6', '3.0', '1.7', '3.6', '2.7', '0', '1', '/static/upload/blog/kat-fackligt.jpg', '/static/upload/blog/kat-fackligt-square.jpg', 'Facken', '', 'fackförbund, fackligt, facken, fackföreningar' ),
( '14', 'utbildning-forskning', 'Utbildning och forskning', 'Högskolor, universitet,  institut och andra verksamheter som bedriver forskning, utbildning eller akademisk verksamhet. Även samverkans&shy;arenor likt science parks där minst en akademisk part är grundare.', '2.6', '3.1', '1.8', '3.6', '2.6', '0', '1', '/static/upload/blog/kat-hogskolor.jpg', '/static/upload/blog/kat-hogskolor-square.jpg', 'Utbildning och forskning', '', 'samverkansarenor, samverkansarena, högskola, högre studier' ),
( '15', 'webbyraer', 'Webbyråer och digitala konsulter', 'Specialiserade webbyråer eller digitala konsulter som till stor del bygger webbplatser. En kategori för att bedöma "skomakarens barn" bland de som bygger webb åt andra.', '2.8', '3.2', '1.8', '4.0', '2.9', '3', '1', '/static/upload/blog/kat-webbyraer.jpg', '/static/upload/blog/kat-webbyraer-square.jpg', 'IT-bolag och webbyråer', 'Hur bra är din webbyrå, digitala eller IT-konsult? Här jämför vi  varje månad hur mycket energi de lagt på sina egna webbplatser.', 'reklam byrå, reklambyrå, digitalbyrå, digital byrå' ),
( '16', 'digitalt-sverige', 'Övrigt viktigt för ett digitalt Sverige', 'Andra webbplatser och tjänster för ett fungerande digitalt samhälle.', '2.7', '3.3', '1.7', '3.2', '2.8', '0', '1', '/static/upload/blog/kat-andra-digitala.jpg', '/static/upload/blog/kat-andra-digitala-square.jpg', 'Övrigt digitalt', '', '' ),
( '17', 'olistade', 'Olistade webbplatser', 'Premium och övriga som inte vill synas.', '3.1', '3.5', '2.8', '3.5', '3.1', '2', '0', '/static/upload/blog/kat-olistade.jpg', '/static/upload/blog/kat-olistade-square.jpg', 'Olistade', '', '' ),
( '18', 'offentliga-bolag', 'Bolag ägda av offentlig sektor', 'Svensk offentlig sektor äger ett antal företag som är aktiebolag. Då svenska folket är ägare är de intressanta ifall de gör ett gott jobb med sin digitala kommunikation. Listar endast bolag där svenska staten eller offentlig sektor är den största ägaren.', '2.6', '3.1', '1.5', '3.3', '2.8', '2', '1', '/static/upload/blog/kat-bolag.jpg', '/static/upload/blog/kat-bolag-square.jpg', 'Bolag ägda av offentlig sektor', '', '' );
-- ---------------------------------------------------------


/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
-- ---------------------------------------------------------