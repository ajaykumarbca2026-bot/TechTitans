from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect("verification.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS instruments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificate_id TEXT UNIQUE NOT NULL,
            instrument_name TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    existing = conn.execute(
        "SELECT COUNT(*) FROM instruments"
    ).fetchone()[0]

    if existing == 0:
        conn.execute("""
            INSERT INTO instruments
            (certificate_id, instrument_name, owner_name, status)
            VALUES (?, ?, ?, ?)
        """, (
            "TEST001",
            "Digital Weighing Machine",
            "ABC Traders",
            "Verified"
        ))

        conn.execute("""
            INSERT INTO instruments
            (certificate_id, instrument_name, owner_name, status)
            VALUES (?, ?, ?, ?)
        """, (
            "TEST002",
            "Digital Measuring Scale",
            "XYZ Store",
            "Pending"
        ))

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/verify", methods=["POST"])
def verify():
    instrument_id = request.form.get("instrument_id", "").strip()

    conn = get_db()

    record = conn.execute(
        "SELECT * FROM instruments WHERE certificate_id = ?",
        (instrument_id,)
    ).fetchone()

    conn.close()

    return render_template(
        "result.html",
        record=record,
        instrument_id=instrument_id
    )


@app.route("/admin")
def admin():
    return render_template("admin.html")


@app.route("/add", methods=["POST"])
def add_instrument():

    certificate_id = request.form.get("certificate_id", "").strip()
    instrument_name = request.form.get("instrument_name", "").strip()
    owner_name = request.form.get("owner_name", "").strip()
    status = request.form.get("status", "").strip()

    conn = get_db()

    try:
        conn.execute("""
            INSERT INTO instruments
            (certificate_id, instrument_name, owner_name, status)
            VALUES (?, ?, ?, ?)
        """, (
            certificate_id,
            instrument_name,
            owner_name,
            status
        ))

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()
        return """
        <h1>Error</h1>
        <p>This Certificate ID already exists.</p>
        <a href="/admin">Back to Admin Panel</a>
        """

    conn.close()

    return """
    <h1>Success!</h1>
    <p>Instrument has been added successfully.</p>
    <a href="/admin">Add Another</a>
    <br>
    <a href="/">Go to Home</a>
    """


if __name__ == "__main__":
    init_db()
    app.run(debug=True)