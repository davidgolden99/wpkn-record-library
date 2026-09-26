-- v1.4.1: retire MediaType DV. Run by hand on prod (sudo mysql wpkn_library)
-- alongside deploy.sh. Idempotent.
-- The MediaType row itself is kept on purpose: every read query INNER JOINs to
-- MediaType, so deleting it would make these rows vanish from Edit/Restore too.
UPDATE RecordLibrary SET Status = 5 WHERE MediaType = 3;
SELECT Status, COUNT(*) FROM RecordLibrary WHERE MediaType = 3 GROUP BY Status;  -- expect 5 | 109
