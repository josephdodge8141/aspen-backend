import os
from sqlmodel import create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aspen_user:aspen_pass@db:5432/aspen_dev")

engine = create_engine(DATABASE_URL, echo=True) 