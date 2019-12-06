-- MySQL dump --
-- ---------------------------------------------------------


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
-- ---------------------------------------------------------

-- CREATE DATABASE "webperfs_wperf" ------------------------
CREATE DATABASE IF NOT EXISTS `webperfs_wperf` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `webperfs_wperf`;
-- ---------------------------------------------------------


-- CREATE TABLE "categories" -----------------------------------
CREATE TABLE `categories` ( 
	`id` Int( 255 ) AUTO_INCREMENT NOT NULL,
	`slug` TinyText CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
	`title` TinyText CHARACTER SET utf8mb4 COLLATE utf8mb4_swedish_ci NOT NULL,
	`description` Text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
	`rating_overall` Decimal( 2, 1 ) NOT NULL DEFAULT -1.0,
	`rating_webstandard` Decimal( 2, 1 ) NOT NULL DEFAULT -1.0,
	`rating_a11y` Decimal( 2, 1 ) NULL DEFAULT -1.0,
	`rating_usability` Decimal( 2, 1 ) NULL DEFAULT -1.0,
	`rating_pagespeed` Decimal( 2, 1 ) NULL DEFAULT -1.0,
	`cat_type` TinyInt( 5 ) NOT NULL DEFAULT 0 COMMENT '1 är offsekt, 0 demokrati, 2 = andra',
	`public` TinyInt( 1 ) NOT NULL DEFAULT 1,
	`feat_img` VarChar( 200 ) CHARACTER SET utf8mb4 COLLATE utf8mb4_swedish_ci NULL,
	`feat_img_small` VarChar( 200 ) CHARACTER SET utf8mb4 COLLATE utf8mb4_swedish_ci NULL,
	`short_name` VarChar( 100 ) CHARACTER SET utf8mb4 COLLATE utf8mb4_swedish_ci NOT NULL,
	`meta_long_name` VarChar( 200 ) CHARACTER SET utf8mb4 COLLATE utf8mb4_swedish_ci NOT NULL,
	`meta_keywords` Text CHARACTER SET utf8mb4 COLLATE utf8mb4_swedish_ci NOT NULL,
	PRIMARY KEY ( `id` ) )
CHARACTER SET = utf8mb4
COLLATE = utf8mb4_swedish_ci
ENGINE = InnoDB
AUTO_INCREMENT = 1;
-- -------------------------------------------------------------

-- CREATE TABLE "sites" ----------------------------------------
CREATE TABLE `sites` ( 
	`id` Int( 255 ) AUTO_INCREMENT NOT NULL,
	`title` TinyText CHARACTER SET utf8mb4 COLLATE utf8mb4_swedish_ci NOT NULL,
	`website` VarChar( 250 ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
	`category` Int( 11 ) NOT NULL DEFAULT 12,
	`date_added` DateTime NOT NULL DEFAULT CURRENT_TIMESTAMP,
	`quota` Smallint( 6 ) NOT NULL DEFAULT 1,
	`public` Smallint( 255 ) NOT NULL DEFAULT 1,
	`rating_overall` Decimal( 2, 1 ) NOT NULL DEFAULT -1.0,
	`rating_webstandard` Decimal( 2, 1 ) NOT NULL DEFAULT -1.0,
	`rating_pagespeed` Decimal( 2, 1 ) NOT NULL DEFAULT -1.0,
	`rating_usability` Decimal( 2, 1 ) NOT NULL DEFAULT -1.0,
	`slug` VarChar( 120 ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
	`date_modified` DateTime NULL DEFAULT CURRENT_TIMESTAMP,
	`premium` Smallint( 8 ) NOT NULL DEFAULT 0 COMMENT 'Har de konto och fått premium-funktioner?',
	`rating_a11y` Decimal( 2, 1 ) NOT NULL DEFAULT -1.0,
	`active` TinyInt( 8 ) NOT NULL DEFAULT 1,
	`timeout` Timestamp NULL COMMENT 'Om sajten strular sätts ett datum för timeout, testas igen senare om någon timme',
	`meta_keywords` Text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
	`public_sector` TinyInt( 4 ) NOT NULL DEFAULT 0 COMMENT '1 om webbplatsen är offsekt',
	PRIMARY KEY ( `id` ),
	CONSTRAINT `slug` UNIQUE( `slug` ),
	CONSTRAINT `unique_id` UNIQUE( `id` ) )
CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci
ENGINE = InnoDB
AUTO_INCREMENT = 1;
-- -------------------------------------------------------------


-- CREATE TABLE "sitetests" ------------------------------------
CREATE TABLE `sitetests` ( 
	`id` Int( 255 ) AUTO_INCREMENT NOT NULL,
	`test_date` DateTime NOT NULL DEFAULT CURRENT_TIMESTAMP,
	`type_of_test` Int( 11 ) NOT NULL DEFAULT 0,
	`pages_checked` Int( 255 ) NOT NULL DEFAULT -1,
	`check_report` Text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
	`json_check_data` Text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
	`site_id` Int( 11 ) NOT NULL,
	`rating` Decimal( 2, 1 ) NULL,
	`most_recent` TinyInt( 1 ) NOT NULL DEFAULT 1 COMMENT '1 om det är det senaste testet av sitt slag för webbplatsen',
	PRIMARY KEY ( `id` ),
	CONSTRAINT `unique_id` UNIQUE( `id` ) )
CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci
ENGINE = InnoDB
AUTO_INCREMENT = 1;
-- -------------------------------------------------------------

-- CREATE INDEX "index_category" -------------------------------
CREATE INDEX `index_category` USING BTREE ON `sites`( `category` );
-- -------------------------------------------------------------


-- CREATE INDEX "index_date_modified" --------------------------
CREATE INDEX `index_date_modified` USING BTREE ON `sites`( `date_modified` );
-- -------------------------------------------------------------


-- CREATE INDEX "index_public" ---------------------------------
CREATE INDEX `index_public` USING BTREE ON `sites`( `public` );
-- -------------------------------------------------------------


-- CREATE INDEX "index_rating" ---------------------------------
CREATE INDEX `index_rating` USING BTREE ON `sites`( `rating_overall` );
-- -------------------------------------------------------------


-- CREATE INDEX "index_rating_pagespeed" -----------------------
CREATE INDEX `index_rating_pagespeed` USING BTREE ON `sites`( `rating_pagespeed` );
-- -------------------------------------------------------------


-- CREATE INDEX "index_rating_usability" -----------------------
CREATE INDEX `index_rating_usability` USING BTREE ON `sites`( `rating_usability` );
-- -------------------------------------------------------------


-- CREATE INDEX "index_slug" -----------------------------------
CREATE INDEX `index_slug` USING BTREE ON `sites`( `slug` );
-- -------------------------------------------------------------


-- CREATE INDEX "index_test_date" ------------------------------
CREATE INDEX `index_test_date` USING BTREE ON `sitetests`( `test_date` );
-- -------------------------------------------------------------


-- CREATE INDEX "index_type_of_test" ---------------------------
CREATE INDEX `index_type_of_test` USING BTREE ON `sitetests`( `type_of_test` );
-- -------------------------------------------------------------


-- CREATE INDEX "lnk_sites_sitetest" ---------------------------
CREATE INDEX `lnk_sites_sitetest` USING BTREE ON `sitetests`( `site_id` );
-- -------------------------------------------------------------


-- CREATE INDEX "most_recent" ----------------------------------
CREATE INDEX `most_recent` USING BTREE ON `sitetests`( `most_recent` );
-- -------------------------------------------------------------

-- CREATE LINK "lnk_sites_sitetest" ----------------------------
ALTER TABLE `sitetests`
	ADD CONSTRAINT `lnk_sites_sitetest` FOREIGN KEY ( `site_id` )
	REFERENCES `sites`( `id` )
	ON DELETE Cascade
	ON UPDATE No Action;
-- -------------------------------------------------------------

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
-- ---------------------------------------------------------