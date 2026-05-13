from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    url_for,
    flash
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from dotenv import load_dotenv
import pymysql
import os

from permissions import (
    login_required,
    admin_required
)
from bot_api import (
    join_vc,
    leave_vc,
    play_sound,
    send_embed
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET",
    "change_this_now"
)

UPLOAD_FOLDER = "sounds"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------- DATABASE ----------------
def db():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def init_db():
    conn = db()

    with conn.cursor() as cursor:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            can_upload BOOLEAN DEFAULT FALSE,
            can_embed BOOLEAN DEFAULT FALSE,
            can_vc BOOLEAN DEFAULT FALSE,
            can_sound BOOLEAN DEFAULT FALSE
        )
        """)

        cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            ("admin",)
        )
        existing = cursor.fetchone()

        if not existing:
            cursor.execute("""
            INSERT INTO users
            (
                username,
                password,
                is_admin,
                can_upload,
                can_embed,
                can_vc,
                can_sound
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                "admin",
                generate_password_hash(
                    "admin123"
                ),
                True,
                True,
                True,
                True,
                True
            ))

    conn.close()


init_db()


# ---------------- ROUTES ----------------
@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = db()

        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE username=%s",
                (username,)
            )
            user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):
            session["user"] = user["username"]
            session["is_admin"] = user["is_admin"]

            flash("Logged in successfully.")
            return redirect(
                url_for("dashboard")
            )

        flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html"
    )


# ---------------- VC CONTROLS ----------------
@app.route("/join_vc", methods=["POST"])
@login_required
def route_join_vc():
    channel_id = int(
        request.form["channel_id"]
    )
    join_vc(channel_id)

    flash("Join VC command sent.")
    return redirect(
        url_for("dashboard")
    )


@app.route("/leave_vc", methods=["POST"])
@login_required
def route_leave_vc():
    leave_vc()

    flash("Leave VC command sent.")
    return redirect(
        url_for("dashboard")
    )


# ---------------- SOUNDS ----------------
@app.route(
    "/sounds",
    methods=["GET", "POST"]
)
@login_required
def sounds():
    if request.method == "POST":
        file = request.files.get("file")

        if file and file.filename:
            allowed = (
                file.filename.endswith(".mp3")
                or file.filename.endswith(".wav")
                or file.filename.endswith(".ogg")
            )

            if allowed:
                path = os.path.join(
                    UPLOAD_FOLDER,
                    file.filename
                )
                file.save(path)
                flash(
                    "Uploaded successfully."
                )
            else:
                flash(
                    "Only mp3/wav/ogg allowed."
                )

    files = os.listdir(
        UPLOAD_FOLDER
    )

    return render_template(
        "sounds.html",
        files=files
    )


@app.route("/play", methods=["POST"])
@login_required
def route_play():
    filename = request.form[
        "filename"
    ]

    play_sound(filename)

    flash(f"Playing {filename}")
    return redirect(
        url_for("sounds")
    )


# ---------------- EMBEDS ----------------
@app.route(
    "/embed",
    methods=["GET", "POST"]
)
@login_required
def embed_page():
    if request.method == "POST":
        channel_id = request.form[
            "channel_id"
        ]
        title = request.form[
            "title"
        ]
        description = request.form[
            "description"
        ]

        send_embed(
            channel_id,
            title,
            description
        )

        flash("Embed sent.")

    return render_template(
        "embeds.html"
    )


# ---------------- USER ADMIN ----------------
@app.route(
    "/users",
    methods=["GET", "POST"]
)
@admin_required
def users():
    conn = db()

    with conn.cursor() as cursor:
        if request.method == "POST":
            username = request.form[
                "username"
            ]
            password = request.form[
                "password"
            ]

            cursor.execute("""
            INSERT INTO users
            (
                username,
                password,
                is_admin,
                can_upload,
                can_embed,
                can_vc,
                can_sound
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                username,
                generate_password_hash(
                    password
                ),
                "is_admin" in request.form,
                "can_upload" in request.form,
                "can_embed" in request.form,
                "can_vc" in request.form,
                "can_sound" in request.form
            ))

            flash("User created.")

        cursor.execute(
            "SELECT * FROM users"
        )
        users = cursor.fetchall()

    conn.close()

    return render_template(
        "users.html",
        users=users
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=2040,
        debug=False
    )