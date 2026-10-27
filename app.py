"""VaultLite - offline password manager (Flask + SQLite + Fernet).
Runs inside a desktop window via launcher.py; can also run in a browser with `python app.py`."""
import base64
import os
import secrets
import sqlite3
import string
import sys
import time
from functools import wraps
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from flask import (Flask, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import licensing
import product


def resource_path(rel):
    """Find bundled files both in normal Python and inside the PyInstaller build."""
    base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base, rel)


def data_dir():
    """User data lives OUTSIDE the install folder, so updates/uninstalls never touch it."""
    override = os.environ.get("VAULTLITE_DATA")
    if override:
        path = override
    elif os.name == "nt":
        path = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), product.APP_NAME)
    else:
        path = os.path.join(os.path.expanduser("~"), "." + product.APP_NAME.lower())
    os.makedirs(path, exist_ok=True)
    return path


DATA_DIR = data_dir()
DATABASE = os.path.join(DATA_DIR, "vault.db")
LICENSE_FILE = os.path.join(DATA_DIR, "license.key")

app = Flask(__name__, template_folder=resource_path("templates"),
            static_folder=resource_path("static"))
app.secret_key = secrets.token_hex(32)           # new every launch -> you are logged out on restart
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
                  PERMANENT_SESSION_LIFETIME=15 * 60)   # auto-lock after 15 min of inactivity
app.config["ALLOWED_HOSTS"] = None               # launcher sets this to the real 127.0.0.1:port

VAULT_KEYS = {}      # user_id -> Fernet, kept in memory only while logged in. Never written to disk.
LAST_HEARTBEAT = {"t": None}


# ---------------------------------------------------------------
# 1. ENCRYPTION - the key is DERIVED from the master password (scrypt),
#    so nothing on disk can decrypt the vault without it.
# ---------------------------------------------------------------
def derive_fernet(master_password, salt):
    key = Scrypt(salt=salt, length=32, n=2 ** 15, r=8, p=1).derive(master_password.encode())
    return Fernet(base64.urlsafe_b64encode(key))

def encrypt_text(plain_text):
    return VAULT_KEYS[session["user_id"]].encrypt(plain_text.encode()).decode()

def decrypt_text(encrypted_text):
    try:
        return VAULT_KEYS[session["user_id"]].decrypt(encrypted_text.encode()).decode()
    except InvalidToken:
        return ""


# ---------------------------------------------------------------
# 2. DATABASE
# ---------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            master_hash TEXT NOT NULL,
            enc_salt BLOB NOT NULL
        );
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            website TEXT NOT NULL,
            login_name TEXT NOT NULL,
            encrypted_password TEXT NOT NULL,
            url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    """)
    db.commit()
    db.close()


# ---------------------------------------------------------------
# 3. LICENSE / TRIAL
# ---------------------------------------------------------------
def current_license():
    return licensing.load_license(LICENSE_FILE)

@app.context_processor
def inject_globals():
    lic = current_license()
    return dict(license_info=lic, trial_max=product.TRIAL_MAX_ENTRIES,
                app_name=product.APP_NAME, app_version=product.APP_VERSION,
                support_email=product.SUPPORT_EMAIL)

@app.route("/activate", methods=["GET", "POST"])
def activate():
    if request.method == "POST":
        key = request.form.get("key", "")
        info = licensing.verify_key(key)
        if info:
            licensing.save_license(LICENSE_FILE, key)
            flash(f"Activated. Thank you, {info.get('name', '')}!", "success")
            return redirect(url_for("home"))
        flash("That license key is not valid. Check it was copied completely.", "error")
    return render_template("activate.html")


# ---------------------------------------------------------------
# 4. SECURITY GUARDS
# ---------------------------------------------------------------
@app.before_request
def guard():
    allowed = app.config["ALLOWED_HOSTS"]
    if allowed and request.host not in allowed:            # blocks DNS-rebinding tricks
        return "Forbidden", 403
    if request.method == "POST":                           # blocks other websites posting to us
        origin = request.headers.get("Origin")
        if origin and urlparse(origin).netloc != request.host:
            return "Forbidden", 403
    session.permanent = True                               # refreshes the inactivity timer

@app.after_request
def no_cache(resp):
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'"
    return resp

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        uid = session.get("user_id")
        if uid is None or uid not in VAULT_KEYS:           # key gone (app restarted) -> log in again
            session.clear()
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def get_own_credential(cred_id):
    return get_db().execute("SELECT * FROM credentials WHERE id = ? AND user_id = ?",
                            (cred_id, session["user_id"])).fetchone()

@app.route("/_hb")
def heartbeat():
    LAST_HEARTBEAT["t"] = time.time()
    return "ok"


# ---------------------------------------------------------------
# 5. REGISTER / LOGIN / LOGOUT
# ---------------------------------------------------------------
@app.route("/")
def home():
    return redirect(url_for("dashboard" if "user_id" in session else "login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if len(username) < 3 or len(password) < 8:
            flash("Username needs 3+ characters and master password 8+.", "error")
        else:
            try:
                get_db().execute(
                    "INSERT INTO users (username, master_hash, enc_salt) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password), os.urandom(16)))
                get_db().commit()
                flash("Account created. You can log in now.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That username is already taken.", "error")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = get_db().execute("SELECT * FROM users WHERE username = ?",
                                (request.form["username"].strip(),)).fetchone()
        if user and check_password_hash(user["master_hash"], request.form["password"]):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            VAULT_KEYS[user["id"]] = derive_fernet(request.form["password"], user["enc_salt"])
            return redirect(url_for("dashboard"))
        flash("Wrong username or master password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    VAULT_KEYS.pop(session.get("user_id"), None)           # forget the key immediately
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------
# 6. DASHBOARD + VAULT
# ---------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    db, uid = get_db(), session["user_id"]
    total = db.execute("SELECT COUNT(*) FROM credentials WHERE user_id = ?", (uid,)).fetchone()[0]
    sites = db.execute("SELECT COUNT(DISTINCT LOWER(website)) FROM credentials WHERE user_id = ?",
                       (uid,)).fetchone()[0]
    recent = db.execute("SELECT * FROM credentials WHERE user_id = ? ORDER BY id DESC LIMIT 5",
                        (uid,)).fetchall()
    return render_template("dashboard.html", total=total, sites=sites, recent=recent)

@app.route("/passwords")
@login_required
def passwords():
    search = request.args.get("q", "").strip()
    rows = get_db().execute(
        "SELECT * FROM credentials WHERE user_id = ? AND website LIKE ? ORDER BY website",
        (session["user_id"], f"%{search}%")).fetchall()
    return render_template("passwords.html", rows=rows, search=search)

@app.route("/add", methods=["GET", "POST"])
@login_required
def add_password():
    if request.method == "POST":
        if not current_license():
            count = get_db().execute("SELECT COUNT(*) FROM credentials").fetchone()[0]
            if count >= product.TRIAL_MAX_ENTRIES:
                flash(f"Trial limit reached ({product.TRIAL_MAX_ENTRIES} passwords). "
                      "Enter a license key to unlock unlimited.", "error")
                return redirect(url_for("activate"))
        f = request.form
        get_db().execute(
            "INSERT INTO credentials (user_id, website, login_name, encrypted_password, url) "
            "VALUES (?, ?, ?, ?, ?)",
            (session["user_id"], f["website"].strip(), f["login_name"].strip(),
             encrypt_text(f["password"]), f["url"].strip()))
        get_db().commit()
        flash("Password saved.", "success")
        return redirect(url_for("passwords"))
    return render_template("add_password.html")

@app.route("/edit/<int:cred_id>", methods=["GET", "POST"])
@login_required
def edit_password(cred_id):
    cred = get_own_credential(cred_id)
    if cred is None:
        flash("Entry not found.", "error")
        return redirect(url_for("passwords"))
    if request.method == "POST":
        f = request.form
        get_db().execute(
            "UPDATE credentials SET website=?, login_name=?, encrypted_password=?, url=? "
            "WHERE id=? AND user_id=?",
            (f["website"].strip(), f["login_name"].strip(), encrypt_text(f["password"]),
             f["url"].strip(), cred_id, session["user_id"]))
        get_db().commit()
        flash("Entry updated.", "success")
        return redirect(url_for("passwords"))
    return render_template("edit_password.html", cred=cred,
                           password=decrypt_text(cred["encrypted_password"]))

@app.route("/delete/<int:cred_id>", methods=["POST"])
@login_required
def delete_password(cred_id):
    get_db().execute("DELETE FROM credentials WHERE id=? AND user_id=?",
                     (cred_id, session["user_id"]))
    get_db().commit()
    flash("Entry deleted.", "success")
    return redirect(url_for("passwords"))

@app.route("/reveal/<int:cred_id>")
@login_required
def reveal(cred_id):
    cred = get_own_credential(cred_id)
    if cred is None:
        return jsonify(error="Not found"), 404
    return jsonify(password=decrypt_text(cred["encrypted_password"]))


# ---------------------------------------------------------------
# 7. PASSWORD GENERATOR
# ---------------------------------------------------------------
@app.route("/generator")
@login_required
def generator():
    return render_template("generator.html")

@app.route("/api/generate")
@login_required
def api_generate():
    length = max(8, min(32, request.args.get("length", 16, type=int)))
    pools = []
    if request.args.get("upper") == "1":   pools.append(string.ascii_uppercase)
    if request.args.get("lower") == "1":   pools.append(string.ascii_lowercase)
    if request.args.get("numbers") == "1": pools.append(string.digits)
    if request.args.get("symbols") == "1": pools.append("!@#$%^&*()-_=+[]{}?")
    if not pools:
        return jsonify(error="Select at least one character type."), 400
    chars = [secrets.choice(p) for p in pools]
    all_chars = "".join(pools)
    chars += [secrets.choice(all_chars) for _ in range(length - len(chars))]
    secrets.SystemRandom().shuffle(chars)
    return jsonify(password="".join(chars))


init_db()

if __name__ == "__main__":          # developer mode: python app.py -> open http://127.0.0.1:5000
    app.run(host="127.0.0.1", port=5000)
