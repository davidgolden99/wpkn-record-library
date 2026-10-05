-- v1.5: genre review page. Run by hand on prod (sudo mysql wpkn_library)
-- alongside deploy.sh. Safe to re-run.

-- 1. New narrow role for genre volunteers. init_db() only CREATEs, so an
--    existing Users table has to be altered by hand (same as Restore in v1.3).
ALTER TABLE Users MODIFY Role ENUM('Admin','Librarian','Entry','Restore','Genre') NOT NULL;

-- 2. One row per record handed to a volunteer. Reference columns are a
--    snapshot taken at assignment time; volunteers only ever write
--    proposed_genre / confidence / notes. Kept permanently as the audit log of
--    who proposed and who approved each genre.
CREATE TABLE IF NOT EXISTS genre_staging (
    record_id      INT          NOT NULL PRIMARY KEY,
    artist         VARCHAR(255),
    title          VARCHAR(255),
    label          VARCHAR(100),
    year           INT,
    media          VARCHAR(10),
    current_genre  VARCHAR(50),
    assigned_to    VARCHAR(50)  NOT NULL,
    assigned_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    proposed_genre VARCHAR(50),
    confidence     ENUM('High','Medium','Low'),
    notes          VARCHAR(500),
    status         ENUM('open','proposed','approved','rejected','skipped') NOT NULL DEFAULT 'open',
    edited_by      VARCHAR(50),
    edited_at      DATETIME,
    final_genre    VARCHAR(50),
    reviewed_by    VARCHAR(50),
    reviewed_at    DATETIME,
    notes_cleared_by VARCHAR(50),   -- Librarian marked the note as dealt with;
    notes_cleared_at DATETIME,      -- the note text itself is never erased
    KEY idx_gs_assigned (assigned_to, status),
    KEY idx_gs_status (status),
    CONSTRAINT fk_gs_record FOREIGN KEY (record_id) REFERENCES RecordLibrary (ID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 3. notes_cleared_by / notes_cleared_at came after the table was first
--    created, so CREATE TABLE IF NOT EXISTS above skips them on a database
--    that already has genre_staging. MySQL has no ADD COLUMN IF NOT EXISTS,
--    so check information_schema and only ALTER when the columns are missing.
SET @has_cleared = (SELECT COUNT(*) FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'genre_staging'
                      AND COLUMN_NAME = 'notes_cleared_at');
SET @sql = IF(@has_cleared = 0,
    'ALTER TABLE genre_staging ADD COLUMN notes_cleared_by VARCHAR(50) AFTER reviewed_at,
                               ADD COLUMN notes_cleared_at DATETIME AFTER notes_cleared_by',
    'DO 0');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SHOW CREATE TABLE Users;
SELECT COUNT(*) AS genre_staging_rows FROM genre_staging;
