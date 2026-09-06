-- WPKN Record Library — MySQL schema
-- Table definitions only, no data. Extracted from a mysqldump of `wpkn_library`
-- (2026-09-04) with all `-- Dumping data for table ...` sections and
-- server-instance-specific GTID state removed.
--
-- The `Users` table is also created at runtime by app.py's init_db() if it
-- doesn't exist, with the same definition as below.

SET NAMES utf8mb4;

--
-- Table structure for table `Genre`
--

DROP TABLE IF EXISTS `Genre`;
CREATE TABLE `Genre` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `Genre` varchar(50) NOT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `MediaType`
--

DROP TABLE IF EXISTS `MediaType`;
CREATE TABLE `MediaType` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `Media` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `RecordLibrary`
--

DROP TABLE IF EXISTS `RecordLibrary`;
CREATE TABLE `RecordLibrary` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `LibraryNumber` int DEFAULT NULL,
  `MediaType` int DEFAULT NULL,
  `Status` int DEFAULT NULL,
  `Artist` varchar(255) DEFAULT NULL,
  `Title` varchar(255) DEFAULT NULL,
  `Genre` varchar(50) DEFAULT NULL,
  `Style` varchar(255) DEFAULT NULL,
  `ReleaseYear` int DEFAULT NULL,
  `ReleaseDate` date DEFAULT NULL,
  `Label` varchar(100) DEFAULT NULL,
  `Comments` varchar(255) DEFAULT NULL,
  `Section` int DEFAULT NULL,
  `NeedsReview` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`ID`),
  KEY `MediaType` (`MediaType`),
  KEY `Status` (`Status`),
  CONSTRAINT `recordlibrary_ibfk_1` FOREIGN KEY (`MediaType`) REFERENCES `MediaType` (`ID`),
  CONSTRAINT `recordlibrary_ibfk_2` FOREIGN KEY (`Status`) REFERENCES `Status` (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `Sections`
--

DROP TABLE IF EXISTS `Sections`;
CREATE TABLE `Sections` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `Section` varchar(50) DEFAULT NULL,
  `Location` varchar(100) DEFAULT NULL,
  `RangeStart` int DEFAULT NULL,
  `RangeEnd` int DEFAULT NULL,
  `MediaType` int DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `Status`
--

DROP TABLE IF EXISTS `Status`;
CREATE TABLE `Status` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `Status` varchar(50) NOT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `Users`
--

DROP TABLE IF EXISTS `Users`;
CREATE TABLE `Users` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `Username` varchar(50) NOT NULL,
  `PasswordHash` varchar(255) NOT NULL,
  `Role` enum('Admin','Librarian','Entry') NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `Username` (`Username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
