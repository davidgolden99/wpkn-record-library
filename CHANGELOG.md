# Changelog

All notable changes to this project are documented here.

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
