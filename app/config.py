import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/signage.db")
