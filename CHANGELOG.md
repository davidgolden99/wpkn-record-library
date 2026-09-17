# Changelog

All notable changes to this project are documented here.

## [v1.3] - unreleased

Batched for the programmer-feedback window; target deploy ~2026-09-20.

### Added
- Edit page: by-artist lookup for records that can't be found by Library
  Number. Choosing **DM** in the "Media Type" box swaps the Library Number
  field for an **Artist** field; the search runs `Artist LIKE` across all
  media types (so mis-coded records surface too) and returns a pick-list
  with an Edit button per row. Previously DM records — which show a blank
  Library Number — and any record with a NULL `LibraryNumber` were
  unreachable for editing.
- Add Record form now auto-derives `Section` on insert from `MediaType` +
  `LibraryNumber` via the `Sections` range table, instead of leaving it
  blank. No new field on the form — kept intentionally minimal.
- New **Restore Deleted** screen (`/restore`): finds a record with
  `Status = Deleted` (by Library Number, or by Artist for DM/no-number
  records) and offers exactly one action — restore it to `Available`.
  Nothing else about the record is editable there.
- New dedicated **Restore** role: a user with this role can reach only
  `/restore` (plus public Search) — not Add Record, Edit, Bulk Edit, or
  Admin — so restore-only access can be granted without bundling in the
  ability to add or edit records. Existing `Entry` accounts also keep
  access to `/restore`.
- Bulk Edit: new **Refresh Section Data (CD)** button. Fills in `Section`
  for `Available` CD records whose `Section` is currently blank, using the
  same `Sections` range-match as Add Record. Never overwrites a `Section`
  that's already set, never touches LP/DM/DV, and never touches non-
  `Available` records.

### Fixed
- Edit page: the read-only Library Number box rendered the literal string
  "None" for records with no `LibraryNumber` (all DM records); now blank.
- Search page and the new Restore Deleted page showed a "Data Entry" nav
  link to every logged-in user regardless of role, which 403'd for
  `Restore`-role users; now shown only to roles that can actually use it.

### Deploy notes
- **Required before this version's `Restore` role can be assigned to
  anyone:** `Users.Role` is a MySQL `ENUM`, not free text. Run on the
  server's `wpkn_library` database before or immediately after deploying:
  ```sql
  ALTER TABLE Users MODIFY Role ENUM('Admin','Librarian','Entry','Restore') NOT NULL;
  ```
  `init_db()` only runs `CREATE TABLE IF NOT EXISTS`, so it will not alter
  the existing production table on its own.

## [v1.2] - 2026-09-06

### Added
- MySQL schema (`migration/schema.sql`) — `CREATE TABLE` statements only, no
  data. Previously the repo had no schema representation at all except
  `Users` (defined inline in `app.py`'s `init_db()`).
- `deploy.sh` and a documented deploy workflow (see README). The server now
  runs from a git clone of this repo at `/opt/wpkn-record-library/` on the
  rack server; deploying is `git pull` + service restart via one script.
  Manual/pull-based by design — no CI, no auto-deploy.

## [v1.1] - 2026-09-06

### Changed
- Synced `app.py` with what was actually running in production, which had
  diverged from `v1.0`: added a `python-dotenv` import/`load_dotenv()` call,
  and changed `get_db()`'s fallback default user from `root` to `wpkn_app`.
- Fixed the production systemd unit (on the server, not tracked in this
  repo) to set the correctly-named `WPKN_DB_HOST`/`WPKN_DB_USER`/
  `WPKN_DB_PASSWORD`/`WPKN_DB_NAME` environment variables instead of
  `MYSQL_PASSWORD`, which the app never actually read.

### Security
- Removed the real `wpkn_app` MySQL password, which was hardcoded as a
  fallback default in the deployed `app.py`, replacing it with a
  placeholder before committing.

## [v1.0] - 2026-09-06

### Added
- Initial commit: the Flask app (search, login, data entry, edit, bulk
  edit, admin) and migration tooling (`clean_recordlibrary.py`,
  `wpkn_search_queries.sql`), as originally deployed to
  `library.wpkn.org` on 2026-09-04.

### Security
- Redacted two real secrets found in the source before publishing: the
  `wpkn_app` MySQL password (hardcoded in
  `wpkn_flask/db_env_vars_readme.txt`) and the local MySQL root password
  used for development (hardcoded as `get_db()`'s fallback default).

### Known issue
- The `Entry` account's seed password remains in plaintext in `app.py`
  and was still that account's live production password as of this
  release — left in deliberately (not a miss) pending a move to
  per-user Entry accounts instead of rotating the shared one.
