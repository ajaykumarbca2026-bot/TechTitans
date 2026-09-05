from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
import os
import io
import qrcode

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "techtitans_secret_key_2026"
)


# ============================================================
# DATABASE
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "verification.db")


def get_db():
    conn = sqlite3.connect(DATABASE)
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

        demo_records = [
            (
                "TEST001",
                "Digital Weighing Machine",
                "ABC Traders",
                "Verified"
            ),
            (
                "TEST002",
                "Digital Measuring Scale",
                "XYZ Store",
                "Pending"
            ),
            (
                "TEST003",
                "Electronic Weighing Machine",
                "TechTitans Demo",
                "Verified"
            )
        ]

        conn.executemany("""
            INSERT INTO instruments
            (
                certificate_id,
                instrument_name,
                owner_name,
                status
            )
            VALUES (?, ?, ?, ?)
        """, demo_records)

    conn.commit()
    conn.close()


# IMPORTANT:
# Render/Gunicorn does NOT necessarily execute
# "if __name__ == '__main__'"
# Therefore database initialization must happen here.

init_db()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


# ============================================================
# VERIFY
# ============================================================

@app.route("/verify", methods=["POST"])
def verify():

    instrument_id = request.form.get(
        "instrument_id",
        ""
    ).strip()

    conn = get_db()

    record = conn.execute(
        """
        SELECT *
        FROM instruments
        WHERE certificate_id = ?
        """,
        (instrument_id,)
    ).fetchone()

    conn.close()

    # URL that can be encoded into QR
    verify_url = url_for(
        "verify_by_qr",
        certificate_id=instrument_id,
        _external=True
    )

    return render_template(
        "result.html",
        record=record,
        instrument_id=instrument_id,
        verify_url=verify_url
    )


# ============================================================
# QR VERIFICATION
# ============================================================

@app.route("/verify/<certificate_id>")
def verify_by_qr(certificate_id):

    certificate_id = certificate_id.strip()

    conn = get_db()

    record = conn.execute(
        """
        SELECT *
        FROM instruments
        WHERE certificate_id = ?
        """,
        (certificate_id,)
    ).fetchone()

    conn.close()

    verify_url = url_for(
        "verify_by_qr",
        certificate_id=certificate_id,
        _external=True
    )

    return render_template(
        "result.html",
        record=record,
        instrument_id=certificate_id,
        verify_url=verify_url
    )


# ============================================================
# QR CODE IMAGE
# ============================================================

@app.route("/qr/<certificate_id>")
def generate_qr(certificate_id):

    verify_url = url_for(
        "verify_by_qr",
        certificate_id=certificate_id,
        _external=True
    )

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )

    qr.add_data(verify_url)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    image_stream = io.BytesIO()
    img.save(image_stream, format="PNG")
    image_stream.seek(0)

    return send_file(
        image_stream,
        mimetype="image/png"
    )


# ============================================================
# ADMIN PANEL
# ============================================================

@app.route("/admin")
def admin():

    if not session.get("logged_in"):
        return redirect(url_for("admin_login"))

    search = request.args.get(
        "search",
        ""
    ).strip()

    status_filter = request.args.get(
        "status",
        ""
    ).strip()

    conn = get_db()

    query = """
        SELECT *
        FROM instruments
        WHERE 1=1
    """

    params = []

    if search:

        query += """
            AND (
                certificate_id LIKE ?
                OR instrument_name LIKE ?
                OR owner_name LIKE ?
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value
        ])

    if status_filter:

        query += """
            AND status = ?
        """

        params.append(status_filter)

    query += """
        ORDER BY id DESC
    """

    records = conn.execute(
        query,
        params
    ).fetchall()

    total_records = conn.execute(
        """
        SELECT COUNT(*)
        FROM instruments
        """
    ).fetchone()[0]

    verified_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM instruments
        WHERE status = ?
        """,
        ("Verified",)
    ).fetchone()[0]

    pending_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM instruments
        WHERE status = ?
        """,
        ("Pending",)
    ).fetchone()[0]

    rejected_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM instruments
        WHERE status = ?
        """,
        ("Rejected",)
    ).fetchone()[0]

    conn.close()

    return render_template(
        "admin.html",
        records=records,
        total_records=total_records,
        verified_count=verified_count,
        pending_count=pending_count,
        rejected_count=rejected_count,
        search=search,
        status_filter=status_filter
    )


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        if (
            username == "admin"
            and password == "1234"
        ):

            session["logged_in"] = True

            return redirect(
                url_for("admin")
            )

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("admin_login")
    )


# ============================================================
# ADD INSTRUMENT
# ============================================================

@app.route(
    "/add",
    methods=["POST"]
)
def add_instrument():

    if not session.get("logged_in"):
        return redirect(
            url_for("admin_login")
        )

    certificate_id = request.form.get(
        "certificate_id",
        ""
    ).strip()

    instrument_name = request.form.get(
        "instrument_name",
        ""
    ).strip()

    owner_name = request.form.get(
        "owner_name",
        ""
    ).strip()

    status = request.form.get(
        "status",
        ""
    ).strip()

    if not certificate_id or not instrument_name or not owner_name or not status:
        return """
        <h1>Error</h1>
        <p>All fields are required.</p>
        <br>
        <a href="/admin">Back to Admin Panel</a>
        """

    conn = get_db()

    try:

        conn.execute(
            """
            INSERT INTO instruments
            (
                certificate_id,
                instrument_name,
                owner_name,
                status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                certificate_id,
                instrument_name,
                owner_name,
                status
            )
        )

        conn.commit()

    except sqlite3.IntegrityError:

        conn.close()

        return """
        <h1>Error</h1>
        <p>This Certificate ID already exists.</p>
        <br>
        <a href="/admin">Back to Admin Panel</a>
        """

    conn.close()

    return redirect(
        url_for("admin")
    )


# ============================================================
# EDIT PAGE
# ============================================================

@app.route(
    "/edit/<int:record_id>"
)
def edit_instrument(record_id):

    if not session.get("logged_in"):
        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    record = conn.execute(
        """
        SELECT *
        FROM instruments
        WHERE id = ?
        """,
        (record_id,)
    ).fetchone()

    conn.close()

    if record is None:
        return "Record not found."

    return render_template(
        "edit.html",
        record=record
    )


# ============================================================
# UPDATE
# ============================================================

@app.route(
    "/update/<int:record_id>",
    methods=["POST"]
)
def update_instrument(record_id):

    if not session.get("logged_in"):
        return redirect(
            url_for("admin_login")
        )

    certificate_id = request.form.get(
        "certificate_id",
        ""
    ).strip()

    instrument_name = request.form.get(
        "instrument_name",
        ""
    ).strip()

    owner_name = request.form.get(
        "owner_name",
        ""
    ).strip()

    status = request.form.get(
        "status",
        ""
    ).strip()

    conn = get_db()

    try:

        conn.execute(
            """
            UPDATE instruments

            SET
                certificate_id = ?,
                instrument_name = ?,
                owner_name = ?,
                status = ?

            WHERE id = ?
            """,
            (
                certificate_id,
                instrument_name,
                owner_name,
                status,
                record_id
            )
        )

        conn.commit()

    except sqlite3.IntegrityError:

        conn.close()

        return """
        <h1>Error</h1>
        <p>This Certificate ID already exists.</p>
        <br>
        <a href="/admin">Back to Admin Panel</a>
        """

    conn.close()

    return redirect(
        url_for("admin")
    )


# ============================================================
# DELETE
# ============================================================

@app.route(
    "/delete/<int:record_id>",
    methods=["POST"]
)
def delete_instrument(record_id):

    if not session.get("logged_in"):
        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    conn.execute(
        """
        DELETE FROM instruments
        WHERE id = ?
        """,
        (record_id,)
    )

    conn.commit()
    conn.close()

    return redirect(
        url_for("admin")
    )


# ============================================================
# RUN LOCAL SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )