import sqlite3
import io
import os
from datetime import date, datetime, timedelta
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, make_response, g)
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

app = Flask(__name__)
app.config.from_object(Config)

# ─────────────────────────────────────────────
# Database — supports PostgreSQL + SQLite
# ─────────────────────────────────────────────

def is_postgres():
    return bool(os.environ.get('DATABASE_URL'))

def get_db():
    if 'db' not in g:
        if is_postgres():
            import psycopg2
            db_url = os.environ['DATABASE_URL']
            # Ensure sslmode is set for Supabase
            if 'sslmode' not in db_url:
                db_url += '?sslmode=require'
            conn = psycopg2.connect(db_url)
            conn.autocommit = False
            g.db = conn
            g._db_type = 'pg'
        else:
            conn = sqlite3.connect(app.config['SQLITE_PATH'])
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            g.db = conn
            g._db_type = 'sqlite'
    return g.db

def db_execute(sql, params=()):
    db = get_db()
    if g._db_type == 'pg':
        import psycopg2.extras
        sql = sql.replace('?', '%s')
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cur = db.cursor()
    cur.execute(sql, params)
    return cur

def db_fetchone(sql, params=()):
    return db_execute(sql, params).fetchone()

def db_fetchall(sql, params=()):
    return db_execute(sql, params).fetchall()

def db_commit():
    get_db().commit()

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        if not is_postgres():
            db.close()
        else:
            try:
                db.close()
            except Exception:
                pass

def init_db():
    """Create tables and seed staff account."""
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        import psycopg2
        if 'sslmode' not in db_url:
            db_url += '?sslmode=require'
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Student (
                Roll_No  TEXT PRIMARY KEY,
                Name     TEXT NOT NULL,
                Password TEXT NOT NULL,
                Branch   TEXT NOT NULL,
                Email    TEXT UNIQUE,
                Phone    TEXT,
                Semester INTEGER,
                Subject  TEXT
            );
            CREATE TABLE IF NOT EXISTS Exam (
                Exam_ID  SERIAL PRIMARY KEY,
                Subject  TEXT NOT NULL,
                Date     TEXT NOT NULL,
                Time     TEXT NOT NULL,
                Duration TEXT DEFAULT '3 Hours',
                Semester INTEGER,
                Branch   TEXT
            );
            CREATE TABLE IF NOT EXISTS Allocation (
                Alloc_ID SERIAL PRIMARY KEY,
                Roll_No  TEXT NOT NULL REFERENCES Student(Roll_No) ON DELETE CASCADE,
                Exam_ID  INTEGER NOT NULL REFERENCES Exam(Exam_ID) ON DELETE CASCADE,
                Room_No  TEXT NOT NULL,
                Seat_No  TEXT NOT NULL,
                Block    TEXT,
                UNIQUE (Roll_No, Exam_ID)
            );
            CREATE TABLE IF NOT EXISTS Staff (
                Staff_ID SERIAL PRIMARY KEY,
                Name     TEXT NOT NULL,
                Email    TEXT NOT NULL UNIQUE,
                Password TEXT NOT NULL,
                Role     TEXT DEFAULT 'staff'
            );
        """)
        cur.execute("SELECT Staff_ID FROM Staff WHERE Email = %s",
                    ('raparthinithesh765@gmail.com',))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO Staff (Name, Email, Password, Role) VALUES (%s,%s,%s,%s)",
                ('Nithesh', 'raparthinithesh765@gmail.com',
                 generate_password_hash('admin123'), 'admin')
            )
            print("Staff account created: raparthinithesh765@gmail.com  /  admin123")
        conn.commit()
        conn.close()
        print("PostgreSQL database ready.")
    else:
        # SQLite path
        conn = sqlite3.connect(app.config['SQLITE_PATH'])
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS Student (
                Roll_No  TEXT PRIMARY KEY,
                Name     TEXT NOT NULL,
                Password TEXT NOT NULL,
                Branch   TEXT NOT NULL,
                Email    TEXT UNIQUE,
                Phone    TEXT,
                Semester INTEGER,
                Subject  TEXT
            );
            CREATE TABLE IF NOT EXISTS Exam (
                Exam_ID  INTEGER PRIMARY KEY AUTOINCREMENT,
                Subject  TEXT NOT NULL,
                Date     TEXT NOT NULL,
                Time     TEXT NOT NULL,
                Duration TEXT DEFAULT '3 Hours',
                Semester INTEGER,
                Branch   TEXT
            );
            CREATE TABLE IF NOT EXISTS Allocation (
                Alloc_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Roll_No  TEXT NOT NULL,
                Exam_ID  INTEGER NOT NULL,
                Room_No  TEXT NOT NULL,
                Seat_No  TEXT NOT NULL,
                Block    TEXT,
                FOREIGN KEY (Roll_No) REFERENCES Student(Roll_No) ON DELETE CASCADE,
                FOREIGN KEY (Exam_ID) REFERENCES Exam(Exam_ID) ON DELETE CASCADE,
                UNIQUE (Roll_No, Exam_ID)
            );
            CREATE TABLE IF NOT EXISTS Staff (
                Staff_ID  INTEGER PRIMARY KEY AUTOINCREMENT,
                Name      TEXT NOT NULL,
                Email     TEXT NOT NULL UNIQUE,
                Password  TEXT NOT NULL,
                Role      TEXT DEFAULT 'staff'
            );
        """)
        cur = conn.cursor()
        cur.execute("SELECT Staff_ID FROM Staff WHERE Email = ?",
                    ('raparthinithesh765@gmail.com',))
        if not cur.fetchone():
            conn.execute(
                "INSERT INTO Staff (Name, Email, Password, Role) VALUES (?,?,?,?)",
                ('Nithesh', 'raparthinithesh765@gmail.com',
                 generate_password_hash('admin123'), 'admin')
            )
            print("Staff account created: raparthinithesh765@gmail.com  /  admin123")
        conn.commit()
        conn.close()
        print("SQLite database ready:", app.config['SQLITE_PATH'])

# ─────────────────────────────────────────────
# Auth decorators
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# Helper — check if allocation is unlocked
# Unlocks 1 hour before exam time on exam date
# ─────────────────────────────────────────────

def is_unlocked(exam_date_str, exam_time_str):
    """Return True if current time >= exam datetime minus 1 hour."""
    try:
        # Try common time formats: "09:00 AM", "09:00", "9:00 AM"
        for fmt in ('%I:%M %p', '%H:%M', '%I:%M%p'):
            try:
                t = datetime.strptime(exam_time_str.strip(), fmt)
                break
            except ValueError:
                continue
        else:
            # If time can't be parsed, fall back to date-only check
            return exam_date_str <= date.today().isoformat()

        exam_dt = datetime.combine(
            datetime.strptime(exam_date_str, '%Y-%m-%d').date(),
            t.time()
        )
        unlock_dt = exam_dt - timedelta(hours=1)
        return datetime.now() >= unlock_dt
    except Exception:
        # Safe fallback — if anything fails, use date-only
        return exam_date_str <= date.today().isoformat()


def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'student_roll' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('student_login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Staff access required.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────
# Landing
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

# ─────────────────────────────────────────────
# Student Routes
# ─────────────────────────────────────────────

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if 'student_roll' in session:
        return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password   = request.form.get('password', '').strip()

        if not identifier or not password:
            flash('Please enter your Roll Number / Email and Password.', 'danger')
            return render_template('student/login.html')

        db = get_db()

        # Support login via Roll No OR Email
        student = db_fetchone(
            "SELECT * FROM Student WHERE Roll_No = ? OR (Email IS NOT NULL AND Email = ?)",
            (identifier.upper(), identifier.lower())
        )

        if student and check_password_hash(student['Password'], password):
            session['student_roll'] = student['Roll_No']
            session['student_name'] = student['Name']
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid credentials. Please check your Roll Number / Email and Password.', 'danger')

    return render_template('student/login.html')


@app.route('/student/dashboard')
@student_required
def student_dashboard():
    roll_no = session['student_roll']
    db = get_db()
    student = db_fetchone(
        "SELECT * FROM Student WHERE Roll_No = ?", (roll_no,)
    )
    allocations = db_fetchall("""
        SELECT a.*, e.Subject, e.Date, e.Time, e.Duration
        FROM Allocation a
        JOIN Exam e ON a.Exam_ID = e.Exam_ID
        WHERE a.Roll_No = ?
        ORDER BY e.Date ASC
    """, (roll_no,))

    # Build unlock status per allocation
    unlock_map = {
        a['Exam_ID']: is_unlocked(a['Date'], a['Time'])
        for a in allocations
    }

    return render_template('student/dashboard.html',
                           student=student,
                           allocations=allocations,
                           unlock_map=unlock_map,
                           today_date=date.today().isoformat())


@app.route('/student/allocation/<int:exam_id>')
@student_required
def student_allocation(exam_id):
    roll_no = session['student_roll']
    db = get_db()
    detail = db_fetchone("""
        SELECT a.*, e.Subject, e.Date, e.Time, e.Duration,
               s.Name, s.Branch, s.Semester
        FROM Allocation a
        JOIN Exam e ON a.Exam_ID = e.Exam_ID
        JOIN Student s ON a.Roll_No = s.Roll_No
        WHERE a.Roll_No = ? AND a.Exam_ID = ?
    """, (roll_no, exam_id))

    if not detail:
        flash('Allocation not found.', 'danger')
        return redirect(url_for('student_dashboard'))

    if not is_unlocked(detail['Date'], detail['Time']):
        flash('Room allocation details will be available 1 hour before the exam.', 'warning')
        return redirect(url_for('student_dashboard'))

    return render_template('student/allocation.html', detail=detail)


@app.route('/student/download/<int:exam_id>')
@student_required
def download_slip(exam_id):
    roll_no = session['student_roll']
    db = get_db()
    detail = db_fetchone("""
        SELECT a.*, e.Subject, e.Date, e.Time, e.Duration,
               s.Name, s.Branch, s.Semester
        FROM Allocation a
        JOIN Exam e ON a.Exam_ID = e.Exam_ID
        JOIN Student s ON a.Roll_No = s.Roll_No
        WHERE a.Roll_No = ? AND a.Exam_ID = ?
    """, (roll_no, exam_id))

    if not detail:
        flash('Allocation not found.', 'danger')
        return redirect(url_for('student_dashboard'))

    if not is_unlocked(detail['Date'], detail['Time']):
        flash('Hall ticket will be available 1 hour before the exam.', 'warning')
        return redirect(url_for('student_dashboard'))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                  fontSize=16, spaceAfter=4,
                                  alignment=TA_CENTER,
                                  textColor=colors.HexColor('#1a1a1a'))
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'],
                                fontSize=10, spaceAfter=4, alignment=TA_CENTER,
                                textColor=colors.HexColor('#555555'))

    elements = []
    elements.append(Paragraph("ONLINE EXAMINATION HALL ALLOCATION", title_style))
    elements.append(Paragraph("Hall Allocation Slip", sub_style))
    elements.append(Spacer(1, 0.5*cm))

    data = [
        ['Field', 'Details'],
        ['Student Name', detail['Name']],
        ['Roll Number',  detail['Roll_No']],
        ['Branch',       detail['Branch']],
        ['Subject',      detail['Subject']],
        ['Exam Date',    detail['Date']],
        ['Exam Time',    detail['Time']],
        ['Duration',     detail['Duration']],
        ['Block',        detail['Block'] or '-'],
        ['Room Number',  detail['Room_No']],
        ['Seat Number',  detail['Seat_No']],
    ]

    table = Table(data, colWidths=[6*cm, 10*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 11),
        ('ALIGN',         (0, 0), (-1, -1), 'LEFT'),
        ('PADDING',       (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1),
         [colors.HexColor('#f5f5f5'), colors.white]),
        ('FONTNAME',      (0, 1), (0, -1), 'Helvetica-Bold'),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(
        "* Carry this slip and your college ID card to the examination hall. "
        "Latecomers will not be permitted after 30 minutes.",
        styles['Italic']))
    doc.build(elements)

    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = \
        f'attachment; filename=HallSlip_{roll_no}_{exam_id}.pdf'
    return response


@app.route('/student/logout')
def student_logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ─────────────────────────────────────────────
# Admin / Staff Routes
# ─────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        db = get_db()
        staff = db_fetchone(
            "SELECT * FROM Staff WHERE Email = ?", (email,)
        )

        if staff and check_password_hash(staff['Password'], password):
            session['admin_logged_in'] = True
            session['admin_name']  = staff['Name']
            session['admin_email'] = staff['Email']
            session['admin_role']  = staff['Role']
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('admin/login.html')


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    db = get_db()
    student_count = db_fetchone("SELECT COUNT(*) as cnt FROM Student")['cnt']
    exam_count    = db_fetchone("SELECT COUNT(*) as cnt FROM Exam")['cnt']
    alloc_count   = db_fetchone("SELECT COUNT(*) as cnt FROM Allocation")['cnt']

    recent_exams = db_fetchall("""
        SELECT e.Subject, e.Date, e.Time, COUNT(a.Roll_No) AS enrolled
        FROM Exam e
        LEFT JOIN Allocation a ON e.Exam_ID = a.Exam_ID
        GROUP BY e.Exam_ID, e.Subject, e.Date, e.Time
        ORDER BY e.Date ASC
        LIMIT 5
    """)

    return render_template('admin/dashboard.html',
                           student_count=student_count,
                           exam_count=exam_count,
                           alloc_count=alloc_count,
                           recent_exams=recent_exams)


# ── Students ──

@app.route('/admin/students')
@admin_required
def admin_students():
    db = get_db()
    students = db_fetchall("SELECT * FROM Student ORDER BY Roll_No")
    return render_template('admin/students.html', students=students)


@app.route('/admin/students/add', methods=['POST'])
@admin_required
def admin_add_student():
    roll_no  = request.form.get('roll_no', '').strip().upper()
    name     = request.form.get('name', '').strip()
    password = request.form.get('password', '').strip()
    branch   = request.form.get('branch', '').strip()
    email    = request.form.get('email', '').strip().lower()
    phone    = request.form.get('phone', '').strip()
    semester = request.form.get('semester', 1)
    subject  = request.form.get('subject', '').strip()

    if not all([roll_no, name, password, branch]):
        flash('Roll No, Name, Password and Branch are required.', 'danger')
        return redirect(url_for('admin_students'))

    try:
        db = get_db()
        hashed = generate_password_hash(password)
        db_execute("""
            INSERT INTO Student (Roll_No, Name, Password, Branch, Email, Phone, Semester, Subject)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (roll_no, name, hashed, branch, email or None, phone or None, semester, subject or None))
        db_commit()
        flash(f'Student {name} ({roll_no}) added.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')

    return redirect(url_for('admin_students'))


@app.route('/admin/students/delete/<roll_no>', methods=['POST'])
@admin_required
def admin_delete_student(roll_no):
    try:
        db = get_db()
        db_execute("DELETE FROM Student WHERE Roll_No = ?", (roll_no,))
        db_commit()
        flash('Student removed.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin_students'))


# ── Exams ──

@app.route('/admin/exams')
@admin_required
def admin_exams():
    db = get_db()
    exams = db_fetchall("""
        SELECT e.*, COUNT(a.Roll_No) AS enrolled
        FROM Exam e
        LEFT JOIN Allocation a ON e.Exam_ID = a.Exam_ID
        GROUP BY e.Exam_ID, e.Subject, e.Date, e.Time, e.Duration, e.Semester, e.Branch
        ORDER BY e.Date ASC
    """)
    return render_template('admin/exams.html', exams=exams)


@app.route('/admin/exams/add', methods=['POST'])
@admin_required
def admin_add_exam():
    subject  = request.form.get('subject', '').strip()
    date     = request.form.get('date', '').strip()
    time_val = request.form.get('time', '').strip()
    duration = request.form.get('duration', '3 Hours').strip()
    semester = request.form.get('semester', 1)
    branch   = request.form.get('branch', '').strip()

    if not all([subject, date, time_val]):
        flash('Subject, Date and Time are required.', 'danger')
        return redirect(url_for('admin_exams'))

    try:
        db = get_db()
        db_execute("""
            INSERT INTO Exam (Subject, Date, Time, Duration, Semester, Branch)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (subject, date, time_val, duration, semester, branch))
        db_commit()
        flash(f'Exam "{subject}" scheduled.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')

    return redirect(url_for('admin_exams'))


@app.route('/admin/exams/delete/<int:exam_id>', methods=['POST'])
@admin_required
def admin_delete_exam(exam_id):
    try:
        db = get_db()
        db_execute("DELETE FROM Exam WHERE Exam_ID = ?", (exam_id,))
        db_commit()
        flash('Exam deleted.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin_exams'))


@app.route('/admin/exams/edit/<int:exam_id>', methods=['POST'])
@admin_required
def admin_edit_exam(exam_id):
    subject  = request.form.get('subject', '').strip()
    date     = request.form.get('date', '').strip()
    time_val = request.form.get('time', '').strip()
    duration = request.form.get('duration', '3 Hours').strip()
    semester = request.form.get('semester', 1)
    branch   = request.form.get('branch', '').strip()

    if not all([subject, date, time_val]):
        flash('Subject, Date and Time are required.', 'danger')
        return redirect(url_for('admin_exams'))

    try:
        db = get_db()
        db_execute("""
            UPDATE Exam SET Subject=?, Date=?, Time=?, Duration=?, Semester=?, Branch=?
            WHERE Exam_ID=?
        """, (subject, date, time_val, duration, semester, branch, exam_id))
        db_commit()
        flash(f'Exam "{subject}" updated.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin_exams'))


# ── Allocations ──

@app.route('/admin/allocations')
@admin_required
def admin_allocations():
    db = get_db()
    allocations = db_fetchall("""
        SELECT a.*, s.Name, e.Subject, e.Date, e.Time
        FROM Allocation a
        JOIN Student s ON a.Roll_No = s.Roll_No
        JOIN Exam e ON a.Exam_ID = e.Exam_ID
        ORDER BY e.Date ASC, a.Room_No, a.Seat_No
    """)

    students = db_fetchall(
        "SELECT Roll_No, Name FROM Student ORDER BY Roll_No"
    )

    exams = db_fetchall(
        "SELECT Exam_ID, Subject, Date FROM Exam ORDER BY Date"
    )

    return render_template('admin/allocations.html',
                           allocations=allocations,
                           students=students, exams=exams)


@app.route('/admin/allocations/add', methods=['POST'])
@admin_required
def admin_add_allocation():
    roll_no = request.form.get('roll_no', '').strip().upper()
    exam_id = request.form.get('exam_id', '').strip()
    room_no = request.form.get('room_no', '').strip().upper()
    seat_no = request.form.get('seat_no', '').strip().upper()
    block   = request.form.get('block', '').strip()

    if not all([roll_no, exam_id, room_no, seat_no]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('admin_allocations'))

    try:
        db = get_db()
        db_execute("""
            INSERT INTO Allocation (Roll_No, Exam_ID, Room_No, Seat_No, Block)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(Roll_No, Exam_ID)
            DO UPDATE SET Room_No=EXCLUDED.Room_No,
                          Seat_No=EXCLUDED.Seat_No,
                          Block=EXCLUDED.Block
        """, (roll_no, exam_id, room_no, seat_no, block))
        db_commit()
        flash('Allocation saved.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')

    return redirect(url_for('admin_allocations'))


@app.route('/admin/allocations/delete/<int:alloc_id>', methods=['POST'])
@admin_required
def admin_delete_allocation(alloc_id):
    try:
        db = get_db()
        db_execute("DELETE FROM Allocation WHERE Alloc_ID = ?", (alloc_id,))
        db_commit()
        flash('Allocation removed.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin_allocations'))


@app.route('/admin/allocations/edit/<int:alloc_id>', methods=['POST'])
@admin_required
def admin_edit_allocation(alloc_id):
    room_no = request.form.get('room_no', '').strip().upper()
    seat_no = request.form.get('seat_no', '').strip().upper()
    block   = request.form.get('block', '').strip()

    if not all([room_no, seat_no]):
        flash('Room Number and Seat Number are required.', 'danger')
        return redirect(url_for('admin_allocations'))

    try:
        db = get_db()
        db_execute("""
            UPDATE Allocation SET Room_No=?, Seat_No=?, Block=?
            WHERE Alloc_ID=?
        """, (room_no, seat_no, block, alloc_id))
        db_commit()
        flash('Allocation updated.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin_allocations'))


# ── Staff management (admin-only) ──

@app.route('/admin/staff')
@admin_required
def admin_staff():
    db = get_db()
    staff_list = db_fetchall("SELECT * FROM Staff ORDER BY Name")
    return render_template('admin/staff.html', staff_list=staff_list)


@app.route('/admin/staff/add', methods=['POST'])
@admin_required
def admin_add_staff():
    name     = request.form.get('name', '').strip()
    email    = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip()
    role     = request.form.get('role', 'staff').strip()

    if not all([name, email, password]):
        flash('Name, Email and Password are required.', 'danger')
        return redirect(url_for('admin_staff'))

    try:
        db = get_db()
        db_execute(
            "INSERT INTO Staff (Name, Email, Password, Role) VALUES (?, ?, ?, ?)",
            (name, email, generate_password_hash(password), role)
        )
        db_commit()
        flash(f'Staff account created for {email}.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')

    return redirect(url_for('admin_staff'))


@app.route('/admin/staff/delete/<int:staff_id>', methods=['POST'])
@admin_required
def admin_delete_staff(staff_id):
    # Prevent deleting your own account
    if session.get('admin_email') == request.form.get('email'):
        flash('You cannot remove your own account.', 'danger')
        return redirect(url_for('admin_staff'))
    try:
        db = get_db()
        db_execute("DELETE FROM Staff WHERE Staff_ID = ?", (staff_id,))
        db_commit()
        flash('Staff account removed.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin_staff'))


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('index'))


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

# Always init DB — works for both gunicorn (Render) and direct python run
with app.app_context():
    init_db()

if __name__ == '__main__':
    print("Server running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000, use_reloader=False)
