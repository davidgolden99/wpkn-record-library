-- Assign a batch of genre-less records to one genre volunteer.
-- Edit the two SET lines, then run:  sudo mysql wpkn_library < assign_genre_batch.sql
-- Read-only against RecordLibrary; only inserts into genre_staging.
--
-- Picks Available CDs with no genre whose artist has no other record with a
-- genre anywhere in the catalog -- the planned same-artist fill-in (Phase 3a)
-- could never answer these, so no volunteer effort is wasted. Skips anything
-- already assigned to someone. Sorted by artist so one decision covers every
-- album by that artist.

SET @volunteer  = 'CHANGE_ME';   -- must match the volunteer's Username exactly
SET @batch_size = 250;

-- Refuse to run with a username that doesn't exist.
SELECT IF(COUNT(*) = 1, 'OK: user exists', 'STOP: no such user, nothing assigned') AS check_user
FROM Users WHERE Username = @volunteer;

SET @sql = '
INSERT INTO genre_staging (record_id, artist, title, label, year, media, current_genre, assigned_to)
SELECT r.ID, r.Artist, r.Title, r.Label, r.ReleaseYear, mt.Media, r.Genre, ?
FROM RecordLibrary r
JOIN MediaType mt ON mt.ID = r.MediaType
LEFT JOIN (SELECT DISTINCT Artist FROM RecordLibrary
           WHERE Genre IS NOT NULL AND Genre <> '''') g ON g.Artist = r.Artist
LEFT JOIN genre_staging s ON s.record_id = r.ID
WHERE r.Status = 1
  AND r.MediaType = 1
  AND (r.Genre IS NULL OR r.Genre = '''')
  AND g.Artist IS NULL
  AND s.record_id IS NULL
  AND (SELECT COUNT(*) FROM Users WHERE Username = ?) = 1
ORDER BY r.Artist, r.Title, r.ID
LIMIT ?';
PREPARE stmt FROM @sql;
EXECUTE stmt USING @volunteer, @volunteer, @batch_size;
DEALLOCATE PREPARE stmt;

SELECT assigned_to, status, COUNT(*) AS rows_assigned
FROM genre_staging WHERE assigned_to = @volunteer GROUP BY assigned_to, status;
