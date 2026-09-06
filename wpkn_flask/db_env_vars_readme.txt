WPKN Flask App — Database Connection via Environment Variables
================================================================

app.py's get_db() now reads its MySQL connection settings from environment
variables, falling back to your local dev values if they're not set:

    WPKN_DB_HOST      (default: localhost)
    WPKN_DB_USER      (default: root)
    WPKN_DB_PASSWORD  (default: <your local MySQL root password>)
    WPKN_DB_NAME      (default: wpkn_library)

LOCAL DEV (your MacBook)
-------------------------
Nothing to do. Run the app exactly as before:

    cd wpkn_flask
    python3 app.py

It connects as root on localhost, same as always.

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
it there, not on your local MySQL). Hardcoding it in app.py would break
local testing, since your MacBook's MySQL only has root. Env vars let the
same app.py work in both places without editing code before/after deploys.
