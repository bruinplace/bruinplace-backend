from sqlalchemy.orm import declarative_base
Base = declarative_base()

# Import models so that metadata is aware for table creation / migrations
from app.db.models.user import User
