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

4. Ensure environment variables are set

Environment file `.env` can be found in the Google Drive folder. See `.env.example` for the fields.

## Auth (Google OAuth + JWT)

Minimal Google OAuth flow that enforces UCLA domains via OIDC ID token verification.

Endpoints:
- `GET /api/v1/auth/login` → Redirects to Google
- `GET /api/v1/auth/callback` → Exchanges code, verifies ID token, returns app JWT
- `GET /api/v1/auth/me` → Current user (requires `Authorization: Bearer <token>`)
- `POST /api/v1/auth/logout` → Clears transient OAuth state cookie

Required env vars (in addition to DB settings):
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI` (e.g., `http://localhost:8000/api/v1/auth/callback`)
- `ALLOWED_GOOGLE_HD` (comma-separated list, default: `ucla.edu,g.ucla.edu`)
- `JWT_SECRET_KEY` (generate a strong secret)
- `JWT_ALGORITHM` (default `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default `60`)

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
