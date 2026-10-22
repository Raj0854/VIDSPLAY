# VIDSPLAY — Full-Stack Video Streaming & CMS Platform

**VIDSPLAY** is a modern, production-grade video platform featuring dynamic navigation management, a visual page & layout builder, dual video addition options (local drag-and-drop file upload with range streaming & verified YouTube/embed URLs), responsive playback, and a full-featured admin control center.

---

## 🌟 Key Features

### 🎬 Frontend & Video Player
- **Preserved & Elevated Brand Identity**: Modern dark-mode glassmorphic interface with vibrant cyan/blue/purple gradients, micro-animations, and responsive cards.
- **Universal Player Modal**: Intelligently switches between responsive YouTube embeds and custom HTML5 `<video>` elements supporting HTTP 206 Partial Content range requests for seekable local video streaming.
- **Dynamic Navigation System**: Secondary category bar and mobile drawer are rendered directly from backend database configuration—no manual HTML edits required.
- **Live Search & Filter Autocomplete**: Real-time debounce search with instantaneous video suggestions, category badges, and direct playback.
- **Category Browsing & Sorting**: Dynamic category routes (`/category/<slug>`) with sort options (Newest, Most Viewed, Alphabetical).
- **Dynamic Section-Based Page Builder**: Custom URL routing (`/pages/<slug>`) dynamically rendering hero showcases, video grids, carousels, category spotlights, and promotional banners.

### 🛡️ Admin Dashboard (`/admin`)
- **Overview & Real Analytics**: Live statistics (Total videos, Published vs. Drafts, Categories count, Active nav tabs, Views) derived strictly from stored records, alongside recent activity audit feeds.
- **Videos Tab**: Searchable, filterable catalogue table with inline publish/draft toggles, metadata editing, thumbnail updates, and safe delete workflows with confirmation dialogs.
- **Dual Video Addition Methods**:
  - **Option 1: Upload a Local Video File**: Drag-and-drop file upload with real progress tracking, MIME/size validation, and thumbnail poster upload.
  - **Option 2: Add Video via URL**: Validates and normalizes YouTube links (standard watch, shorts, youtu.be, embeds) or direct MP4/WebM URLs, auto-extracts high-res thumbnails, and provides live preview before saving.
- **Categories Tab**: Add, rename, toggle visibility, reorder (Up/Down), and delete categories with safe video reassignment.
- **Navbar Management Tab**: Manage root and nested navigation tabs, toggle visibility for Desktop, Mobile, or Both, set destination types (Category, Page, Custom URL), and reorder tabs.
- **Pages & Layout Builder Tab**: Create new pages with custom slugs, duplicate pages, and visually configure sections (Hero Banner, Video Grid, Category Showcase, Banner, Custom Text) without writing HTML.
- **Media Library Tab**: Manage uploaded video and image assets, preview files, copy paths, and check reference dependencies before deletion.
- **Site Settings**: Manage platform brand name, tagline, announcement marquee text, and administrator contact info.
- **Activity Logs**: Full security audit trail tracking admin logins, uploads, edits, and deletions with timestamps and IP addresses.

---

## 🏗️ Architecture & Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | Python Flask 3.0+ | Lightweight REST API and server-rendered view routing |
| **ORM & Database** | Flask-SQLAlchemy (SQLAlchemy 2.0) | Declarative models; SQLite for dev, PostgreSQL for production |
| **Database Migrations**| Flask-Migrate (Alembic) | Safe database schema evolution |
| **Authentication** | Flask-Login & Werkzeug | PBKDF2-SHA256 password hashing, secure session cookies, CSRF protection |
| **Security & Headers** | Secure cookies, CORS, Rate logging | Session protection, SameSite=Lax, HttpOnly |
| **Media Handling** | Pillow (PIL), mimetypes, UUID | Secure filename generation, validation, and thumbnail creation |
| **Production Server** | Waitress (Windows/Linux) / Gunicorn | High-performance WSGI production server |
| **Frontend UI** | HTML5, CSS3, Vanilla ES6+, Bootstrap 5.3 | Modular, framework-independent, responsive glassmorphic UI |

---

## 📁 Repository Directory Structure

```
VIDSPLAY/
├── app.py                      # Application factory, blueprints registration & CLI
├── config.py                   # Development, Testing, and Production configurations
├── wsgi.py                     # Production entry point running Waitress
├── requirements.txt            # Python dependencies
├── seed_data.py                # Database seeder (imports 46 original videos & 9 categories)
├── .env.example                # Environment variables template
├── .env                        # Local development environment configuration
│
├── models/                     # SQLAlchemy Relational Models
│   ├── __init__.py             # DB instance and model exports
│   ├── user.py                 # AdminUser model with password hashing & roles
│   ├── video.py                # Video model (YouTube / Local / External, stats)
│   ├── category.py             # Category model (slug, name, icon, order)
│   ├── navigation.py           # NavigationItem model (targets, visibility, hierarchy)
│   ├── page.py                 # Page & PageSection models for the Page Builder
│   ├── media.py                # MediaAsset model (uploads tracking)
│   └── site.py                 # SiteSetting & ActivityLog models
│
├── routes/                     # Modular API Blueprints & Page Views
│   ├── __init__.py
│   ├── api_auth.py             # Admin login, logout, session check
│   ├── api_videos.py           # Video CRUD, local uploads, YouTube validator
│   ├── api_categories.py       # Category CRUD & video counts
│   ├── api_navigation.py       # Dynamic navbar CRUD & reordering
│   ├── api_pages.py            # Page & Section builder CRUD & reordering
│   ├── api_media.py            # Media library uploads & safe deletion
│   ├── api_dashboard.py        # Analytics stats, activity logs, settings
│   └── views.py                # Frontend page routes & HTTP range video streaming
│
├── utils/                      # Helper Utilities
│   ├── auth_helpers.py         # @admin_required route decorator
│   ├── media_handler.py        # File validation & secure upload handling
│   ├── url_parser.py           # YouTube & video URL validator / normalizer
│   └── streaming.py            # HTTP 206 Partial Content Range streaming
│
├── static/                     # Static Assets
│   ├── css/
│   │   ├── style.css           # Preserved legacy styles
│   │   ├── modern.css          # Modern glassmorphic theme & video card styling
│   │   └── admin.css           # Admin dashboard sidebar, tables & dropzones
│   ├── js/
│   │   ├── app.js              # Dynamic navbar rendering & live search
│   │   ├── player.js           # Universal modal player (YouTube & HTML5 Video)
│   │   └── admin.js            # Admin Dashboard SPA logic & reordering
│   ├── img/                    # All 55 preserved original images & logo
│   └── uploads/                # Local development media storage
│       ├── videos/
│       ├── thumbnails/
│       └── banners/
│
├── templates/                  # Jinja2 Layouts & Pages
│   ├── base.html               # Master layout with dynamic header & player modal
│   ├── index.html              # Modern Homepage with hero & category showcases
│   ├── category.html           # Dynamic category page with sorting & video cards
│   ├── page_builder.html       # Visual section-based dynamic page renderer (/pages/<slug>)
│   ├── admin/
│   │   ├── login.html          # Secure Admin Login page
│   │   └── dashboard.html      # Complete Admin Dashboard with all 9 tabs
│   └── errors/
│       ├── 404.html            # Custom not found page
│       └── 500.html            # Custom server error page
│
└── tests/                      # Automated Pytest Suite
    ├── conftest.py             # Fixtures with in-memory DB & auth client
    ├── test_auth.py            # Authentication & authorization tests
    ├── test_videos.py          # Video addition, YouTube parsing & visibility tests
    ├── test_categories.py      # Category CRUD & ordering tests
    ├── test_navigation.py      # Navbar tab management tests
    └── test_pages.py           # Page & Section builder tests
```

---

## 🚀 Local Setup Instructions (Windows)

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Setup Virtual Environment & Install Dependencies
Open PowerShell inside the repository folder:
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install requirements
python -m pip install -r requirements.txt
```

### 3. Initialize & Seed Database
The seeder will automatically create the database schema, default admin credentials, site settings, all 9 original categories, 10 navbar items, and import all 46 existing videos from the repository HTML files:
```powershell
python seed_data.py
```

### 4. Run the Development Server
```powershell
python app.py
```
Open your browser at:
- **Public Website**: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- **Admin Portal**: [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login)

---

## 🔑 Default Administrator Credentials

- **Username**: `admin`
- **Password**: `admin123`

To securely create or update an administrator account via CLI:
```powershell
flask --app app create-admin --username admin --email admin@vidsplay.com
```

---

## 🧪 Running Automated Tests

Run the complete test suite verifying authentication, video CRUD, YouTube URL normalization, draft/published visibility, category management, navbar ordering, and page builder operations:
```powershell
.\.venv\Scripts\python -m pytest -v
```

---

## 🌐 Production Deployment Guide

### Environment Variables
Configure the following in your production environment (e.g., Render, Railway, AWS, DigitalOcean):
```bash
FLASK_ENV=production
SECRET_KEY=generate-a-strong-random-64-character-secret
DATABASE_URL=postgresql://username:password@hostname:5432/vidsplay
UPLOAD_FOLDER=static/uploads
PORT=5000
```

### Running with WSGI Server
On Windows / Cross-platform:
```powershell
python wsgi.py
```
On Linux with Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app('production')"
```

### Media Storage in Production
- For small-to-medium deployments, persistent container volumes mounted to `static/uploads/` can be used.
- For high-volume production, configure an S3-compatible object store (AWS S3, Cloudflare R2, DigitalOcean Spaces) by updating `utils/media_handler.py`.

---

## 🛡️ License
Copyright © 2026 VIDSPLAY. All rights reserved.
