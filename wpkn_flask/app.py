from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import mysql.connector
import os
from datetime import date
from urllib.parse import quote_plus
load_dotenv()

# Bumped by hand alongside CHANGELOG.md -- not read from git tags (v1.3 was
# never tagged, so tags aren't reliably in sync with what's deployed).
APP_VERSION = "1.5"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "wpkn-library-secret-2026")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'


class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT ID, Username, Role FROM Users WHERE ID = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    db.close()
    return User(row['ID'], row['Username'], row['Role']) if row else None


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── Database helpers ──────────────────────────────────────────────────────────

def get_db():
    return mysql.connector.connect(
        host=os.environ.get("WPKN_DB_HOST", "localhost"),
        user=os.environ.get("WPKN_DB_USER", "wpkn_app"),
        password=os.environ.get("WPKN_DB_PASSWORD", "changeme"),
        database=os.environ.get("WPKN_DB_NAME", "wpkn_library")
    )

def get_genres():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT Genre FROM Genre ORDER BY Genre")
    genres = [row[0] for row in cursor.fetchall()]
    cursor.close()
    db.close()
    return genres

def get_media_types():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    # DV is retired (v1.4.1): hidden from every dropdown, but the MediaType row
    # stays so the legacy DV records still resolve in the INNER JOINs.
    cursor.execute("SELECT ID, Media FROM MediaType WHERE Media != 'DV' ORDER BY ID")
    media_types = cursor.fetchall()
    cursor.close()
    db.close()
    return media_types

def get_statuses():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT ID, Status FROM `Status` ORDER BY ID")
    statuses = cursor.fetchall()
    cursor.close()
    db.close()
    return statuses

def get_newest_release():
    """Newest release date/year among Available records, for the status bar.
    RecordLibrary has no date-added column, so this is the album's release
    date/year -- not when it was catalogued (see CLAUDE.md/todo.md). Dates
    more than 6 months out are excluded: a handful of rows have obviously
    bad data (e.g. a 2077 ReleaseYear, or 2028/2029 typos) that would
    otherwise surface as the "newest" release. A shorter, few-weeks-out
    future date is kept -- confirmed 2026-09-17 that WPKN does catalog
    advance copies ahead of their actual street date, so excluding *all*
    future dates would have hidden legitimate recent entries too."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            (SELECT MAX(ReleaseDate) FROM RecordLibrary
              WHERE Status = 1 AND ReleaseDate IS NOT NULL
                AND ReleaseDate <= DATE_ADD(CURDATE(), INTERVAL 6 MONTH)) AS max_date,
            (SELECT MAX(ReleaseYear) FROM RecordLibrary
              WHERE Status = 1 AND ReleaseYear IS NOT NULL
                AND ReleaseYear <= YEAR(DATE_ADD(CURDATE(), INTERVAL 6 MONTH))) AS max_year
    """)
    row = cursor.fetchone()
    cursor.close()
    db.close()

    max_date = row["max_date"]
    max_year = row["max_year"]
    if max_date and (not max_year or max_date.year >= max_year):
        return max_date.strftime("%B %-d, %Y")
    if max_year:
        return str(max_year)
    return None


def fetch_records_by_artist(artist):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.ID, r.Artist, r.Title, r.Genre, r.Style,
               CASE
                   WHEN mt.Media = 'DM' THEN NULL
                   ELSE CONCAT(mt.Media, '-', r.LibraryNumber)
               END AS CallNumber
        FROM RecordLibrary r
        JOIN MediaType mt ON r.MediaType = mt.ID
        WHERE r.Artist = %s
        ORDER BY r.MediaType, r.LibraryNumber
    """, (artist,))
    records = cursor.fetchall()
    cursor.close()
    db.close()
    return records

def fetch_record_by_id(record_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT ID, LibraryNumber, MediaType, Status, Artist, Title,
               Label, Genre, Style, ReleaseDate, ReleaseYear, Comments, Section
        FROM RecordLibrary WHERE ID = %s
    """, (record_id,))
    record = cursor.fetchone()
    cursor.close()
    db.close()
    return record

def fetch_new_releases(media_type, limit=50):
    """Most recently added Available records of one MediaType, for the New
    Releases page. "Latest" = insertion order (ID DESC) -- RecordLibrary has
    no date-added column, so this is a proxy, not an actual date."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            CASE WHEN mt.Media = 'DM' THEN NULL
                 ELSE CONCAT(mt.Media, '-', r.LibraryNumber)
            END AS CallNumber,
            r.Artist, r.Title, r.Label, r.ReleaseYear, r.Genre,
            CASE WHEN mt.Media = 'DM' THEN 'Digital'
                 WHEN r.Section IS NULL THEN mt.Media
                 ELSE CONCAT(mt.Media, ' - Section ', r.Section)
            END AS Location
        FROM RecordLibrary r
        JOIN MediaType mt ON r.MediaType = mt.ID
        WHERE r.Status = 1 AND r.MediaType = %s
        ORDER BY r.ID DESC
        LIMIT %s
    """, (media_type, limit))
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return rows

def fetch_deleted_matches_by_artist(artist):
    """Deleted (Status=5) records whose Artist contains `artist`, for the
    Restore page's by-artist lookup — the way to reach DM records and any
    record with no LibraryNumber."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.ID, r.LibraryNumber, r.Artist, r.Title,
               mt.Media,
               CASE WHEN mt.Media = 'DM' OR r.LibraryNumber IS NULL THEN NULL
                    ELSE CONCAT(mt.Media, '-', r.LibraryNumber) END AS CallNumber
        FROM RecordLibrary r
        JOIN MediaType mt ON r.MediaType = mt.ID
        WHERE r.Artist LIKE %s AND r.Status = 5
        ORDER BY r.Artist, r.Title
        LIMIT 200
    """, ("%" + artist + "%",))
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return rows

def fetch_edit_matches_by_artist(artist):
    """Records whose Artist contains `artist`, for the Edit page's by-artist
    lookup — the way to reach DM records and any record with no LibraryNumber."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.ID, r.LibraryNumber, r.Artist, r.Title,
               mt.Media, s.Status AS StatusName,
               CASE WHEN mt.Media = 'DM' OR r.LibraryNumber IS NULL THEN NULL
                    ELSE CONCAT(mt.Media, '-', r.LibraryNumber) END AS CallNumber
        FROM RecordLibrary r
        JOIN MediaType mt ON r.MediaType = mt.ID
        LEFT JOIN `Status` s ON r.Status = s.ID
        WHERE r.Artist LIKE %s
        ORDER BY r.Artist, r.Title
        LIMIT 200
    """, ("%" + artist + "%",))
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return rows

def fetch_matches_by_number(media_type, library_number, deleted_only=False):
    """Records with this MediaType + LibraryNumber. LibraryNumber isn't unique
    (thousands of numbers are shared by 2+ records), so Edit/Restore show these
    as a pick-list when there's more than one instead of assuming a single row."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.ID, r.LibraryNumber, r.Artist, r.Title,
               mt.Media, s.Status AS StatusName,
               CONCAT(mt.Media, '-', r.LibraryNumber) AS CallNumber
        FROM RecordLibrary r
        JOIN MediaType mt ON r.MediaType = mt.ID
        LEFT JOIN `Status` s ON r.Status = s.ID
        WHERE r.MediaType = %s AND r.LibraryNumber = %s
    """ + (" AND r.Status = 5" if deleted_only else "") + """
        ORDER BY r.Artist, r.Title
        LIMIT 200
    """, (media_type, library_number))
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return rows

@app.context_processor
def inject_status_bar():
    try:
        newest_release = get_newest_release()
    except Exception:
        newest_release = None
    return {
        "app_version": APP_VERSION,
        "current_date": date.today().strftime("%B %-d, %Y"),
        "newest_release": newest_release,
    }


def init_db():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            ID           INT AUTO_INCREMENT PRIMARY KEY,
            Username     VARCHAR(50)  UNIQUE NOT NULL,
            PasswordHash VARCHAR(255) NOT NULL,
            Role         ENUM('Admin','Librarian','Entry','Restore','Genre') NOT NULL
        )
    """)
    db.commit()
    cursor.execute("SELECT COUNT(*) FROM Users")
    if cursor.fetchone()[0] == 0:
        seed = [
            ('Admin',     generate_password_hash('wpknadmin'),   'Admin'),
            ('Librarian', generate_password_hash('wpknlibrary'), 'Librarian'),
            ('Entry',     generate_password_hash('wpkn895'),     'Entry'),
        ]
        cursor.executemany(
            "INSERT INTO Users (Username, PasswordHash, Role) VALUES (%s, %s, %s)", seed
        )
        db.commit()
    cursor.close()
    db.close()


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('search'))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT ID, Username, PasswordHash, Role FROM Users WHERE Username = %s",
            (username,)
        )
        row = cursor.fetchone()
        cursor.close()
        db.close()
        if row and check_password_hash(row['PasswordHash'], password):
            login_user(User(row['ID'], row['Username'], row['Role']))
            return redirect(request.args.get('next') or url_for('search'))
        error = "Invalid username or password."
    return render_template("login.html", error=error)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('search'))


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.route("/admin", methods=["GET", "POST"])
@role_required('Admin')
def admin():
    message = None
    message_type = None
    edit_user = None

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "load_edit":
            user_id = request.form.get("user_id")
            db = get_db()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT ID, Username, Role FROM Users WHERE ID = %s", (user_id,))
            edit_user = cursor.fetchone()
            cursor.close()
            db.close()

        elif action == "add":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            role     = request.form.get("role", "")
            if not username or not password or not role:
                message = "Username, password, and role are all required."
                message_type = "error"
            else:
                try:
                    db = get_db()
                    cursor = db.cursor()
                    cursor.execute(
                        "INSERT INTO Users (Username, PasswordHash, Role) VALUES (%s, %s, %s)",
                        (username, generate_password_hash(password), role)
                    )
                    db.commit()
                    cursor.close()
                    db.close()
                    message = f"User '{username}' created."
                    message_type = "success"
                except Exception as e:
                    message = f"Error: {e}"
                    message_type = "error"

        elif action == "update":
            user_id  = request.form.get("user_id")
            username = request.form.get("username", "").strip()
            role     = request.form.get("role", "")
            password = request.form.get("password", "").strip()
            if not username or not role:
                message = "Username and role are required."
                message_type = "error"
            else:
                try:
                    db = get_db()
                    cursor = db.cursor()
                    if password:
                        cursor.execute(
                            "UPDATE Users SET Username=%s, Role=%s, PasswordHash=%s WHERE ID=%s",
                            (username, role, generate_password_hash(password), user_id)
                        )
                    else:
                        cursor.execute(
                            "UPDATE Users SET Username=%s, Role=%s WHERE ID=%s",
                            (username, role, user_id)
                        )
                    db.commit()
                    cursor.close()
                    db.close()
                    message = f"User '{username}' updated."
                    message_type = "success"
                except Exception as e:
                    message = f"Error: {e}"
                    message_type = "error"

        elif action == "delete":
            user_id = request.form.get("user_id")
            if str(user_id) == str(current_user.id):
                message = "You cannot delete your own account."
                message_type = "error"
            else:
                try:
                    db = get_db()
                    cursor = db.cursor()
                    cursor.execute("DELETE FROM Users WHERE ID = %s", (user_id,))
                    db.commit()
                    cursor.close()
                    db.close()
                    message = "User deleted."
                    message_type = "success"
                except Exception as e:
                    message = f"Error: {e}"
                    message_type = "error"

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT ID, Username, Role FROM Users ORDER BY Role, Username")
    users = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template("admin.html",
                           users=users,
                           edit_user=edit_user,
                           message=message,
                           message_type=message_type)


# ── Search (public) ───────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def search():
    results = []
    artist       = request.form.get("artist", "")
    artist2      = request.form.get("artist2", "")
    artist_toggle = request.form.get("artist_toggle", "AND")
    artist_exact = request.form.get("artist_exact", "")
    title        = request.form.get("title", "")
    title_exact  = request.form.get("title_exact", "")
    genre        = request.form.get("genre", "")
    style        = request.form.get("style", "")
    local_only   = request.form.get("local_only", "")
    record_count = 0
    genres       = get_genres()

    if request.method == "POST":
        db = get_db()
        cursor = db.cursor(dictionary=True)

        query = """
            SELECT
                CASE
                    WHEN mt.Media = 'DM' THEN NULL
                    ELSE CONCAT(mt.Media, '-', r.LibraryNumber)
                END AS CallNumber,
                r.Artist, r.Title, r.Genre, r.Style, r.ReleaseYear, r.Comments,
                CASE
                    WHEN mt.Media = 'DM' THEN 'Digital'
                    WHEN r.Section IS NULL THEN mt.Media
                    ELSE CONCAT(mt.Media, ' - Section ', r.Section)
                END AS Location
            FROM RecordLibrary r
            JOIN MediaType mt ON r.MediaType = mt.ID
            WHERE r.Status = 1
        """
        params = []

        op = "=" if artist_exact else "LIKE"
        def artist_val(term):
            return term if artist_exact else f"%{term}%"

        if artist and artist2:
            if artist_toggle == "OR":
                query += f" AND (r.Artist {op} %s OR r.Artist {op} %s)"
            else:
                query += f" AND (r.Artist {op} %s AND r.Artist {op} %s)"
            params += [artist_val(artist), artist_val(artist2)]
        elif artist:
            query += f" AND r.Artist {op} %s"
            params.append(artist_val(artist))
        elif artist2:
            query += f" AND r.Artist {op} %s"
            params.append(artist_val(artist2))

        if title:
            title_op = "=" if title_exact else "LIKE"
            query += f" AND r.Title {title_op} %s"
            params.append(title if title_exact else f"%{title}%")
        if genre:
            query += " AND r.Genre = %s"
            params.append(genre)
        if style:
            query += " AND r.Style LIKE %s"
            params.append(f"%{style}%")
        if local_only:
            query += " AND r.Comments LIKE %s"
            params.append("%Local%")

        query += " ORDER BY r.MediaType, r.LibraryNumber LIMIT 200"

        cursor.execute(query, params)
        results = cursor.fetchall()
        record_count = len(results)
        cursor.close()
        db.close()

    return render_template("search.html",
                           results=results,
                           artist=artist, artist2=artist2,
                           artist_toggle=artist_toggle,
                           artist_exact=artist_exact,
                           title=title, title_exact=title_exact,
                           genre=genre, style=style,
                           local_only=local_only,
                           genres=genres,
                           record_count=record_count)


# ── New Releases (public) ──────────────────────────────────────────────────────

@app.route("/new_releases", methods=["GET", "POST"])
def new_releases():
    media_types = get_media_types()
    media_type  = request.form.get("media_type", "")
    results     = []

    if request.method == "POST" and media_type:
        results = fetch_new_releases(media_type, limit=50)

    return render_template("new_releases.html",
                           media_types=media_types,
                           media_type=media_type,
                           results=results)


# ── Data Entry ────────────────────────────────────────────────────────────────

@app.route("/entry", methods=["GET", "POST"])
@role_required('Entry', 'Librarian', 'Admin')
def entry():
    genres      = get_genres()
    media_types = get_media_types()
    message     = None
    message_type = None
    current_year = date.today().year

    if request.method == "POST":
        media_type     = request.form.get("media_type", "").strip()
        library_number = request.form.get("library_number", "").strip()
        artist         = request.form.get("artist", "").strip()
        title          = request.form.get("title", "").strip()
        label          = request.form.get("label", "").strip()
        genre          = request.form.get("genre", "").strip()
        style          = request.form.get("style", "").strip()
        release_date   = request.form.get("release_date") or None
        release_year   = request.form.get("release_year") or None

        if not media_type or not library_number or not artist or not title:
            message = "Media Type, Artist, and Title are required."
            message_type = "error"
        else:
            try:
                db = get_db()
                cursor = db.cursor()
                cursor.execute("""
                    SELECT Section FROM Sections
                    WHERE MediaType = %s
                      AND RangeEnd > 0
                      AND %s BETWEEN RangeStart AND RangeEnd
                    LIMIT 1
                """, (media_type, library_number))
                row = cursor.fetchone()
                section = row[0] if row else None

                cursor.execute("""
                    INSERT INTO RecordLibrary
                        (LibraryNumber, MediaType, Status, Artist, Title, Label,
                         Genre, Style, ReleaseDate, ReleaseYear, Section)
                    VALUES (%s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (library_number, media_type, artist, title,
                      label or None, genre or None, style or None,
                      release_date, release_year or None, section))
                db.commit()
                cursor.close()
                db.close()
                message = f"Saved: {artist} — {title}"
                message_type = "success"
            except Exception as e:
                message = f"Error saving record: {e}"
                message_type = "error"

    return render_template("entry.html",
                           genres=genres, media_types=media_types,
                           message=message, message_type=message_type,
                           current_year=current_year)


# ── Restore Deleted ───────────────────────────────────────────────────────────

@app.route("/restore", methods=["GET", "POST"])
@role_required('Entry', 'Restore', 'Librarian', 'Admin')
def restore():
    genres      = get_genres()
    media_types = get_media_types()
    dm_media_id = next((str(mt["ID"]) for mt in media_types if mt["Media"] == "DM"), "")
    record      = None
    message     = None
    message_type = None
    search_media_type     = request.form.get("search_media_type", "")
    search_library_number = request.form.get("search_library_number", "").strip()
    search_artist         = request.form.get("search_artist", "").strip()
    artist_matches        = []
    matches_for           = search_artist

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "search":
            picked_id = request.form.get("record_id", "").strip()
            if picked_id:
                candidate = fetch_record_by_id(picked_id)
                if candidate and candidate["Status"] == 5:
                    record = candidate
                    search_media_type     = str(record["MediaType"])
                    search_library_number = str(record["LibraryNumber"] or "")
                else:
                    message = "That record is no longer Deleted."
                    message_type = "error"
            elif search_artist:
                artist_matches = fetch_deleted_matches_by_artist(search_artist)
                if not artist_matches:
                    message = f"No Deleted records found for an artist matching '{search_artist}'."
                    message_type = "error"
            elif search_media_type and search_library_number:
                number_matches = fetch_matches_by_number(
                    search_media_type, search_library_number, deleted_only=True)
                if len(number_matches) == 1:
                    record = fetch_record_by_id(number_matches[0]["ID"])
                elif number_matches:
                    artist_matches = number_matches
                    matches_for = number_matches[0]["CallNumber"]
                else:
                    message = f"No Deleted record found for library number {search_library_number}."
                    message_type = "error"
            else:
                message = "Enter a Library Number, or pick Digital (DM) and search by Artist."
                message_type = "error"

        elif action == "restore":
            record_id    = request.form.get("record_id")
            label        = request.form.get("label", "").strip() or None
            genre        = request.form.get("genre", "").strip()
            release_year = request.form.get("release_year") or None
            current      = fetch_record_by_id(record_id)
            if not current or current["Status"] != 5:
                message = "That record is no longer Deleted — nothing was changed."
                message_type = "error"
            elif genre not in genres:
                # Genre is required on restore: restores are picked by someone
                # who knows the music, so every restored record should come back
                # with an approved Genre. Keep what they typed and re-show.
                record = dict(current, Label=label, ReleaseYear=release_year)
                message = "Choose a Genre from the list before restoring."
                message_type = "error"
            else:
                # An off-list legacy Genre (e.g. "Texas Swing, Jazz") is being
                # replaced — keep its text in Style rather than losing it.
                style = current["Style"]
                old_genre = (current["Genre"] or "").strip()
                if old_genre and old_genre not in genres:
                    style = f"{style.strip()}; {old_genre}" if (style or "").strip() else old_genre
                try:
                    db = get_db()
                    cursor = db.cursor()
                    cursor.execute("""
                        UPDATE RecordLibrary SET
                            Status = 1, Label = %s, Genre = %s, ReleaseYear = %s, Style = %s
                        WHERE ID = %s AND Status = 5
                    """, (label, genre, release_year, style, record_id))
                    db.commit()
                    restored = cursor.rowcount == 1
                    cursor.close()
                    db.close()
                    if restored:
                        message = "Record restored to Available."
                        message_type = "success"
                    else:
                        message = "That record is no longer Deleted — nothing was changed."
                        message_type = "error"
                except Exception as e:
                    message = f"Error: {e}"
                    message_type = "error"

    return render_template("restore.html",
                           genres=genres, media_types=media_types, record=record,
                           message=message, message_type=message_type,
                           search_media_type=search_media_type,
                           search_library_number=search_library_number,
                           search_artist=search_artist, artist_matches=artist_matches,
                           matches_for=matches_for, dm_media_id=dm_media_id)


# ── Edit / Delete ─────────────────────────────────────────────────────────────

@app.route("/edit", methods=["GET", "POST"])
@role_required('Librarian', 'Admin')
def edit():
    genres      = get_genres()
    media_types = get_media_types()
    statuses    = get_statuses()
    dm_media_id = next((str(mt["ID"]) for mt in media_types if mt["Media"] == "DM"), "")
    record      = None
    message     = None
    message_type = None
    search_media_type      = request.form.get("search_media_type", "")
    search_library_number  = request.form.get("search_library_number", "").strip()
    search_artist          = request.form.get("search_artist", "").strip()
    artist_matches         = []
    matches_for            = search_artist

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "search":
            picked_id = request.form.get("record_id", "").strip()
            if picked_id:
                # Chosen from the by-artist match list — how DM records and any
                # record with no LibraryNumber get opened for editing.
                record = fetch_record_by_id(picked_id)
                if record:
                    search_media_type     = str(record["MediaType"])
                    search_library_number = str(record["LibraryNumber"] or "")
                else:
                    message = "That record could no longer be found."
                    message_type = "error"
            elif search_artist:
                artist_matches = fetch_edit_matches_by_artist(search_artist)
                if not artist_matches:
                    message = f"No records found for an artist matching '{search_artist}'."
                    message_type = "error"
            elif search_media_type and search_library_number:
                number_matches = fetch_matches_by_number(search_media_type, search_library_number)
                if len(number_matches) == 1:
                    record = fetch_record_by_id(number_matches[0]["ID"])
                elif number_matches:
                    artist_matches = number_matches
                    matches_for = number_matches[0]["CallNumber"]
                else:
                    message = f"No record found for library number {search_library_number}."
                    message_type = "error"
            else:
                message = "Enter a Library Number, or pick Digital (DM) and search by Artist."
                message_type = "error"

        elif action == "update":
            record_id = request.form.get("record_id")
            artist = request.form.get("artist", "").strip()
            title  = request.form.get("title", "").strip()
            if not artist or not title:
                message = "Artist and Title are required."
                message_type = "error"
            else:
                try:
                    db = get_db()
                    cursor = db.cursor()
                    cursor.execute("""
                        UPDATE RecordLibrary SET
                            MediaType=%s, Status=%s, Artist=%s, Title=%s,
                            Label=%s, Genre=%s, Style=%s,
                            ReleaseDate=%s, ReleaseYear=%s,
                            Comments=%s, Section=%s
                        WHERE ID=%s
                    """, (
                        request.form.get("media_type"),
                        request.form.get("status"),
                        artist, title,
                        request.form.get("label")    or None,
                        request.form.get("genre")    or None,
                        request.form.get("style")    or None,
                        request.form.get("release_date")  or None,
                        request.form.get("release_year")  or None,
                        request.form.get("comments") or None,
                        request.form.get("section")  or None,
                        record_id
                    ))
                    db.commit()
                    cursor.close()
                    db.close()
                    message = f"Saved: {artist} — {title}"
                    message_type = "success"
                except Exception as e:
                    message = f"Error: {e}"
                    message_type = "error"
            record = fetch_record_by_id(record_id)
            if record:
                search_media_type     = str(record["MediaType"])
                search_library_number = str(record["LibraryNumber"] or "")

        elif action == "delete":
            record_id = request.form.get("record_id")
            try:
                db = get_db()
                cursor = db.cursor()
                cursor.execute("UPDATE RecordLibrary SET Status = 5 WHERE ID = %s", (record_id,))
                db.commit()
                cursor.close()
                db.close()
                message = "Record marked as Deleted."
                message_type = "success"
            except Exception as e:
                message = f"Error: {e}"
                message_type = "error"

    return render_template("edit.html",
                           genres=genres, media_types=media_types, statuses=statuses,
                           record=record, message=message, message_type=message_type,
                           search_media_type=search_media_type,
                           search_library_number=search_library_number,
                           search_artist=search_artist, artist_matches=artist_matches,
                           matches_for=matches_for, dm_media_id=dm_media_id)


# ── Bulk Edit by Artist ────────────────────────────────────────────────────────

@app.route("/bulk_edit", methods=["GET", "POST"])
@role_required('Librarian', 'Admin')
def bulk_edit():
    genres  = get_genres()
    message = None
    message_type = None
    artist  = request.form.get("artist", "").strip()
    records = []

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "search":
            if artist:
                records = fetch_records_by_artist(artist)
                if not records:
                    message = f"No records found for artist '{artist}'."
                    message_type = "error"

        elif action == "apply":
            genre = request.form.get("genre", "").strip()
            style = request.form.get("style", "").strip()
            record_ids = request.form.getlist("record_ids")

            if not record_ids:
                message = "No records selected."
                message_type = "error"
            elif not genre and not style:
                message = "Enter a Genre or Style to apply."
                message_type = "error"
            else:
                set_parts = []
                params = []
                if genre:
                    set_parts.append("Genre = %s")
                    params.append(genre)
                if style:
                    set_parts.append("Style = %s")
                    params.append(style)
                placeholders = ", ".join(["%s"] * len(record_ids))

                try:
                    db = get_db()
                    cursor = db.cursor()
                    cursor.execute(
                        f"UPDATE RecordLibrary SET {', '.join(set_parts)} WHERE ID IN ({placeholders})",
                        params + record_ids
                    )
                    db.commit()
                    updated = cursor.rowcount
                    cursor.close()
                    db.close()
                    message = f"Updated {updated} record(s) for '{artist}'."
                    message_type = "success"
                except Exception as e:
                    message = f"Error: {e}"
                    message_type = "error"

            records = fetch_records_by_artist(artist)

        elif action == "refresh_sections":
            try:
                db = get_db()
                cursor = db.cursor()
                cursor.execute("""
                    UPDATE RecordLibrary r
                    JOIN Sections s
                        ON s.MediaType = r.MediaType
                       AND s.RangeEnd > 0
                       AND r.LibraryNumber BETWEEN s.RangeStart AND s.RangeEnd
                    SET r.Section = s.Section
                    WHERE r.MediaType = 1
                      AND r.Status = 1
                      AND r.Section IS NULL
                """)
                db.commit()
                updated = cursor.rowcount
                cursor.close()
                db.close()
                message = f"Section refresh complete: filled in Section for {updated} CD record(s) that had a blank Section."
                message_type = "success"
            except Exception as e:
                message = f"Error: {e}"
                message_type = "error"

    return render_template("bulk_edit.html",
                           genres=genres, records=records, artist=artist,
                           message=message, message_type=message_type)


# ── Next library number API ───────────────────────────────────────────────────

# ── Genre review (volunteers propose, Librarian approves) ─────────────────────

CONFIDENCE_LEVELS = ("High", "Medium", "Low")

def discogs_search_url(artist, title):
    return ("https://www.discogs.com/search/?type=all&q="
            + quote_plus(f"{artist or ''} {title or ''}".strip()))

@app.route("/genres")
@role_required('Genre', 'Librarian', 'Admin')
def genres():
    """A volunteer's own batch. Rows save one at a time via /genres/save."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT record_id, artist, title, label, year, media,
               proposed_genre, confidence, notes, status, final_genre
        FROM genre_staging
        WHERE assigned_to = %s
        ORDER BY artist, title, record_id
    """, (current_user.username,))
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    for row in rows:
        row["lookup_url"] = discogs_search_url(row["artist"], row["title"])
    # A note with no genre stays open -- only a chosen genre counts as done.
    done = sum(1 for r in rows if r["status"] != "open")
    return render_template("genres.html", rows=rows, done=done,
                           genres=get_genres(), confidence_levels=CONFIDENCE_LEVELS)

@app.route("/genres/save", methods=["POST"])
@role_required('Genre', 'Librarian', 'Admin')
def genres_save():
    data       = request.get_json(silent=True) or {}
    record_id  = data.get("record_id")
    genre      = (data.get("proposed_genre") or "").strip()
    confidence = (data.get("confidence") or "").strip()
    notes      = (data.get("notes") or "").strip()[:500]
    if genre and genre not in get_genres():
        return jsonify({"ok": False, "error": "Pick a genre from the list."}), 400
    if confidence and confidence not in CONFIDENCE_LEVELS:
        return jsonify({"ok": False, "error": "Pick High, Medium, or Low."}), 400
    db = get_db()
    cursor = db.cursor()
    # Only the volunteer's own rows, and never one the Librarian has already
    # approved or rejected. Checked with a SELECT rather than the UPDATE's
    # rowcount, which is 0 when a re-save changes nothing.
    cursor.execute("""
        SELECT status FROM genre_staging WHERE record_id = %s AND assigned_to = %s
    """, (record_id, current_user.username))
    row = cursor.fetchone()
    if not row or row[0] not in ("open", "proposed"):
        cursor.close()
        db.close()
        if not row:
            return jsonify({"ok": False, "error": "This album isn't on your list."}), 404
        return jsonify({"ok": False,
                        "error": "This row can't be changed any more — it's already been reviewed."}), 409
    cursor.execute("""
        UPDATE genre_staging SET
            proposed_genre = %s, confidence = %s, notes = %s,
            status = %s, edited_by = %s, edited_at = NOW()
        WHERE record_id = %s AND assigned_to = %s AND status IN ('open', 'proposed')
    """, (genre or None, confidence or None, notes or None,
          "proposed" if genre else "open",
          current_user.username, record_id, current_user.username))
    db.commit()
    cursor.execute("""
        SELECT COUNT(*), SUM(status <> 'open') FROM genre_staging WHERE assigned_to = %s
    """, (current_user.username,))
    total, done = cursor.fetchone()
    cursor.close()
    db.close()
    return jsonify({"ok": True, "status": "proposed" if genre else "open",
                    "done": int(done or 0), "total": total})

@app.route("/genres/review", methods=["GET", "POST"])
@role_required('Librarian', 'Admin')
def genre_review():
    genre_list = get_genres()
    volunteer  = request.values.get("volunteer", "").strip()
    message = None
    message_type = None

    if request.method == "POST":
        action = request.form.get("action", "")
        db = get_db()
        cursor = db.cursor(dictionary=True)
        try:
            if action in ("approve", "reject"):
                targets = [(request.form.get("record_id"), request.form.get("final_genre", "").strip())]
            elif action == "approve_high":
                cursor.execute("""
                    SELECT record_id, proposed_genre FROM genre_staging
                    WHERE status = 'proposed' AND confidence = 'High'
                """ + (" AND assigned_to = %s" if volunteer else ""),
                    (volunteer,) if volunteer else ())
                targets = [(r["record_id"], r["proposed_genre"]) for r in cursor.fetchall()]
            else:
                targets = []

            approved = rejected = skipped = 0
            for record_id, final_genre in targets:
                if action == "reject":
                    cursor.execute("""
                        UPDATE genre_staging SET status = 'rejected',
                               reviewed_by = %s, reviewed_at = NOW()
                        WHERE record_id = %s AND status = 'proposed'
                    """, (current_user.username, record_id))
                    rejected += cursor.rowcount
                    continue
                if final_genre not in genre_list:
                    raise ValueError(f"'{final_genre}' is not in the Genre list.")
                # Only a row a volunteer has actually proposed, locked so a
                # concurrent save can't slip in between the two writes.
                cursor.execute("""
                    SELECT status FROM genre_staging WHERE record_id = %s FOR UPDATE
                """, (record_id,))
                row = cursor.fetchone()
                if not row or row["status"] != "proposed":
                    continue
                # Never overwrite a genre someone added some other way in the
                # meantime (Edit, Restore, Bulk Edit).
                cursor.execute("""
                    UPDATE RecordLibrary SET Genre = %s, NeedsReview = 0
                    WHERE ID = %s AND (Genre IS NULL OR Genre = '')
                """, (final_genre, record_id))
                wrote = cursor.rowcount == 1
                cursor.execute("""
                    UPDATE genre_staging SET status = %s, final_genre = %s,
                           reviewed_by = %s, reviewed_at = NOW()
                    WHERE record_id = %s AND status = 'proposed'
                """, ("approved" if wrote else "skipped", final_genre if wrote else None,
                      current_user.username, record_id))
                if wrote:
                    approved += 1
                else:
                    skipped += 1
            db.commit()
            parts = []
            if approved: parts.append(f"{approved} approved")
            if rejected: parts.append(f"{rejected} rejected")
            if skipped:  parts.append(f"{skipped} skipped (record already had a genre)")
            if parts:
                message = ", ".join(parts).capitalize() + "."
            elif action in ("approve", "reject"):
                message = "That suggestion isn't waiting for review any more — it was already reviewed or changed."
            else:
                message = "No High-confidence suggestions to approve."
            message_type = "success"
        except Exception as e:
            db.rollback()
            message = f"Error: {e}"
            message_type = "error"
        finally:
            cursor.close()
            db.close()

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT assigned_to,
               COUNT(*)                   AS total,
               SUM(status = 'open')       AS open_rows,
               SUM(status = 'proposed')   AS proposed,
               SUM(status = 'approved')   AS approved,
               SUM(status = 'rejected')   AS rejected,
               SUM(status = 'skipped')    AS skipped
        FROM genre_staging GROUP BY assigned_to ORDER BY assigned_to
    """)
    summary = cursor.fetchall()
    cursor.execute("""
        SELECT record_id, artist, title, label, year, media, assigned_to,
               proposed_genre, confidence, notes, edited_at
        FROM genre_staging
        WHERE status = 'proposed'
    """ + (" AND assigned_to = %s" if volunteer else "") + """
        ORDER BY assigned_to, artist, title, record_id
        LIMIT 500
    """, (volunteer,) if volunteer else ())
    proposals = cursor.fetchall()
    cursor.close()
    db.close()
    for row in proposals:
        row["lookup_url"] = discogs_search_url(row["artist"], row["title"])
    return render_template("genre_review.html", summary=summary, proposals=proposals,
                           volunteer=volunteer, genres=genre_list,
                           message=message, message_type=message_type)


@app.route("/api/next_library_number")
@role_required('Entry', 'Librarian', 'Admin')
def next_library_number():
    media_type = request.args.get("media_type", "").strip()
    if not media_type:
        return jsonify({"error": "media_type required"}), 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT COALESCE(MAX(LibraryNumber), 0) + 1 FROM RecordLibrary WHERE MediaType = %s",
        (media_type,)
    )
    next_num = cursor.fetchone()[0]
    cursor.close()
    db.close()
    return jsonify({"next_number": next_num})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
