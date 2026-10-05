WPKN Flask App — Database Connection via Environment Variables
================================================================

app.py's get_db() reads its MySQL connection settings from environment
variables. At startup app.py also loads wpkn_flask/.env (python-dotenv), so
the variables can live in that file instead. If a variable isn't set, it
falls back to:

    WPKN_DB_HOST      (default: localhost)
    WPKN_DB_USER      (default: wpkn_app)
    WPKN_DB_PASSWORD  (default: changeme, a placeholder that never works)
    WPKN_DB_NAME      (default: wpkn_library)

LOCAL DEV (your MacBook)
-------------------------
Your MacBook's MySQL has no wpkn_app account, so local dev needs a .env.
One-time setup, from the repo folder:

    python3 -m pip install -r requirements.txt

Then create wpkn_flask/.env with your local root login:

    WPKN_DB_USER=root
    WPKN_DB_PASSWORD=<your local MySQL root password>

Git ignores .env (.gitignore has *.env), so the password stays on the Mac.
Then run:

    cd wpkn_flask
    python3 app.py

Without .env the app fails at startup with "Access denied for user
'wpkn_app'@'localhost'".

PRODUCTION (the rack server)
------------------------------
Set these four env vars before starting the app, using the wpkn_app
account Matthew (Now IT Works) created:

    export WPKN_DB_HOST=localhost
    export WPKN_DB_USER=wpkn_app
    export WPKN_DB_PASSWORD='<wpkn_app account password — see internal credentials doc>'
    export WPKN_DB_NAME=wpkn_library

    python3 app.py

If you're using systemd to run the app as a service, put these in an
EnvironmentFile instead of exporting them by hand, e.g.:

    # /etc/wpkn/flask.env
    WPKN_DB_HOST=localhost
    WPKN_DB_USER=wpkn_app
    WPKN_DB_PASSWORD=<wpkn_app account password — see internal credentials doc>
    WPKN_DB_NAME=wpkn_library

...and reference it in the systemd unit file with:

    EnvironmentFile=/etc/wpkn/flask.env

Keep that env file out of version control, same as authentication.txt.

WHY
---
The wpkn_app MySQL account only exists on the rack server (Matthew created
it there, not on your local MySQL), and your MacBook's MySQL only has root.
Env vars let the same app.py work in both places without editing code
before/after deploys.
