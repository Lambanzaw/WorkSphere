# WorkSphere: A Web-Based Human Resource Management System
## Smart Workforce Management Made Simple

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

mkdir worksphere
cd worksphere

python -m venv venv
venv\Scripts\activate


python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

CREATE DATABASE worksphere_db;


CREATE USER worksphere_user WITH PASSWORD 'yourpassword123';


GRANT ALL PRIVILEGES ON DATABASE worksphere_db TO worksphere_user;


# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env


DB_NAME=worksphere_db
DB_USER=worksphere_user
DB_PASSWORD=yourpassword123
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your-very-secret-key-change-this
DEBUG=True


python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"


django-admin startproject worksphere .
python manage.py startapp core


python manage.py makemigrations core
python manage.py migrate

python manage.py createsuperuser


python manage.py shell


python manage.py collectstatic


python manage.py runserver


Open your browser: **http://127.0.0.1:8000/**


All files go inside the root worksphere/ folder
├── requirements.txt          → root
├── .env.example              → root
├── worksphere/settings.py    → worksphere/ subfolder
├── worksphere/urls.py        → worksphere/ subfolder
├── core/models.py            → core/ subfolder
├── core/*.py                 → core/ subfolder
├── templates/**/*.html       → templates/ folder (maintain subfolders)
└── static/css/worksphere.css → static/css/ folder


pip install psycopg2-binary


python manage.py migrate --run-syncdb




