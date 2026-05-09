# AALMS — AI-Powered Attendance & Leave Management System

A modern, full-stack attendance management system using **real-time facial recognition** for automated check-ins, with a complete **leave management workflow** and **admin dashboard**.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal?logo=fastapi)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

### 🎯 Core
- **Real-time Face Detection & Recognition** — HOG-based face detection with 128-dimensional encoding matching
- **Automated Attendance Logging** — Recognized students are marked present instantly
- **One-time Registration** — Register a student's face once via webcam; the system remembers them permanently

### 📊 Admin Dashboard
- **Attendance Calendar** — View attendance grouped by date with expandable day-wise details
- **Shortage Overview** — Automatically flags students with < 75% attendance
- **Attendance Database** — Raw logs with date, day, check-in time, and recognition confidence
- **Leave Request Processing** — Approve/reject pending leave applications (max 15 per semester)
- **Daily Reset** — Clear today's attendance data for re-scanning
- **Admin Settings** — Change admin username, password, and display name

### 🎨 UI/UX
- Clean, light-mode minimalist design
- Responsive layout built with Next.js + Tailwind CSS
- Start/Stop detection control on the kiosk page
- Real-time check-in feed with live status indicators

---

## 🏗 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 15, React 19, TypeScript | Dashboard & Kiosk UI |
| **Styling** | Tailwind CSS v4, Custom CSS | Minimalist light-mode design |
| **Backend API** | FastAPI, Uvicorn | REST API with auto-generated docs |
| **Database** | SQLite + SQLAlchemy ORM | Student, Attendance, Leave, Admin models |
| **Face Recognition** | face_recognition (dlib), OpenCV | Detection, encoding, and matching |
| **Webcam** | react-webcam | Browser-based camera capture |

---

## 📂 Project Structure

```
AALMS/
├── api/
│   ├── main.py              # FastAPI application & all endpoints
│   └── schemas.py           # Pydantic request/response schemas
├── core/
│   ├── face_engine.py       # Face detection, encoding & recognition logic
│   └── camera_attendance.py # Standalone camera attendance (CLI mode)
├── database/
│   ├── database.py          # SQLAlchemy engine & session config
│   ├── models.py            # ORM models (Student, Attendance, Leave, Admin, FaceEmbedding)
│   └── db_manager.py        # Database utility functions
├── frontend/
│   ├── src/app/
│   │   ├── page.tsx          # Kiosk page (webcam + live check-ins)
│   │   ├── layout.tsx        # Root layout with navigation
│   │   ├── globals.css       # Design system (light-mode minimal)
│   │   └── admin/
│   │       ├── page.tsx      # Admin login page
│   │       └── dashboard/
│   │           └── page.tsx  # Admin dashboard (all tabs)
│   ├── package.json
│   └── next.config.ts
├── requirements.txt          # Python dependencies
├── manage.py                 # CLI management commands
└── README.md                 # This file
```

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** and **npm**
- **CMake** and a **C++ compiler** (required by dlib)
  - macOS: `brew install cmake`
  - Ubuntu: `sudo apt install cmake build-essential`
  - Windows: Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/AALMS.git
cd AALMS
```

### 2. Setup Python Backend
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Setup Next.js Frontend
```bash
cd frontend
npm install
cd ..
```

### 4. Start the Backend Server
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```
> API docs available at: http://localhost:8000/docs

### 5. Start the Frontend
```bash
cd frontend
npm run dev
```
> Frontend available at: http://localhost:3000

---

## 🔐 Default Admin Credentials

| Field | Value |
|-------|-------|
| Username | `hananashraf` |
| Password | `coldspot` |

> ⚠️ Change these immediately after first login via **Settings** tab.

---

## 📡 API Endpoints

### Students
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/students/` | Create a student |
| GET | `/students/` | List all students |
| POST | `/students/register_with_face` | Register student + capture face encoding |

### Attendance
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/attendance/process_frame` | Process a webcam frame for face recognition |
| GET | `/attendance/today` | Get today's check-ins |
| GET | `/attendance/all` | Get all attendance records |
| GET | `/attendance/overview` | Get shortage overview (< 75% flagged) |
| GET | `/attendance/calendar` | Get attendance grouped by date |
| DELETE | `/attendance/reset-today` | Delete today's attendance records |
| GET | `/attendance/debug` | Debug: check face embeddings in DB |

### Leaves
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/leaves/apply/` | Submit a leave application (status: pending) |
| GET | `/leaves/all` | Get all leave records |
| POST | `/leaves/{id}/approve` | Approve a pending leave |
| POST | `/leaves/{id}/reject` | Reject a pending leave |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/admin/login` | Authenticate admin |
| POST | `/admin/settings` | Update admin credentials |

### Cache
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/cache/reload` | Force reload face encoding cache |

---

## 🧠 How Face Recognition Works

```
Registration:
  Webcam Frame → OpenCV decode → face_recognition.face_locations (HOG)
  → face_recognition.face_encodings (128-d vector, 2 jitters)
  → pickle.dumps → Store in SQLite (FaceEmbedding table)

Recognition:
  Live Frame → Detect faces → Encode each face
  → Compare against all stored encodings (tolerance: 0.55)
  → If match found → Log attendance for today
  → Draw bounding box with student ID + confidence %
```

---

## ⚙️ Configuration

| Setting | Value | Location |
|---------|-------|----------|
| Face match tolerance | `0.55` | `core/face_engine.py` |
| Cache refresh interval | `30 seconds` | `api/main.py` |
| Max leaves per semester | `15` | `api/main.py` |
| Shortage threshold | `75%` | `api/main.py` |
| Database | `attendance.db` (SQLite) | `database/database.py` |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Hanan Ashraf** — [GitHub](https://github.com/YOUR_USERNAME)

Built as part of an AI-powered smart campus initiative.
