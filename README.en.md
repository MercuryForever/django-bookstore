# Bookstore Retail Management System

![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB)
![Django 6.0](https://img.shields.io/badge/Django-6.0-092E20)
![License: MIT](https://img.shields.io/badge/License-MIT-green)

[简体中文](README.md) | English

A retail and inventory management system for small and mid-sized bookstores, built around a single traceable flow: purchase receiving → stock transfers and counts → POS checkout → financial reporting, connecting products, stores, members, orders, and stock movements.

## Table of Contents

- [Overview](#overview)
- [Background & Motivation](#background--motivation)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Local Development](#local-development)
- [Deployment](#deployment)
- [Screenshots](#screenshots)
- [Demo Accounts & Roles](#demo-accounts--roles)
- [Commit Convention](#commit-convention)
- [License](#license)

## Overview

This is a monolithic Django web application built on the native MVT architecture with server-rendered templates. It runs without a separate frontend build step. The codebase is split into five business apps — `users`, `inventory`, `purchase`, `sales`, and `finance` — each owning its models, routes, templates, and access rules, with boundaries enforced through URL namespaces.

The interface uses Bootstrap 5 and Chart.js and covers the analytics dashboard, POS checkout, stock ledger, purchase orders, member profiles, and financial reports. Development uses SQLite, and two management commands bootstrap an administrator and demo data so the full workflow can be explored immediately.

## Background & Motivation

This project started from a specific goal: moving Django beyond a working example and toward a system with a complete structure and clear boundaries. Rather than building another isolated CRUD page, I wanted to work through an entire business domain — from domain modeling and access control to transactional consistency and reporting.

Bookstore retail is a good fit because its entities are easy to reason about (products, categories, warehouses, stores, suppliers, members, orders) while still carrying real complexity: stock changes need an auditable trail, transfers and purchase orders need state transitions, discounts and loyalty points need dedicated rules, and reports need cross-table aggregation over time series.

Three design decisions shaped the implementation:

1. **Server-side rendering first**: Django Templates plus Bootstrap keep the complexity in the business layer, avoiding a separate frontend stack and build pipeline for what is essentially an admin system.
2. **One app per business domain**: every app owns its models, routes, templates, and migrations; permissions are centralized at the view layer through the `role_required` decorator instead of scattered conditionals.
3. **Stock movements as the single source of truth**: receiving, sales deductions, transfers, and counts all write to `StockMovement`, so quantity changes always remain reconcilable rather than overwriting a stock field directly.

## Features

| Module | Capabilities | Notes |
| :--- | :--- | :--- |
| Authentication `users` | Sign in / out, employee CRUD, three-tier roles | `admin` / `manager` / `cashier`, enforced by `role_required` and its shortcut decorators |
| Dashboard | Business overview and trends | Today's / month-to-date revenue and order counts, 7-day sales trend, low-stock count, member total, product ranking, recent sales |
| Inventory `inventory` | Product ledger and warehouse operations | Products and categories, warehouses and stores, stock list and detail, low-stock alerts, transfer orders (create / approve / execute / cancel), stock counts (create / record / complete), stock and product lookup APIs |
| Purchase `purchase` | Suppliers and procurement flow | Supplier management, purchase orders (create / edit / submit / approve / cancel), receiving and receiving line items |
| Sales `sales` | POS and membership | Checkout cart, discount validation (including the Wednesday member discount), member checkout and loyalty points, sales records and details, Excel export, ranking and trend APIs, member registration and profile editing |
| Finance `finance` | Reporting and analysis | Daily and monthly reports, profit analysis, and Excel exports for both reports |
| Developer tooling | Data bootstrap and verification | The `create_admin` and `generate_test_data` management commands, plus data consistency check scripts in the project root |

## Technology Stack

| Category | Choice | Purpose |
| :--- | :--- | :--- |
| Language | Python ≥ 3.12 | Runtime |
| Web framework | Django ≥ 6.0 | ORM, authentication, admin, templates, migrations |
| UI | Django Templates + Bootstrap 5.3 + Bootstrap Icons 1.10 | Server-side rendering, loaded from CDN |
| Charts | Chart.js | Sales trends and ranking visualizations |
| Database | SQLite (development) / PostgreSQL, MySQL (configure for production) | Accessed through the Django ORM |
| Libraries | Faker, openpyxl | Demo data generation, Excel report export |
| Tooling | uv | Dependency declaration and virtual environments (`pyproject.toml` + `uv.lock`) |

## Project Structure

```text
django-bookstore/
├── config/                         # Project-level configuration
│   ├── settings.py                 # Settings, logging, auth redirects
│   ├── urls.py                     # Root routing and dashboard view
│   └── asgi.py / wsgi.py
├── users/                          # Employees, authentication, role permissions
│   ├── decorators.py               # role_required and shortcut decorators
│   ├── management/commands/        # create_admin
│   └── templates/users/
├── inventory/                      # Products, stock, transfers, counts
│   ├── management/commands/        # generate_test_data
│   ├── templatetags/               # Template helper tags
│   └── templates/inventory/
├── purchase/                       # Suppliers and purchase orders
│   └── templates/purchase/
├── sales/                          # POS, members, sales records
│   ├── utils.py                    # Trend and ranking aggregations
│   └── templates/sales/
├── finance/                        # Daily/monthly reports, profit analysis
│   └── templates/finance/
├── templates/                      # base.html and dashboard.html
├── static/                         # Local static assets (reserved)
├── docs/screenshots/               # UI screenshots (placeholders)
├── manage.py
├── pyproject.toml / uv.lock
├── README.md / README.en.md
└── LICENSE
```

The scripts `check_sales.py`, `check_sales_data.py`, `sync_check.py`, `create_test_data.py`, and `test_dashboard.py` in the project root are development-time data verification helpers; they do not serve runtime requests.

## Local Development

### 1. Clone the repository

```bash
git clone https://github.com/MercuryForever/django-bookstore.git
cd django-bookstore
```

### 2. Set up the environment

Python 3.12 or newer is required. Install dependencies in one of two ways:

**Using uv (recommended, versions pinned by `uv.lock`)**

```bash
uv sync
```

**Using pip**

```bash
python -m pip install "django>=6.0" "faker>=40.1.0" "openpyxl>=3.1.5"
```

> In a uv environment, prefix each command with `uv run`, for example `uv run python manage.py migrate`.

### 3. Initialize the database

```bash
python manage.py migrate
```

### 4. Create an administrator

```bash
python manage.py create_admin
```

Default credentials are `admin` / `admin123` — **for local development only**.

### 5. Generate demo data (optional)

```bash
python manage.py generate_test_data
```

This creates warehouses, stores, categories, products, members, employees, simulated sales records, and the manager/cashier demo accounts listed below.

### 6. Start the server

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000` in a browser.

## Deployment

The committed `config/settings.py` uses development defaults: `DEBUG = True`, `ALLOWED_HOSTS = ['*']`, a hard-coded `SECRET_KEY`, and SQLite. **These settings must not be used in production.** Complete the following adjustments before deploying.

### 1. Inject production configuration

Read sensitive values from environment variables, for example:

```python
import os

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
DEBUG = os.environ.get('DJANGO_DEBUG', '0') == '1'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
```

Then set `DJANGO_SECRET_KEY` (a long random string), `DJANGO_ALLOWED_HOSTS` (the real domain), plus `CSRF_TRUSTED_ORIGINS` and the relevant `SECURE_*` settings, and enable HTTPS.

### 2. Switch the database

SQLite is intended for local and single-machine demos. For production, point `DATABASES` at PostgreSQL or MySQL, install the corresponding driver, and run migrations against the new database.

### 3. Configure static files

Set `STATIC_ROOT` in settings, then run:

```bash
python manage.py collectstatic --noinput
```

Bootstrap and Chart.js are served from a CDN. If the deployment environment has no outbound access, host them locally instead. The `static/` directory is reserved for project-owned assets.

### 4. Install dependencies and initialize

```bash
uv sync --frozen                 # or install from pyproject.toml with pip
python manage.py migrate
python manage.py create_admin    # or createsuperuser
python manage.py collectstatic --noinput
```

Change the default password immediately after creating the administrator. **Do not run `generate_test_data` in production**, and do not keep any demo accounts.

### 5. Application server and reverse proxy

Serve the WSGI app with Gunicorn and let Nginx terminate HTTPS, proxy requests, and serve static files:

```bash
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

Point Nginx `proxy_pass` at the application exposed by `config/wsgi.py`, and map `/static/` to `STATIC_ROOT`. Logs are written to `bookstore.log` in the project root; make sure the runtime user can write to that path.

### 6. Pre-launch checks

```bash
python manage.py check --deploy
```

Address every item reported, then verify that no secrets are committed, `DEBUG` is off, database and log permissions are correct, and demo data has been removed.

## Screenshots

Screenshots live in `docs/screenshots/`. The directory exists and the images are **placeholders to be added**.

| Screen | File | What it shows |
| :--- | :--- | :--- |
| Dashboard | `docs/screenshots/dashboard.png` | Today's / month-to-date sales, 7-day trend, low-stock alerts, product ranking |
| POS checkout | `docs/screenshots/pos.png` | Product search, cart, discounts, member checkout |
| Inventory list | `docs/screenshots/inventory.png` | Multi-store stock lookup and low-stock markers |
| Stock transfer | `docs/screenshots/stock-transfer.png` | Transfer order creation and state transitions |
| Purchase order | `docs/screenshots/purchase-order.png` | Order line items, approval, receiving |
| Membership | `docs/screenshots/members.png` | Member profiles and points history |
| Financial reports | `docs/screenshots/finance-report.png` | Daily / monthly reports and profit analysis |

<!-- Enable once the screenshots are added:
![Dashboard](docs/screenshots/dashboard.png)
-->

## Demo Accounts & Roles

These accounts are created by `generate_test_data` and are intended for local exploration only.

| Role | Username | Password |
| :--- | :--- | :--- |
| Admin | `admin` (created by `create_admin`) | `admin123` |
| Manager | `manager_S0001` – `manager_S0050` | `password123` |
| Cashier | `cashier_S0001_1` | `password123` |

| Role | Access |
| :--- | :--- |
| Admin | All features, including employee management and system configuration |
| Manager | Stock lookup / transfers / counts, purchase approval, financial reports, sales ranking, membership management |
| Cashier | POS checkout and payment |

## Commit Convention

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) using `<type>(<scope>): <subject>`:

- **type**: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `chore`
- **scope**: an app name (`users`, `inventory`, `purchase`, `sales`, `finance`, `config`) or a domain term (`dashboard`, `scripts`, `deps`)

Examples:

```text
feat(sales): add membership points redemption at checkout
fix(inventory): prevent negative stock on transfer execution
docs: clarify production deployment checklist
```

## License

Released under the [MIT License](LICENSE), Copyright (c) 2026 MercuryForever.
