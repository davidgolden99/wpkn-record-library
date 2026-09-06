# WPKN Record Library

A Flask + MySQL web app for searching and managing WPKN 89.5 FM's music catalog
(~145,000 CDs, LPs, digital files, and DVDs), replacing a Microsoft Access
database that programmers previously had to request access to individually.

Live at `library.wpkn.org` for station programmers. Public search requires no
login; Data Entry, Librarian, and Administrator roles require authentication
(Flask-Login).

## Structure

- `wpkn_flask/` — the Flask app (`app.py`), templates, and static assets.
- `migration/` — scripts used to clean and load the original Access export
  into MySQL (`clean_recordlibrary.py`), plus reference SQL queries mirroring
  the app's search logic (`wpkn_search_queries.sql`).

## Running locally

```bash
cd wpkn_flask
python3 app.py
# http://127.0.0.1:5000
```

Requires a local MySQL instance with the `wpkn_library` schema loaded (see
`migration/clean_recordlibrary.py` for how the source data was prepared, and
`wpkn_flask/db_env_vars_readme.txt` for the environment variables the app
expects). Connection credentials are read from `WPKN_DB_*` env vars — there
are no working credentials in this repo.

## Status

Microsoft Access remains the authoritative source of truth while the MySQL
data is cleaned up post-launch; this repo tracks the app and migration
tooling, not the catalog data itself.
