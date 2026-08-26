import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

conn = psycopg.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
)

chunk_id = "document_01_chunk003"

with conn.cursor() as cur:
    cur.execute(
        """
        SELECT chunk_id, document_id, title, source, category, text
        FROM chunks WHERE chunk_id = %s;
        """,
        (chunk_id,),
    )
    row = cur.fetchone()
    if row:
        print("=" * 70)
        print(f"Chunk ID : {row[0]}")
        print(f"Document : {row[1]}")
        print(f"Title    : {row[2]}")
        print(f"Source   : {row[3]}")
        print(f"Category : {row[4]}")
        print("=" * 70)
        print(row[5])
    else:
        print("Chunk not found.")

conn.close()
