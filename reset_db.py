
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

HOST = os.environ.get("PGHOST", "127.0.0.1")
PORT = os.environ.get("PGPORT", "5432")
DB_NAME = os.environ.get("PGDATABASE", "online_restaurant")
USER = os.environ.get("PGUSER", "postgres")
PASSWORD = os.environ.get("PGPASSWORD")

if not PASSWORD:
    raise SystemExit("PGPASSWORD is not set. Specify it in the .env file before running reset_db.py")

conn = psycopg2.connect(host=HOST, port=PORT, dbname=DB_NAME, user=USER, password=PASSWORD)
conn.autocommit = True

try:
    with conn.cursor() as cur:
        print("[RESET] Dropping schema public...")
        cur.execute("DROP SCHEMA public CASCADE;")
        print("[RESET] Creating schema public...")
        cur.execute("CREATE SCHEMA public;")
        print("[RESET] Restoring privileges...")
        cur.execute("GRANT ALL ON SCHEMA public TO %s;" % USER)
        cur.execute("GRANT ALL ON SCHEMA public TO public;")
        print("[RESET] Schema reset complete.")
finally:
    conn.close()
