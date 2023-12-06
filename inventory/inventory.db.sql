BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "LocationList" (
	"LocationID"	integer,
	"Location"	TEXT NOT NULL,
	PRIMARY KEY("LocationID")
);
CREATE TABLE IF NOT EXISTS "CategoryList" (
	"CategoryID"	integer,
	"Category"	TEXT NOT NULL,
	PRIMARY KEY("CategoryID")
);
CREATE TABLE IF NOT EXISTS "ItemList" (
	"ID"	integer,
	"ItemID"	INT NOT NULL,
	"date_created"	Date,
	PRIMARY KEY("ID")
);
CREATE TABLE IF NOT EXISTS "BrandList" (
	"BrandID"	INTEGER,
	"Brand"	TEXT,
	PRIMARY KEY("BrandID")
);
CREATE TABLE IF NOT EXISTS "ImageList" (
	"ID"	INTEGER,
	"FileName"	TEXT,
	"ThumbnailName"	TEXT,
	"ItemID"	INTEGER,
	PRIMARY KEY("ID")
);
CREATE TABLE IF NOT EXISTS "ItemDetails" (
	"ItemID"	integer,
	"Description"	TEXT NOT NULL,
	"LocationID"	INT,
	"CategoryID"	INT,
	"BrandID"	INTEGER,
	"SerialNumber"	TEXT,
	"Warranty"	TEXT,
	"PurchaseDate"	TEXT,
	"Archived"	INTEGER,
	"Notes"	TEXT,
	"Accessories"	TEXT,
	"CreatedDate"	TEXT,
	"ModifiedDate"	TEXT,
	"Value"	REAL,
	PRIMARY KEY("ItemID")
);

INSERT INTO CategoryList (Category) VALUES ('Not Assigned');
INSERT INTO CategoryList (Category) VALUES ('Electronics');
INSERT INTO CategoryList (Category) VALUES ('Jewerly');
INSERT INTO CategoryList (Category) VALUES ('Tools');
INSERT INTO CategoryList (Category) VALUES ('Furniture');

INSERT INTO LocationList (Location) VALUES ('Not Assigned');
INSERT INTO LocationList (Location) VALUES ('Kitchen');
INSERT INTO LocationList (Location) VALUES ('Living Room');
INSERT INTO LocationList (Location) VALUES ('Bedroom');

INSERT INTO BrandList (Brand) VALUES ('Not Assigned');
COMMIT;
