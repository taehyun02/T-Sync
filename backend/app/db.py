import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL이 설정되지 않았습니다.")
    return psycopg2.connect(DATABASE_URL)