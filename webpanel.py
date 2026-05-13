from flask import (
    Flask, render_template, request,
    redirect, session, url_for, flash
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
import sqlite3
import os

from permissions import login_required, admin_required
from bot_api import (
    join_vc,
    leave_vc,
    play_sound,
    send_embed
)

app = Flask(__name__)
app.secret_key = "change_this"

UPLOAD_FOLDER = "sounds"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        is_admin INTEGER DEFAULT 0,
        can_upload INTEGER DEFAULT 0,
        can_embed INTEGER DEFAULT 0,
        can_vc INTEGER DEFAULT 0,
        can_sound INTEGER DEFAULT 0
    )
    """)

    conn.commit()

    existing = conn.execute(
        "SELECT * FROM users WHERE username=?",
        ("admin",)
    ).fetchone()

    if not existing:
        conn.execute("""
        INSERT INTO users
        (username,password,is_admin,can_upload,
         can_embed,can_vc,can_sound)
        VALUES (?,?,?,?,?,?,?)
        """, (
            "admin",
            generate_password_hash("admin123"),
            1, 1, 1, 1, 1
        ))
        conn.commit()

    conn.close()


init_db()


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
        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(
            user["password"], password
        ):
            session["user"] = user["username"]
            session["is_admin"] = user["is_admin"]
            return redirect(url_for("dashboard"))

        flash("Invalid login")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/join_vc", methods=["POST"])
@login_required
def route_join_vc():
    channel_id = int(request.form["channel_id"])
    join_vc(channel_id)
    return redirect(url_for("dashboard"))


@app.route("/leave_vc", methods=["POST"])
@login_required
def route_leave_vc():
    leave_vc()
    return redirect(url_for("dashboard"))


@app.route("/play", methods=["POST"])
@login_required
def route_play():
    filename = request.form["filename"]
    play_sound(filename)
    return redirect(url_for("sounds"))


@app.route("/sounds", methods=["GET", "POST"])
@login_required
def sounds():
    if request.method == "POST":
        file = request.files["file"]

        if file:
            file.save(
                os.path.join(
                    UPLOAD_FOLDER,
                    file.filename
                )
            )

    files = os.listdir(UPLOAD_FOLDER)
    return render_template(
        "sounds.html",
        files=files
    )


@app.route("/embed", methods=["GET", "POST"])
@login_required
def embed_page():
    if request.method == "POST":
        send_embed(
            request.form["channel_id"],
            request.form["title"],
            request.form["description"]
        )

    return render_template("embeds.html")


@app.route("/users", methods=["GET", "POST"])
@admin_required
def users():
    conn = db()

    if request.method == "POST":
        conn.execute("""
        INSERT INTO users
        (username,password,is_admin,can_upload,
         can_embed,can_vc,can_sound)
        VALUES (?,?,?,?,?,?,?)
        """, (
            request.form["username"],
            generate_password_hash(
                request.form["password"]
            ),
            int("is_admin" in request.form),
            int("can_upload" in request.form),
            int("can_embed" in request.form),
            int("can_vc" in request.form),
            int("can_sound" in request.form),
        ))
        conn.commit()

    users = conn.execute(
        "SELECT * FROM users"
    ).fetchall()
    conn.close()

    return render_template(
        "users.html",
        users=users
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2040)