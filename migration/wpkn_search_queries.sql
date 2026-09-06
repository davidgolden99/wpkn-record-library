-- ============================================================
-- WPKN 89.5 FM Record Library
-- MySQL Search Query Reference
-- ============================================================
-- Standard column order: CallNumber, Artist, Title, Genre, Style, ReleaseYear, Location
-- CallNumber = NULL for Digital (DM) records
-- Location = 'Digital' for DM records, 'Media - Section N' for physical
-- Status = 1 (Available), 8 (Unknown)
-- ============================================================


-- ============================================================
-- CORE SELECT BLOCK (reuse in all queries)
-- ============================================================
/*
    CASE 
        WHEN mt.Media = 'DM' THEN NULL
        ELSE CONCAT(mt.Media, '-', r.LibraryNumber)
    END AS CallNumber,
    r.Artist,
    r.Title,
    r.Genre,
    r.Style,
    r.ReleaseYear,
    CASE 
        WHEN mt.Media = 'DM' THEN 'Digital'
        ELSE CONCAT(mt.Media, ' - Section ', r.Section)
    END AS Location
FROM RecordLibrary r
JOIN MediaType mt ON r.MediaType = mt.ID
WHERE r.Status = 1
*/


-- ============================================================
-- 1. SEARCH BY ARTIST (partial match)
-- ============================================================
SELECT 
    CASE 
        WHEN mt.Media = 'DM' THEN NULL
        ELSE CONCAT(mt.Media, '-', r.LibraryNumber)
    END AS CallNumber,
    r.Artist,
    r.Title,
    r.Genre,
    r.Style,
    r.ReleaseYear,
    CASE 
        WHEN mt.Media = 'DM' THEN 'Digital'
        ELSE CONCAT(mt.Media, ' - Section ', r.Section)
    END AS Location
FROM RecordLibrary r
JOIN MediaType mt ON r.MediaType = mt.ID
WHERE r.Status = 1
AND r.Artist LIKE '%Ellington%'
ORDER BY r.Artist, r.LibraryNumber;


-- ============================================================
-- 2. SEARCH BY ARTIST (two artists, AND)
-- ============================================================
SELECT 
    CASE 
        WHEN mt.Media = 'DM' THEN NULL
        ELSE CONCAT(mt.Media, '-', r.LibraryNumber)
    END AS CallNumber,
    r.Artist,
    r.Title,
    r.Genre,
    r.Style,
    r.ReleaseYear,
    CASE 
        WHEN mt.Media = 'DM' THEN 'Digital'
        ELSE CONCAT(mt.Media, ' - Section ', r.Section)
    END AS Location
FROM RecordLibrary r
JOIN MediaType mt ON r.MediaType = mt.ID
WHERE r.Status = 1
AND (r.Artist LIKE '%Duke%' AND r.Artist LIKE '%Ellington%')
ORDER BY r.Artist, r.LibraryNumber;


-- ============================================================
-- 3. SEARCH BY ARTIST (two artists, OR)
-- ============================================================
SELECT 
    CASE 
        WHEN mt.Media = 'DM' THEN NULL
        ELSE CONCAT(mt.Media, '-', r.LibraryNumber)
    END AS CallNumber,
    r.Artist,
    r.Title,
    r.Genre,
    r.Style,
    r.ReleaseYear,
    CASE 
        WHEN mt.Media = 'DM' THEN 'Digital'
        ELSE CONCAT(mt.Media, ' - Section ', r.Section)
    END AS Location
FROM RecordLibrary r
JOIN MediaType mt ON r.MediaType = mt.ID
WHERE r.Status = 1
AND (r.Artist LIKE '%Ellington%' OR r.Artist LIKE '%Coltrane%')
ORDER BY r.Artist, r.LibraryNumber;


-- ============================================================
-- 4. SEARCH BY TITLE (partial match)
-- ============================================================
SELECT 
    CASE 
        WHEN mt.Media = 'DM' THEN NULL
        ELSE CONCAT(mt.Media, '-', r.LibraryNumber)
    END AS CallNumber,
    r.Artist,
    r.Title,
    r.Genre,
    r.Style,
    r.ReleaseYear,
    CASE 
        WHEN mt.Media = 'DM' THEN 'Digital'
        ELSE CONCAT(mt.Media, ' - Section ', r.Section)
    END AS Location
FROM RecordLibrary r
JOIN MediaType mt ON r.MediaType = mt.ID
WHERE r.Status = 1
AND r.Title LIKE '%Kind of Blue%'
ORDER BY r.Artist, r.LibraryNumber;


-- ============================================================
-- 5. SEARCH BY GENRE (exact match)
-- ============================================================
SELECT 
    CASE 
        WHEN mt.Media = 'DM' THEN NULL
        ELSE CONCAT(mt.Media, '-', r.LibraryNumber)
    END AS CallNumber,
    r.Artist,
    r.Title,
    r.Genre,
    r.Style,
    r.ReleaseYear,
    CASE 
        WHEN mt.Media = 'DM' THEN 'Digital'
        ELSE CONCAT(mt.Media, ' - Section ', r.Section)
    END AS Location
FROM RecordLibrary r
JOIN MediaType mt ON r.MediaType = mt.ID
WHERE r.Status = 1
AND r.Genre = 'Jazz'
ORDER BY r.Artist, r.LibraryNumber
LIMIT 200;


-- ============================================================
-- 6. SEARCH BY STYLE (partial match)
-- ============================================================
SELECT 
    CASE 
        WHEN mt.Media = 'DM' THEN NULL
        ELSE CONCAT(mt.Media, '-', r.LibraryNumber)
    END AS CallNumber,
    r.Artist,
    r.Title,
    r.Genre,
    r.Style,
    r.ReleaseYear,
    CASE 
        WHEN mt.Media = 'DM' THEN 'Digital'
        ELSE CONCAT(mt.Media, ' - Section ', r.Section)
    END AS Location
FROM RecordLibrary r
JOIN MediaType mt ON r.MediaType = mt.ID
WHERE r.Status = 1
AND r.Style LIKE '%Jamband%'
ORDER BY r.Artist, r.LibraryNumber;


-- ============================================================
-- 7. LOCAL ARTISTS (Comments LIKE '%Local%')
-- ============================================================
SELECT 
    CASE 
        WHEN mt.Media = 'DM' THEN NULL
        ELSE CONCAT(mt.Media, '-', r.LibraryNumber)
    END AS CallNumber,
    r.Artist,
    r.Title,
    r.Genre,
    r.Style,
    r.ReleaseYear,
    CASE 
        WHEN mt.Media = 'DM' THEN 'Digital'
        ELSE CONCAT(mt.Media, ' - Section ', r.Section)
    END AS Location
FROM RecordLibrary r
JOIN MediaType mt ON r.MediaType = mt.ID
WHERE r.Status = 1
AND r.Comments LIKE '%Local%'
ORDER BY r.Artist, r.LibraryNumber;


-- ============================================================
-- 8. COMBINED SEARCH (Artist + Genre + Style)
-- ============================================================
SELECT 
    CASE 
        WHEN mt.Media = 'DM' THEN NULL
        ELSE CONCAT(mt.Media, '-', r.LibraryNumber)
    END AS CallNumber,
    r.Artist,
    r.Title,
    r.Genre,
    r.Style,
    r.ReleaseYear,
    CASE 
        WHEN mt.Media = 'DM' THEN 'Digital'
        ELSE CONCAT(mt.Media, ' - Section ', r.Section)
    END AS Location
FROM RecordLibrary r
JOIN MediaType mt ON r.MediaType = mt.ID
WHERE r.Status = 1
AND r.Artist LIKE '%Metheny%'
AND r.Genre = 'Jazz'
ORDER BY r.Artist, r.LibraryNumber;


-- ============================================================
-- 9. LABEL RESEARCH (Artist + Label + Year)
-- ============================================================
SELECT 
    CASE 
        WHEN mt.Media = 'DM' THEN NULL
        ELSE CONCAT(mt.Media, '-', r.LibraryNumber)
    END AS CallNumber,
    r.Artist,
    r.Title,
    r.Label,
    r.ReleaseYear,
    CASE 
        WHEN mt.Media = 'DM' THEN 'Digital'
        ELSE CONCAT(mt.Media, ' - Section ', r.Section)
    END AS Location
FROM RecordLibrary r
JOIN MediaType mt ON r.MediaType = mt.ID
WHERE r.Status = 1
AND r.Artist LIKE '%Metheny%'
ORDER BY r.Artist, r.LibraryNumber;


-- ============================================================
-- 10. DIGITAL COLLECTION ONLY
-- ============================================================
SELECT 
    r.LibraryNumber,
    r.Artist,
    r.Title,
    r.Genre,
    r.Style,
    r.ReleaseYear,
    r.Comments
FROM RecordLibrary r
WHERE r.Status = 1
AND r.MediaType = 4
ORDER BY r.Artist, r.LibraryNumber
LIMIT 200;


-- ============================================================
-- 11. SECTION INVENTORY (physical media only)
-- ============================================================
SELECT 
    CONCAT(mt.Media, '-', r.LibraryNumber) AS CallNumber,
    r.Artist,
    r.Title,
    r.Genre,
    r.Style,
    r.ReleaseYear,
    CONCAT(mt.Media, ' - Section ', r.Section) AS Location
FROM RecordLibrary r
JOIN MediaType mt ON r.MediaType = mt.ID
WHERE r.Status = 1
AND r.MediaType IN (1, 2)
AND r.Section = 20
ORDER BY mt.MediaType, r.LibraryNumber;


-- ============================================================
-- 12. GENRE COUNTS (inventory summary)
-- ============================================================
SELECT 
    r.Genre,
    mt.Media,
    COUNT(*) AS RecordCount
FROM RecordLibrary r
JOIN MediaType mt ON r.MediaType = mt.ID
WHERE r.Status = 1
AND r.Genre IS NOT NULL
GROUP BY r.Genre, mt.Media
ORDER BY r.Genre, mt.Media;


-- ============================================================
-- 13. NEEDS REVIEW QUEUE
-- ============================================================
SELECT 
    CONCAT(mt.Media, '-', r.LibraryNumber) AS CallNumber,
    r.Artist,
    r.Title,
    r.Genre,
    r.Style,
    r.Comments
FROM RecordLibrary r
JOIN MediaType mt ON r.MediaType = mt.ID
WHERE r.NeedsReview = 1
AND r.Status IN (1, 8)
ORDER BY r.Genre, r.Artist;
