# Changelog

All notable changes to this project are documented here.

## [v1.5] - unreleased

### Added
- **Genre review, built into the app instead of NocoDB.** This is Phase 3b of the data cleansing plan.
  - **My Genre List (`/genres`)** is for volunteers with the new **Genre** role. It shows their own assigned batch, sorted by artist, with a "Look it up" link (Discogs search) per row. Each row has Suggested genre (41 approved genres only), Confidence (High/Medium/Low), and Notes. Rows **save automatically** as they're changed; there's no Save button, matching `genre_reviewer_guide.md`. An "N of M done" counter counts a row as done only once a genre is chosen; a note without a genre stays open. The server checks that the genre is approved and the row belongs to that volunteer. Reviewed rows are locked.
  - **Genre Review (`/genres/review`)** is for Librarian/Admin. It shows a per-volunteer progress summary and the suggestions waiting for review. Each can be approved, changed then approved, or rejected, and there's a bulk "Approve all High confidence" button, optionally for one volunteer. Approving writes `RecordLibrary.Genre` (and clears `NeedsReview`) **only if the record's Genre is still blank**. Otherwise the suggestion is marked `skipped`, so nothing is ever overwritten.
  - `genre_staging` is kept permanently as the audit log: who proposed what and when, and who approved which final genre.
  - New **Genre** role: it can reach only My Genre List, Search, and New Releases. It's added to Admin's role dropdowns.
  - `migration/assign_genre_batch.sql` assigns a batch to one volunteer. Set the username and batch size, then run it. It picks Available CDs with no genre whose artist has no other record with a genre, so the planned same-artist fill-in could never answer them. It skips anything already assigned, sorts by artist, and refuses unknown usernames.

### Fixed
- Search and New Releases showed a **Restore Deleted** link to every logged-in user. Now only roles that can use it see it, which matters now that Genre volunteers can log in.

### Data
- `migration/v1.5_genre_review.sql` adds `'Genre'` to `Users.Role` and creates `genre_staging`. Run it by hand on prod with this deploy, **before** anyone opens Genre Review.

## [v1.4.1] - 2026-09-26

### Changed
- **Restore Deleted** screen can now correct **Label** and **Release Year** while restoring, and **requires an approved Genre** (from the `Genre` table) before a record can go back to Available. Blank and off-list values are both rejected, checked on the server as well as in the browser, and a rejected save keeps what was typed. Restores are picked by someone with thorough musical knowledge, so this makes every restored record come back with a real genre instead of adding to the catalog's blank-genre backlog. A Deleted record whose old Genre isn't on the list (216 CDs on local dev, e.g. "Texas Swing, Jazz", "VOCAL") shows that value for reference. On restore it's copied into **Style**, added after any existing Style text with "; " (14 of the 216 already have a Style), so the detail isn't lost. Everything else stays read-only.
- **MediaType DV retired.** WPKN has no DV items and won't be adding any. DV no longer appears in the Add Record, Edit, Restore, or New Releases dropdowns (`get_media_types()` filters it out). The `MediaType` row itself is kept on purpose: every read query INNER JOINs to it, and deleting it would make the 109 legacy DV records vanish from Edit/Restore lookups too. `edit.html` shows a selected "DV (legacy)" option for those records, so saving an unrelated field can't silently switch them to CD. `restore.html`'s read-only Media Type box shows "DV" for them instead of going blank.

### Fixed
- **Edit and Restore crashed ("Unread result found" → error page) when a Library Number is shared by more than one record.** LibraryNumber isn't unique: 6,867 MediaType + LibraryNumber pairs have 2+ records (1,617 among Deleted records alone), and the by-number lookup assumed exactly one row. The bug was in Edit since before v1.3 and in Restore since v1.3. Now, if a number matches exactly one record, it opens directly as before. If it matches several, you get the same pick-list the Artist lookup uses (e.g. "2 Deleted record(s) matching CD-70041"). New `fetch_matches_by_number()` in `app.py`.

### Data
- `migration/v1.4.1_retire_dv.sql`: `UPDATE RecordLibrary SET Status = 5 WHERE MediaType = 3;` (the 109 DV records → Deleted). Run by hand on prod with this deploy. It's idempotent, and a no-op on local dev, where all 109 were already Deleted.

## [v1.4] - 2026-09-17

### Added
- WPKN logo in the header of every page — the solid-disc "WPKN DL, White Transparent Basic" mark, chosen after compositing candidate marks onto the header's actual navy (`#1F3864`) background to check real contrast (an all-black variant tested nearly invisible there). New `wpkn_flask/static/logo.png`, `.header-title`/`.logo` CSS, header markup updated on all 7 templates.
- Favicon (`favicon.ico`, `favicon-32x32.png`, `favicon-16x16.png`) and an `apple-touch-icon.png` for iOS home-screen bookmarking, generated from the same logo mark. `<link rel="icon">`/`<link rel="apple-touch-icon">` added to all 7 templates' `<head>`.
- Status bar on every page: app version, current date, and the newest release date/year in the catalog (`Status = 1` records, excluding anything more than 6 months in the future — see Fixed below). Labeled "Newest release," not "last entry" — `RecordLibrary` has no date-added column, so this reflects the album's release date, not when it was catalogued. New `APP_VERSION` constant + `get_newest_release()` + `inject_status_bar()` context processor in `app.py`, `.status-bar` CSS, `<footer>` added to all 7 templates.
- New `/new_releases` page (public, no login — like Search): pick a Media Type and see the 50 most recently added Available records of that type. Generalizes `wpkn_reports/new_releases_report.py` (kept as its own standalone script, not replaced) from two hardcoded reports (CD/DM only) into an interactive page covering all four media types. New `fetch_new_releases()` in `app.py`, `templates/new_releases.html`, nav link added to all 7 existing templates.

### Fixed
- (Data, not code) Found while building the status bar: a handful of `Status = 1` rows have a future `ReleaseDate`/`ReleaseYear`. Initially treated all of them as bad data and excluded anything past today — but David confirmed 2026-09-17 that at least one near-future date (a CD added that same night, dated 2026-09-18) is a real advance copy catalogued ahead of its street date, not a typo. Adjusted the status bar's cutoff to exclude only dates more than 6 months out, which still catches the actual typos (a `ReleaseYear = 2077`, and two rows around 2028-2029) while no longer hiding legitimate near-future entries. The typo rows themselves are still uncorrected in the catalog — tracked in `wpkn_database/todo.md` under "Data & Database."
- **Location showed the literal string "None"** for any physical (CD/LP/DV) record with a blank `Section` — surfaced 2026-09-17 by 7 newly-added prod CDs whose `Section` hadn't been backfilled yet (entered before the Section auto-derive code above went live; fix is running the "Refresh Section Data (CD)" Bulk Edit button). Root cause: MySQL's `CONCAT()` returns `NULL` for the whole expression if *any* argument is `NULL`, so `CONCAT(mt.Media, ' - Section ', r.Section)` went fully `NULL` (not just the missing part) whenever `Section` was blank, and the template had no fallback for that field. Now falls back to just the Media Type (e.g. `CD`) instead. Existed in three places with the identical query fragment: `search()` and `fetch_new_releases()` in `app.py`, plus `wpkn_reports/new_releases_report.py` (fixed too, in the `wpkn_database` repo — that script isn't part of this repo).

## [v1.3] - 2026-09-17

Deployed on-site 2026-09-17 (earlier than the originally planned ~2026-09-20 feedback-window close).

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
