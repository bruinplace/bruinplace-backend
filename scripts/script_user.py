"""Create and reuse a shared script user for local scripts.

Usage:
    uv run python scripts/run_script.py script_user

Future scripts can import:
    from scripts.script_user import SCRIPT_USER_ID, ensure_script_user
"""

from dataclasses import dataclass

from app.api.v1.users.models import User
from app.db.session import SessionLocal


@dataclass(frozen=True)
class ScriptUserConfig:
    id: str = "bruinplace-script-user"
    email: str = "bruin@bruinplace.dev"
    name: str = "BruinPlace Script User"
    profile_picture: str | None = None


SCRIPT_USER = ScriptUserConfig()
SCRIPT_USER_ID = SCRIPT_USER.id


def ensure_script_user(db, *, config: ScriptUserConfig = SCRIPT_USER) -> User:
    """Return the shared script user, creating it when missing."""
    existing = db.get(User, config.id)
    if existing:
        return existing

    user = User(
        id=config.id,
        email=config.email,
        name=config.name,
        profile_picture=config.profile_picture,
    )
    db.add(user)
    db.flush()
    return user


def seed_script_user() -> None:
    db = SessionLocal()
    try:
        user = ensure_script_user(db)
        db.commit()
        print(f"Script user ready: id={user.id}, email={user.email}")
    except Exception:
        print("Error seeding script user, rolling back")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_script_user()
