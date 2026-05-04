import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Pastikan di .env DATABASE_URL menggunakan format: 
# postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Engine: Jembatan ke Supabase
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # Pool size disesuaikan agar tidak melebihi kuota koneksi Supabase Free Tier
    pool_size=5, 
    max_overflow=10
)

# SessionLocal: Pabrik untuk membuat sesi database per request API
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base: Class induk untuk semua Models kita
Base = declarative_base()