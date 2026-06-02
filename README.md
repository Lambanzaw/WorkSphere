WorkSphere: AI-Powered Human Resource and Payroll Management System
Project Description
WorkSphere is a web-based Human Resource and Payroll Management System developed to automate and simplify employee management processes within an organization. The system provides features such as attendance monitoring, payroll management, leave request handling, employee directory management, report generation, and AI-powered functionalities including voice command navigation. The project aims to reduce manual processing, improve operational efficiency, minimize errors, and enhance employee and administrator experience through a centralized digital platform.

Features
Employee Management
Attendance Monitoring
Payroll Management
Leave Request System
Voice Command Navigation
Voice Command Assistance
Attendance Report Export (CSV/PDF)
Employee Directory Export (CSV/PDF)
Payroll Summary Export (CSV/PDF)
Clock In and Clock Out
Department and Status Filtering
Role-Based Access Control
Responsive Web Design
Admin Dashboard
Authentication and Authorization

Technologies Used
Frontend
HTML
CSS
JavaScript
Bootstrap
Backend
Python
Django Framework
Database
PostgreSQL
Deployment
Railway
Version Control
GitHub
AI Integration
Claude API (Sonnet 4.5)
NLP Processing
System Requirements
Python 3.11 or higher
PostgreSQL
Git
pip
Virtual Environment
Google Chrome (Recommended)

Installation Guide
Clone the Repository
git clone https://github.com/Lambanzaw/WorkSphere

cd WorkSphere

Create Virtual Environment
python -m venv venv

Activate Virtual Environment
Windows
venv\Scripts\activate

Install Dependencies
pip install -r requirements.txt


Database Setup
Apply Migrations
python manage.py migrate

Create Superuser
python manage.py createsuperuser


Running the System
python manage.py runserver

Open your browser and visit:
http://127.0.0.1:8000/
https://worksphere-production-81a0.up.railway.app/
Default Login Credentials
Admin Account
Username:
admin

Password:
yourpassword123

Employee Account
Username:
Joshua

Password:
Joshua123!

Employee Account
Username:
John

Password:
Paul123!

Folder Structure
WORKSPHERE/
│
├── .vscode/
│
├── core/
│   │
│   ├── __pycache__/
│   ├── migrations/
│   │
│   ├── static/
│   │   ├── css/
│   │   └── images/
│   │
│   ├── templates/
│   │   └── core/
│   │       ├── _placeholder.html
│   │       ├── attendance.html
│   │       ├── base.html
│   │       ├── dashboard.html
│   │       ├── employee_add.html
│   │       ├── employee_delete.html
│   │       ├── employee_detail.html
│   │       ├── employee_edit.html
│   │       ├── employees.html
│   │       ├── login.html
│   │       └── settings.html
│   │
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── decorators.py
│   ├── forms.py
│   ├── models.py
│   ├── scheduler.py
│   ├── urls.py
│   ├── views.py
│   ├── views_attendance.py
│   ├── views_auth.py
│   ├── views_employee.py
│   ├── views_leave.py
│   ├── views_payroll.py
│   └── views_sphere.py
│
├── media/
│   ├── employee_photos/
│   └── logo.jpg
│
├── templates/
│   │
│   ├── attendance/
│   │   ├── admin_list.html
│   │   ├── clock_in.html
│   │   ├── clock_out.html
│   │   ├── my_attendance.html
│   │   ├── my_schedule.html
│   │   └── override.html
│   │
│   ├── employees/
│   │   ├── archive_confirm.html
│   │   ├── create.html
│   │   ├── detail.html
│   │   ├── edit.html
│   │   ├── list.html
│   │   ├── my_profile.html
│   │   └── unarchive_confirm.html
│   │
│   ├── leave/
│   │   ├── admin_list.html
│   │   ├── admin_review.html
│   │   ├── cancel_confirm.html
│   │   ├── create.html
│   │   └── my_leaves.html
│   │
│   ├── payroll/
│   │   ├── finalize_confirm.html
│   │   ├── generate.html
│   │   ├── list.html
│   │   ├── my_payslips.html
│   │   └── payslip.html
│   │
│   ├── reports/
│   │   └── index.html
│   │
│   ├── sphere/
│   │   ├── logs.html
│   │   └── sphere.html
│   │
│   ├── 404.html
│   ├── 500.html
│   ├── admin_dashboard.html
│   ├── base.html
│   ├── employee_dashboard.html
│   ├── forgot_password.html
│   ├── login.html
│   ├── reset_password.html
│   ├── security_questions.html
│   └── setup_security_question.html
│
├── venv/
│
├── worksphere/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── Profile/
│
├── .env
├── .env.example
├── .gitignore
├── fix_leaves.py
├── manage.py
├── README.md
├── requirements.txt
└── runtime.txt


Usage Guide
Employee Management
Add, edit, delete, and manage employee records.
Assign departments and roles.
Attendance Monitoring
Employees can clock in and clock out
Attendance logs are automatically recorded and monitored.
Payroll Management
Generate payroll summaries.
Export payroll reports in CSV and PDF formats.

Leave Request Management
Employees can submit leave requests.
Administrators can approve or reject requests.
AI Voice Command
Navigate system pages using voice commands.
Perform actions such as opening dashboards and accessing reports.
Report Generation
Export attendance reports, payroll summaries, and employee directories.
Print reports directly from the system.

AI Powered Features
Voice Command System
The system includes AI-powered voice command functionality that allows users to navigate pages and execute commands using speech recognition.

Security Features
User Authentication
Role-Based Access Control
Password Hashing
CSRF Protection
Secure Session Handling
Attendance Verification

Deployment
The system is deployed using Railway with PostgreSQL database integration. Environment variables are configured securely for production deployment.
Troubleshooting
Migration Errors
python manage.py makemigrations
python manage.py migrate

Missing Dependencies
pip install -r requirements.txt

PostgreSQL Connection Errors
Check database credentials in .env or settings.py
Ensure PostgreSQL service is running

Developers
Developed by: Cyrille Keith R. Almodovar
	Clark Justin E. Castillo
		Jan Andrei M. Patdu

License
This project is intended for educational purposes only.


