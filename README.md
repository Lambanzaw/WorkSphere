# WorkSphere: A Web-Based Human Resource Management System
## Smart Workforce Management Made Simple

---

## 📋 PREREQUISITES

Before starting, make sure you have these installed:

| Tool | Version | Check Command |
|------|---------|--------------|
| Python | 3.10+ | `python --version` |
| PostgreSQL | 14+ | `psql --version` |
| pip | latest | `pip --version` |
| Git | any | `git --version` |

---

## 🗂️ PROJECT STRUCTURE

```
worksphere/                      ← Root project folder
├── manage.py
├── requirements.txt
├── .env                         ← You create this (copy from .env.example)
├── worksphere/                  ← Django project config
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                        ← Main HR app
│   ├── migrations/
│   ├── __init__.py
│   ├── models.py
│   ├── admin.py
│   ├── forms.py
│   ├── decorators.py
│   ├── views_auth.py
│   ├── views_employee.py
│   ├── views_attendance.py
│   ├── views_leave.py
│   ├── views_payroll.py
│   ├── views_reports.py
│   └── urls.py
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── admin_dashboard.html
│   ├── employee_dashboard.html
│   ├── employees/
│   │   ├── list.html
│   │   ├── create.html
│   │   ├── detail.html
│   │   └── edit.html
│   ├── attendance/
│   │   ├── list.html
│   │   └── admin_list.html
│   ├── leave/
│   │   ├── list.html
│   │   ├── create.html
│   │   └── admin_list.html
│   ├── payroll/
│   │   ├── list.html
│   │   ├── generate.html
│   │   └── payslip.html
│   └── reports/
│       └── index.html
└── static/
    └── css/
        └── worksphere.css
```

---

## 🚀 STEP-BY-STEP SETUP

### STEP 1 — Clone / Create the Project Folder

```bash
mkdir worksphere
cd worksphere
```

### STEP 2 — Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### STEP 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

### STEP 4 — Set Up PostgreSQL Database

Open your PostgreSQL shell (`psql`) and run:

```sql
-- Create the database
CREATE DATABASE worksphere_db;

-- Create a dedicated user
CREATE USER worksphere_user WITH PASSWORD 'yourpassword123';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE worksphere_db TO worksphere_user;

-- Exit
\q
```

### STEP 5 — Create Your .env File

Copy `.env.example` to `.env`:

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Then edit `.env` with your actual credentials:

```
DB_NAME=worksphere_db
DB_USER=worksphere_user
DB_PASSWORD=yourpassword123
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your-very-secret-key-change-this
DEBUG=True
```

**To generate a secure SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### STEP 6 — Create Django Project Structure

If starting fresh (all files provided), just run:

```bash
django-admin startproject worksphere .
python manage.py startapp core
```

Then **replace** the generated files with the ones provided in this package.

### STEP 7 — Run Database Migrations

```bash
python manage.py makemigrations core
python manage.py migrate
```

### STEP 8 — Create the Superuser (Admin)

```bash
python manage.py createsuperuser
```

Enter:
- Username: `admin`
- Email: `admin@worksphere.com`
- Password: (choose a strong password)

### STEP 9 — Load Initial Data (Optional)

```bash
python manage.py shell
```

Then in the shell:
```python
from core.models import LeaveType
LeaveType.objects.create(name="Vacation Leave", max_days=15)
LeaveType.objects.create(name="Sick Leave", max_days=10)
LeaveType.objects.create(name="Emergency Leave", max_days=3)
exit()
```

### STEP 10 — Collect Static Files

```bash
python manage.py collectstatic
```

### STEP 11 — Run the Development Server

```bash
python manage.py runserver
```

Open your browser: **http://127.0.0.1:8000/**

---

## 👤 DEFAULT LOGIN

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | (what you set in Step 8) |
| Employee | (create via admin panel) | (set when creating) |

---

## 🔐 CREATING EMPLOYEE ACCOUNTS

1. Log in as Admin
2. Go to **Employee Management → Add Employee**
3. Fill in all required fields
4. The system auto-creates a User account linked to the employee

---

## 🧪 TESTING HR BUSINESS RULES

### Attendance Rules to Test:
- Try clocking in twice on the same day → should be blocked
- Try clocking out before clock-in time → should be blocked
- Try clocking in on Saturday/Sunday → should be blocked

### Leave Rules to Test:
- Try filing leave for yesterday → should be blocked
- Try filing leave without 2 days advance notice → should be blocked
- Try filing overlapping leave dates → should be blocked

### Payroll Rules to Test:
- Unapproved absences = no salary
- Late deductions calculated automatically
- Net salary cannot be negative

---

## 📁 FILE PLACEMENT GUIDE

After downloading all files, place them exactly as shown:

```
All files go inside the root worksphere/ folder
├── requirements.txt          → root
├── .env.example              → root
├── worksphere/settings.py    → worksphere/ subfolder
├── worksphere/urls.py        → worksphere/ subfolder
├── core/models.py            → core/ subfolder
├── core/*.py                 → core/ subfolder
├── templates/**/*.html       → templates/ folder (maintain subfolders)
└── static/css/worksphere.css → static/css/ folder
```

---

## ⚠️ TROUBLESHOOTING

**"No module named psycopg2"**
```bash
pip install psycopg2-binary
```

**"FATAL: password authentication failed"**
- Double-check your .env DB_PASSWORD matches what you set in PostgreSQL

**"django.db.utils.OperationalError: could not connect to server"**
- Make sure PostgreSQL is running:
  - Windows: Check Services → PostgreSQL
  - Linux: `sudo systemctl start postgresql`
  - macOS: `brew services start postgresql`

**"TemplateDoesNotExist"**
- Make sure `DIRS` in `settings.py` points to your templates folder
- Check `TEMPLATES` setting includes `'DIRS': [BASE_DIR / 'templates']`

**Migrations errors**
```bash
python manage.py migrate --run-syncdb
```

---

## 🔒 PRODUCTION DEPLOYMENT NOTES

Before going live:
1. Set `DEBUG=False` in .env
2. Set `ALLOWED_HOSTS` to your domain
3. Use `gunicorn` + `nginx`
4. Enable HTTPS (SSL certificate)
5. Set up proper database backups
6. Rotate SECRET_KEY

---

## 📞 SYSTEM MODULES OVERVIEW

| Module | Admin Access | Employee Access |
|--------|-------------|----------------|
| Dashboard | Full stats | Personal stats |
| Employees | Full CRUD | View own profile |
| Attendance | View all, override | Clock in/out, view own |
| Leave | Approve/reject all | File, view own |
| Payroll | Generate, view all | View own payslips |
| Reports | All reports | — |

---

*WorkSphere v1.0 — Smart Workforce Management Made Simple*
