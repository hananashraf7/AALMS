"""
manage.py
Command-line management tool for Advanced Face Recognition Attendance System.

Usage:
  python manage.py init-db
  python manage.py add-person --id STU001 --name "Arjun Singh" --dept "CS"
  python manage.py register-face --id STU001 --images face1.jpg face2.jpg
  python manage.py start-camera
  python manage.py list-persons
  python manage.py today
"""

import argparse
import sys
import os
import logging
from datetime import date

# ── Resolve all paths relative to this script file, not the CWD ──────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# ── Also make sure other auto-created dirs exist ──────────────────────────────
for _d in ('known_faces', 'attendance_data'):
    os.makedirs(os.path.join(BASE_DIR, _d), exist_ok=True)

# ── Change CWD to the project root so relative imports work ──────────────────
os.chdir(BASE_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOGS_DIR, 'app.log'), mode='a'),
    ]
)
logger = logging.getLogger(__name__)


def cmd_init_db(args):
    from database.db_manager import init_db
    init_db()
    print("✅ Database initialized.")


def cmd_add_person(args):
    from database.db_manager import init_db, add_person
    init_db()
    ok = add_person(
        person_id  = args.id,
        name       = args.name,
        email      = getattr(args, 'email', ''),
        department = getattr(args, 'dept', ''),
        role       = getattr(args, 'role', 'student'),
    )
    if ok:
        print(f"✅ Registered: {args.name} ({args.id})")
    else:
        print(f"❌ Person {args.id} already exists.")


def cmd_register_face(args):
    from database.db_manager import init_db, update_face_encoding
    from core.face_engine import register_person_faces
    init_db()
    
    ok, msg, encoding = register_person_faces(args.id, args.images)
    if ok and encoding is not None:
        import pickle
        encoding_blob = pickle.dumps(encoding)
        update_face_encoding(args.id, encoding_blob)
    print(('✅ ' if ok else '❌ ') + msg)


def cmd_start_camera(args):
    from database.db_manager import init_db
    from core.camera_attendance import run_camera
    init_db()
    print("📷 Starting camera. Press 'q' to quit.")
    run_camera(camera_index=getattr(args, 'camera', 0))


def cmd_list_persons(args):
    from database.db_manager import init_db, get_all_persons
    init_db()
    persons = get_all_persons()
    if not persons:
        print("No persons registered yet.")
        return
    print(f"\n{'ID':<12} {'Name':<25} {'Department':<20} {'Role'}")
    print('-' * 70)
    for p in persons:
        print(f"{p['person_id']:<12} {p['name']:<25} {p.get('department',''):<20} {p.get('role','')}")
    print(f"\nTotal: {len(persons)}")


def cmd_today(args):
    from database.db_manager import init_db, get_today_attendance
    init_db()
    records = get_today_attendance()
    if not records:
        print("No attendance recorded today.")
        return
    print(f"\nAttendance for today ({date.today()}):")
    print(f"{'Time':<25} {'ID':<15} {'Name':<25} {'Status'}")
    print('-' * 75)
    for r in records:
        print(f"{r['check_in']:<25} {r['person_id']:<15} {r['name']:<25} {r['status']}")
    print(f"\nTotal present: {len(records)}")


# ─── Argument parser ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Smart Attendance System CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('init-db', help='Initialize the database')

    p = sub.add_parser('add-person', help='Register a new person')
    p.add_argument('--id',    required=True)
    p.add_argument('--name',  required=True)
    p.add_argument('--dept',  default='')
    p.add_argument('--email', default='')
    p.add_argument('--role',  default='student', choices=['student','faculty','staff'])

    p = sub.add_parser('register-face', help='Register face images for a person')
    p.add_argument('--id',     required=True)
    p.add_argument('--images', nargs='+', required=True)

    p = sub.add_parser('start-camera', help='Start real-time camera attendance')
    p.add_argument('--camera', type=int, default=0)

    sub.add_parser('list-persons')
    sub.add_parser('today')

    args = parser.parse_args()

    dispatch = {
        'init-db':        cmd_init_db,
        'add-person':     cmd_add_person,
        'register-face':  cmd_register_face,
        'start-camera':   cmd_start_camera,
        'list-persons':   cmd_list_persons,
        'today':          cmd_today,
    }

    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
