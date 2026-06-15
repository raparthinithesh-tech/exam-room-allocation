# Online Examination Hall Allocation Portal

A full-stack web portal built with **Flask + MySQL** that lets students instantly look up their exam room, seat number, date and time — no more crowding at notice boards.

---

## Quick Start

### 1. Install MySQL and create the database
```bash
mysql -u root -p < schema.sql
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure database credentials
Edit `config.py` or set environment variables:
```bash
set MYSQL_HOST=localhost
set MYSQL_USER=root
set MYSQL_PASSWORD=your_password
set MYSQL_DB=exam_portal
```

### 4. Run the application
```bash
python app.py
```

Open http://localhost:5000 in your browser.

---

## Default Credentials

| Role    | Username / Roll No | Password  |
|---------|-------------------|-----------|
| Admin   | admin             | admin123  |
| Student | CS001             | pass123   |
| Student | CS002             | pass123   |
| Student | EC001             | pass123   |
| Student | ME001             | pass123   |

---

## Features

### Student Portal
- Login with Roll Number and Password
- View all exam allocations (room, seat, block, date, time)
- View detailed allocation slip per exam
- Download printable PDF hall slip
- Print allocation slip directly from browser

### Admin Portal
- Dashboard with statistics (student count, exam count, allocations)
- Add / delete students
- Schedule / delete exams
- Create / remove hall allocations
- Search across all allocations in real time

---

## Project Structure
```
exam-portal/
├── app.py              # Flask routes and logic
├── config.py           # Configuration (DB, admin credentials)
├── schema.sql          # MySQL schema + sample data
├── requirements.txt    # Python packages
├── static/
│   ├── css/style.css   # All styling
│   └── js/main.js      # Modal, search, password toggle
└── templates/
    ├── base.html        # Shared layout
    ├── index.html       # Landing page
    ├── student/
    │   ├── login.html
    │   ├── dashboard.html
    │   └── allocation.html
    └── admin/
        ├── login.html
        ├── dashboard.html
        ├── students.html
        ├── exams.html
        └── allocations.html
```

---

## Database Tables

| Table      | Key Fields |
|------------|-----------|
| Student    | Roll_No (PK), Name, Password, Branch, Email, Phone, Semester |
| Exam       | Exam_ID (PK), Subject, Date, Time, Duration, Semester, Branch |
| Allocation | Alloc_ID (PK), Roll_No (FK), Exam_ID (FK), Room_No, Seat_No, Block |
