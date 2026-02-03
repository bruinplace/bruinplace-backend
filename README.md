# BruinPlace Backend

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (AWS RDS)
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Package Manager**: uv

## Prerequisites

- Python 3.12+
- PostgreSQL database (local or AWS RDS)
- uv package manager

## Installation

### 1. Install uv (if not already installed)

**macOS (Homebrew):**
```bash
brew install uv
```

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

See [uv installation documentation](https://docs.astral.sh/uv/getting-started/installation/) for more details.

### 2. Clone the Repository

```bash
git clone <repository-url>
cd bruinplace-backend
```

### 3. Install Dependencies

```bash
uv sync
```

This will:
- Create a virtual environment (`.venv`) if not already present
- Install all dependencies from the existing `uv.lock` file

### 4. Set Up Environment Variables

Environment file `.env` can be found in the Google Drive folder. See `.env.example` for the required fields.

## Database Migrations

Migrations use the same database as the app (from `.env`: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`).

### Create a New Migration

After changing models in `app/db/models/`:

```bash
uv run alembic revision --autogenerate -m "describe your change"
```

Review the generated file in `alembic/versions/` before applying.

### Apply Migrations

```bash
uv run alembic upgrade head
```

### Check Current Migration Version

```bash
uv run alembic current
```

### Migration History

```bash
uv run alembic history
```

> **⚠️ Warning: Downgrades**  
> Avoid running `alembic downgrade` unless you know exactly what you're doing. Downgrades can drop tables or columns and **cause permanent data loss**. Only use downgrade in development or when you have a backup and understand the migration you're reverting.

## Running the Application

### Development Server

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000/api/v1
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

### Custom Host/Port

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```
