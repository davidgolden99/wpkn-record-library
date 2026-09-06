from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import mysql.connector
import os
from datetime import date
load_dotenv()

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
    cursor.execute("SELECT ID, Media FROM MediaType ORDER BY ID")
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

def init_db():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            ID           INT AUTO_INCREMENT PRIMARY KEY,
            Username     VARCHAR(50)  UNIQUE NOT NULL,
            PasswordHash VARCHAR(255) NOT NULL,
            Role         ENUM('Admin','Librarian','Entry') NOT NULL
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
                    INSERT INTO RecordLibrary
                        (LibraryNumber, MediaType, Status, Artist, Title, Label,
                         Genre, Style, ReleaseDate, ReleaseYear)
                    VALUES (%s, %s, 1, %s, %s, %s, %s, %s, %s, %s)
                """, (library_number, media_type, artist, title,
                      label or None, genre or None, style or None,
                      release_date, release_year or None))
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


# ── Edit / Delete ─────────────────────────────────────────────────────────────

@app.route("/edit", methods=["GET", "POST"])
@role_required('Librarian', 'Admin')
def edit():
    genres      = get_genres()
    media_types = get_media_types()
    statuses    = get_statuses()
    record      = None
    message     = None
    message_type = None
    search_media_type      = request.form.get("search_media_type", "")
    search_library_number  = request.form.get("search_library_number", "").strip()

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "search":
            if search_media_type and search_library_number:
                db = get_db()
                cursor = db.cursor(dictionary=True)
                cursor.execute("""
                    SELECT ID, LibraryNumber, MediaType, Status, Artist, Title,
                           Label, Genre, Style, ReleaseDate, ReleaseYear, Comments, Section
                    FROM RecordLibrary
                    WHERE MediaType = %s AND LibraryNumber = %s
                """, (search_media_type, search_library_number))
                record = cursor.fetchone()
                cursor.close()
                db.close()
                if not record:
                    message = f"No record found for library number {search_library_number}."
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
                search_library_number = str(record["LibraryNumber"])

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
                           search_library_number=search_library_number)


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

    return render_template("bulk_edit.html",
                           genres=genres, records=records, artist=artist,
                           message=message, message_type=message_type)


# ── Next library number API ───────────────────────────────────────────────────

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
