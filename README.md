# 🌱 GreenPath - Smart Village Waste Governance System

**Academic Course:** INT253 — Web Development in Python Using Django  
**Academic Session:** 2026–27  
**Architecture:** Monolithic Django Web Application (Server-rendered HTML + REST-style JSON APIs)  
**Database:** Cloud PostgreSQL (Neon) or Local SQLite fallback  

---

## 📌 Executive Summary

**GreenPath** is a modern, accountable solid waste governance platform designed for Gram Panchayats and rural/semi-urban civic administrations. It replaces archaic paper visit registers with:
- **Household Doorstep QR Identifiers** without exposing resident PII.
- **Mobile Web Camera Scanner** with instantaneous village-boundary verification.
- **Audit-Grade Segregation Capture** (Wet, Dry, Sanitary + 1-to-5 Star Rating scale).
- **Executive Analytics Reports** calculating real-time ward coverage, deduplicated daily visits, and average segregation indices.
- **Citizen Household Portal** providing families with visit audit transparency, history logs, and personal printable QR identification cards.

---

## 🏛️ System Architecture & Four Governance Roles

The system strictly enforces role-based access control and multi-tenant Gram Panchayat isolation:

| Role | Provisioning | Scope | Key Capabilities |
| :--- | :--- | :--- | :--- |
| **1. Super Admin** | CLI / Initial Seed | System-Wide | Creates Gram Panchayats (`Village`), sets up `Ward` subdivisions, appoints and assigns `Village Manager` accounts. |
| **2. Village Manager** | Appointed by Super Admin | Assigned Village | Maintains Household register with auto-generated UIDs, provisions `Waste Collector` accounts, prints QR cards, reviews daily ward analytics. |
| **3. Waste Collector** | Appointed by Village Manager | Assigned Village | Mobile doorstep camera QR scanner (`html5-qrcode`), village boundary validation, records visit outcome (`Collected` vs `Missed`), 1-5 star ratings, and daily counter widget. |
| **4. Household User** | Provisioned by Village Manager | Linked Household | Resident self-service portal, views today's visit status (time, rating, collector), downloads/prints personal QR card, and browses audit history. |

> [!NOTE]
> **No Public Self-Registration:** Public visitors can explore an attractive landing page and educational waste segregation guidelines. Account creation is strictly administrative to guarantee governance integrity.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.11+
- Virtual Environment (`venv`)

### 2. Setup Virtual Environment & Install Dependencies
```bash
# Clone or navigate to the project directory
cd GreenPath

# Create virtual environment (if not already created)
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install -r requirements.txt # Or: pip install django pillow qrcode dj-database-url psycopg2-binary python-dotenv
```

### 3. Database Setup & Migrations
```bash
# Apply Django migrations
python manage.py migrate
```

### 4. Seed Academic Demo Data
GreenPath includes an automated seeding command to provision realistic Gram Panchayats, wards, collectors, households, and audit records:
```bash
python manage.py seed_data
```

### 5. Launch Development Server
```bash
python manage.py runserver
```
Visit **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser.

---

## 🔑 Demo Evaluation Credentials

After running `python manage.py seed_data`, you can sign in using any of the four operational roles:

| Role | Username | Password | Purpose & Starting Portal |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `superadmin` | `admin123` | System HQ: `/governance/admin-dashboard/` |
| **Village Manager** | `mgr_shivaji` | `manager123` | Shivaji GP Manager: `/manager/dashboard/` |
| **Waste Collector** | `collector_shivaji1` | `collector123` | Doorstep Mobile Scanner: `/collector/doorstep/` |
| **Household Resident** | `resident_shivaji1` | `resident123` | Resident Portal (#12-A): `/analytics/household-dashboard/` |

---

## 📡 REST-Style JSON API Contract

All endpoints share the same host, port, database, and session authentication with the web UI (SRS Section 3.2.9):

| Method | Endpoint | Clearance | Description |
| :---: | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login/` | Public | Authenticates credentials and returns session cookie with user & village metadata |
| `POST` | `/api/v1/auth/logout/` | Authenticated | Terminates active session |
| `GET` | `/api/v1/auth/me/` | Authenticated | Returns current authenticated user profile, role, and village |
| `GET` | `/api/v1/villages/` | Super Admin | Lists all villages, wards, and manager appointments |
| `POST` | `/api/v1/villages/` | Super Admin | Creates new village with optional initial wards |
| `GET` | `/api/v1/managers/` | Super Admin | Lists all village managers and assigned jurisdictions |
| `POST` | `/api/v1/managers/` | Super Admin | Creates manager account and assigns to a village |
| `GET` | `/api/v1/households/` | Village Manager | Lists village households (optional `?ward=` filter) |
| `POST` | `/api/v1/households/` | Village Manager | Registers household via JSON body, generates UID & QR |
| `GET` | `/api/v1/households/<uid>/qr/` | Manager / Household | Returns QR code image URL and printable card payload |
| `GET` | `/api/v1/collectors/` | Village Manager | Lists waste collectors for the village |
| `POST` | `/api/v1/collectors/` | Village Manager | Provisions new collector account in manager's village |
| `POST` | `/api/v1/collector/validate-qr/` | Waste Collector | Validates scanned QR string against village boundary |
| `POST` | `/api/v1/collector/submit/` | Waste Collector | Submits doorstep visit outcome (`COLLECTED` or `MISSED`) |
| `GET` | `/api/v1/reports/summary/` | Village Manager | Date-filtered totals and ward-wise metrics (`?date=YYYY-MM-DD`) |
| `GET` | `/api/v1/household/my-status/` | Household | Current-day collection status and chronological visit history |

---

## 🧪 Automated Testing & Verification

GreenPath features comprehensive automated unit and integration tests covering models, forms, decorators, multi-tenant scoping, QR generation, aggregation math, error handling, and JSON endpoints:

```bash
# Run all tests across the entire project
python manage.py test

# Run tests by app module
python manage.py test core
python manage.py test accounts
python manage.py test governance
python manage.py test households
python manage.py test waste_collections
python manage.py test analytics
```
**Verification Result:** 40 / 40 Tests Passing (100% Pass Rate).

---

## 🛡️ Cloud Database Configuration (Neon PostgreSQL)

To switch from local SQLite to Neon-hosted Cloud PostgreSQL, set `DATABASE_URL` in your `.env` file:
```env
DATABASE_URL=postgresql://username:password@ep-greenpath.neon.tech/neondb?sslmode=require
```
Django will automatically configure `dj-database-url` with connection pooling and health checks.

---

*Academic Session 2026-27 &bull; INT253 Web Development in Python using Django &bull; Continuous Assessment 3*

