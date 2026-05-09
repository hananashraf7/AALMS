"""
database/db_manager.py
SQLite database manager for Smart Attendance System
"""

import sqlite3
import os
from datetime import datetime, date
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'attendance_data', 'attendance.db')


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize all database tables."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    c = conn.cursor()

    # Students / People table
    c.execute('''
        CREATE TABLE IF NOT EXISTS persons (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id   TEXT UNIQUE NOT NULL,
            name        TEXT NOT NULL,
            email       TEXT,
            department  TEXT,
            role        TEXT DEFAULT 'student',
            face_encoding BLOB,
            registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active   INTEGER DEFAULT 1
        )
    ''')

    # Attendance records
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id   TEXT NOT NULL,
            date        DATE NOT NULL,
            check_in    DATETIME,
            check_out   DATETIME,
            status      TEXT DEFAULT 'present',
            confidence  REAL,
            method      TEXT DEFAULT 'face',
            notes       TEXT,
            FOREIGN KEY(person_id) REFERENCES persons(person_id),
            UNIQUE(person_id, date)
        )
    ''')

    # Security events
    c.execute('''
        CREATE TABLE IF NOT EXISTS security_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT NOT NULL,
            person_id   TEXT,
            description TEXT,
            snapshot_path TEXT,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Sessions
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT NOT NULL,
            subject     TEXT,
            instructor  TEXT,
            start_time  DATETIME,
            end_time    DATETIME,
            is_active   INTEGER DEFAULT 0
        )
    ''')

    # ✅ FIXED: properly indented
    c.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id      TEXT UNIQUE NOT NULL,
            class_name    TEXT NOT NULL,
            department    TEXT NOT NULL,
            semester      INTEGER NOT NULL,
            subject       TEXT,
            instructor    TEXT,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ✅ FIXED: properly indented
    c.execute('''
        CREATE TABLE IF NOT EXISTS class_attendance (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id   TEXT NOT NULL,
            person_id  TEXT NOT NULL,
            date       DATE NOT NULL,
            check_in   DATETIME,
            status     TEXT DEFAULT 'present',
            confidence REAL,
            FOREIGN KEY(class_id)  REFERENCES classes(class_id),
            FOREIGN KEY(person_id) REFERENCES persons(person_id),
            UNIQUE(class_id, person_id, date)
        )
    ''')

    conn.commit()
    conn.close()
    print("[DB] Database initialized.")


# ─── Person CRUD ──────────────────────────────────────────────────────────────

def add_person(person_id: str, name: str, email: str = '',
               department: str = '', role: str = 'student',
               face_encoding=None) -> bool:
    try:
        conn = get_connection()
        conn.execute(
            '''INSERT INTO persons (person_id, name, email, department, role, face_encoding)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (person_id, name, email, department, role, face_encoding)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def update_face_encoding(person_id: str, encoding_blob: bytes) -> bool:
    conn = get_connection()
    conn.execute('UPDATE persons SET face_encoding=? WHERE person_id=?',
                 (encoding_blob, person_id))
    conn.commit()
    conn.close()
    return True


def get_all_persons(active_only=True) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute(
        'SELECT * FROM persons WHERE is_active=? OR ?=0',
        (1 if active_only else 0, 1 if active_only else 1)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_person(person_id: str) -> Optional[Dict]:
    conn = get_connection()
    row = conn.execute('SELECT * FROM persons WHERE person_id=?', (person_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ─── Attendance CRUD ──────────────────────────────────────────────────────────

def mark_check_in(person_id: str, confidence: float = 1.0, method: str = 'face') -> Dict:
    today = date.today().isoformat()
    now   = datetime.now().isoformat(timespec='seconds')
    conn  = get_connection()

    existing = conn.execute(
        'SELECT * FROM attendance WHERE person_id=? AND date=?',
        (person_id, today)
    ).fetchone()

    if existing:
        conn.close()
        return {'status': 'already_marked', 'record': dict(existing)}

    conn.execute(
        '''INSERT INTO attendance (person_id, date, check_in, status, confidence, method)
           VALUES (?, ?, ?, 'present', ?, ?)''',
        (person_id, today, now, confidence, method)
    )
    conn.commit()

    record = conn.execute(
        'SELECT * FROM attendance WHERE person_id=? AND date=?',
        (person_id, today)
    ).fetchone()
    conn.close()
    return {'status': 'marked', 'record': dict(record)}


def mark_check_out(person_id: str) -> Dict:
    today = date.today().isoformat()
    now   = datetime.now().isoformat(timespec='seconds')
    conn  = get_connection()
    conn.execute(
        'UPDATE attendance SET check_out=? WHERE person_id=? AND date=?',
        (now, person_id, today)
    )
    conn.commit()
    conn.close()
    return {'status': 'checked_out', 'time': now}


def get_today_attendance() -> List[Dict]:
    today = date.today().isoformat()
    conn  = get_connection()
    rows  = conn.execute(
        '''SELECT a.*, p.name, p.department
           FROM attendance a
           JOIN persons p ON a.person_id = p.person_id
           WHERE a.date=? ORDER BY a.check_in DESC''',
        (today,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_attendance_range(start: str, end: str, person_id: str = None) -> List[Dict]:
    conn  = get_connection()
    query = '''SELECT a.*, p.name, p.department
               FROM attendance a
               JOIN persons p ON a.person_id = p.person_id
               WHERE a.date BETWEEN ? AND ?'''
    params = [start, end]
    if person_id:
        query += ' AND a.person_id=?'
        params.append(person_id)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_attendance_summary(start: str, end: str) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute(
        '''SELECT p.person_id, p.name, p.department,
                  COUNT(a.id) as days_present,
                  MIN(a.date) as first_seen,
                  MAX(a.date) as last_seen
           FROM persons p
           LEFT JOIN attendance a
             ON p.person_id=a.person_id AND a.date BETWEEN ? AND ?
           WHERE p.is_active=1
           GROUP BY p.person_id''',
        (start, end)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Security Events ──────────────────────────────────────────────────────────

def log_security_event(event_type: str, person_id: str = None,
                       description: str = '', snapshot_path: str = '') -> int:
    conn = get_connection()
    cur  = conn.execute(
        '''INSERT INTO security_events (event_type, person_id, description, snapshot_path)
           VALUES (?, ?, ?, ?)''',
        (event_type, person_id, description, snapshot_path)
    )
    event_id = cur.lastrowid
    conn.commit()
    conn.close()
    return event_id


def get_security_events(limit=100) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute(
        'SELECT * FROM security_events ORDER BY timestamp DESC LIMIT ?', (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
# ─── Classes ──────────────────────────────────────────────────────────────────

def create_class(class_id: str, class_name: str, department: str,
                 semester: int, subject: str = '', instructor: str = '') -> bool:
    try:
        conn = get_connection()
        conn.execute(
            '''INSERT INTO classes (class_id, class_name, department, semester, subject, instructor)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (class_id, class_name, department, semester, subject, instructor)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def get_all_classes(department: str = None) -> List[Dict]:
    conn = get_connection()
    if department:
        rows = conn.execute(
            'SELECT * FROM classes WHERE department=? ORDER BY semester, class_name',
            (department,)
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT * FROM classes ORDER BY department, semester, class_name'
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_class(class_id: str) -> Optional[Dict]:
    conn = get_connection()
    row = conn.execute('SELECT * FROM classes WHERE class_id=?', (class_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_class(class_id: str) -> bool:
    conn = get_connection()
    conn.execute('DELETE FROM class_attendance WHERE class_id=?', (class_id,))
    conn.execute('DELETE FROM classes WHERE class_id=?', (class_id,))
    conn.commit()
    conn.close()
    return True


def mark_class_attendance(class_id: str, person_id: str,
                          confidence: float = 1.0) -> Dict:
    today = date.today().isoformat()
    now   = datetime.now().isoformat(timespec='seconds')
    conn  = get_connection()

    existing = conn.execute(
        'SELECT * FROM class_attendance WHERE class_id=? AND person_id=? AND date=?',
        (class_id, person_id, today)
    ).fetchone()

    if existing:
        conn.close()
        return {'status': 'already_marked', 'record': dict(existing)}

    conn.execute(
        '''INSERT INTO class_attendance (class_id, person_id, date, check_in, confidence)
           VALUES (?, ?, ?, ?, ?)''',
        (class_id, person_id, today, now, confidence)
    )
    conn.commit()
    record = conn.execute(
        'SELECT * FROM class_attendance WHERE class_id=? AND person_id=? AND date=?',
        (class_id, person_id, today)
    ).fetchone()
    conn.close()
    return {'status': 'marked', 'record': dict(record)}


def get_class_attendance(class_id: str, start: str = None, end: str = None) -> List[Dict]:
    conn  = get_connection()
    today = date.today().isoformat()
    start = start or today
    end   = end   or today
    rows  = conn.execute(
        '''SELECT ca.*, p.name, p.department
           FROM class_attendance ca
           JOIN persons p ON ca.person_id = p.person_id
           WHERE ca.class_id=? AND ca.date BETWEEN ? AND ?
           ORDER BY ca.date DESC, ca.check_in DESC''',
        (class_id, start, end)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
