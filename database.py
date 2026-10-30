import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join("data", "app_database.db")


def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initializes the SQLite database with safe, backward-compatible schema migrations.
    Preserves all existing data in tables.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Base reviews table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_text TEXT NOT NULL,
            cleaned_text TEXT,
            prediction TEXT NOT NULL,
            is_suspicious INTEGER NOT NULL,
            confidence REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Inspect existing columns for backward-compatible migration
    cursor.execute("PRAGMA table_info(reviews)")
    existing_columns = {row['name'] for row in cursor.fetchall()}

    if "original_text" not in existing_columns:
        cursor.execute("ALTER TABLE reviews ADD COLUMN original_text TEXT")
        cursor.execute("UPDATE reviews SET original_text = review_text WHERE original_text IS NULL")

    if "is_tampered" not in existing_columns:
        cursor.execute("ALTER TABLE reviews ADD COLUMN is_tampered INTEGER DEFAULT 0")
        cursor.execute("UPDATE reviews SET is_tampered = 0 WHERE is_tampered IS NULL")

    if "batch_id" not in existing_columns:
        cursor.execute("ALTER TABLE reviews ADD COLUMN batch_id TEXT")

    if "source" not in existing_columns:
        cursor.execute("ALTER TABLE reviews ADD COLUMN source TEXT DEFAULT 'single'")
        cursor.execute("UPDATE reviews SET source = 'single' WHERE source IS NULL")

    if "in_blockchain" not in existing_columns:
        cursor.execute("ALTER TABLE reviews ADD COLUMN in_blockchain INTEGER DEFAULT 0")

    # Safely backfill in_blockchain for any reviews that already have corresponding blocks in blockchain_blocks
    cursor.execute('''
        SELECT name FROM sqlite_master WHERE type='table' AND name='blockchain_blocks'
    ''')
    if cursor.fetchone():
        cursor.execute('''
            UPDATE reviews 
            SET in_blockchain = 1 
            WHERE (in_blockchain IS NULL OR in_blockchain = 0)
              AND id IN (SELECT review_id FROM blockchain_blocks WHERE review_id > 0)
        ''')

    conn.commit()
    conn.close()


def insert_review(
    review_text,
    cleaned_text,
    prediction,
    is_suspicious,
    confidence,
    source="single",
    batch_id=None,
    in_blockchain=0
):
    """
    Inserts a single review record. Fully backward-compatible with original signature.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute('''
        INSERT INTO reviews (
            review_text,
            original_text,
            cleaned_text,
            prediction,
            is_suspicious,
            confidence,
            is_tampered,
            batch_id,
            source,
            in_blockchain,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
    ''', (
        review_text,
        review_text,
        cleaned_text,
        prediction,
        1 if is_suspicious else 0,
        confidence,
        batch_id,
        source,
        1 if in_blockchain else 0,
        now_str
    ))

    review_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return review_id


def insert_reviews_batch(reviews_list, batch_id=None, source="csv", in_blockchain=0):
    """
    Inserts multiple reviews in a single transaction.
    Prevents accidental duplicate entries when a batch request is retried.
    """
    if not reviews_list:
        return []

    conn = get_db_connection()
    cursor = conn.cursor()

    # Idempotency / Duplicate Prevention Check
    if batch_id:
        cursor.execute(
            "SELECT id, review_text, cleaned_text, prediction, is_suspicious, confidence, batch_id, source, in_blockchain, created_at "
            "FROM reviews WHERE batch_id = ? ORDER BY id ASC",
            (batch_id,)
        )
        existing_rows = cursor.fetchall()
        if existing_rows:
            conn.close()
            return [dict(row) for row in existing_rows]

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inserted_records = []

    try:
        cursor.execute("BEGIN TRANSACTION")
        for item in reviews_list:
            cursor.execute('''
                INSERT INTO reviews (
                    review_text,
                    original_text,
                    cleaned_text,
                    prediction,
                    is_suspicious,
                    confidence,
                    is_tampered,
                    batch_id,
                    source,
                    in_blockchain,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
            ''', (
                item["review_text"],
                item["review_text"],
                item.get("cleaned_text", ""),
                item["prediction"],
                1 if item.get("is_suspicious") else 0,
                item["confidence"],
                batch_id,
                source,
                1 if in_blockchain else 0,
                now_str
            ))
            rec_id = cursor.lastrowid
            record_copy = dict(item)
            record_copy["id"] = rec_id
            record_copy["batch_id"] = batch_id
            record_copy["source"] = source
            record_copy["in_blockchain"] = 1 if in_blockchain else 0
            record_copy["created_at"] = now_str
            inserted_records.append(record_copy)

        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise

    conn.close()
    return inserted_records


def mark_reviews_in_blockchain(review_ids):
    """
    Marks one or more review IDs as recorded in the blockchain ledger.
    """
    if not review_ids:
        return

    if isinstance(review_ids, int):
        review_ids = [review_ids]

    conn = get_db_connection()
    cursor = conn.cursor()

    placeholders = ",".join("?" for _ in review_ids)
    cursor.execute(
        f"UPDATE reviews SET in_blockchain = 1 WHERE id IN ({placeholders})",
        review_ids
    )
    conn.commit()
    conn.close()


def get_all_reviews(source=None):
    """
    Retrieves all reviews, ordered by descending ID.
    Optionally filters by source ('single', 'csv', 'url').
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if source:
        cursor.execute('''
            SELECT id, review_text, COALESCE(original_text, review_text) as original_text,
                   cleaned_text, prediction, is_suspicious, confidence,
                   COALESCE(is_tampered, 0) as is_tampered,
                   batch_id, COALESCE(source, 'single') as source,
                   COALESCE(in_blockchain, 0) as in_blockchain, created_at
            FROM reviews
            WHERE source = ?
            ORDER BY id DESC
        ''', (source,))
    else:
        cursor.execute('''
            SELECT id, review_text, COALESCE(original_text, review_text) as original_text,
                   cleaned_text, prediction, is_suspicious, confidence,
                   COALESCE(is_tampered, 0) as is_tampered,
                   batch_id, COALESCE(source, 'single') as source,
                   COALESCE(in_blockchain, 0) as in_blockchain, created_at
            FROM reviews
            ORDER BY id DESC
        ''')

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_review_by_id(review_id):
    """
    Retrieves a single review by primary key ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, review_text, COALESCE(original_text, review_text) as original_text,
               cleaned_text, prediction, is_suspicious, confidence,
               COALESCE(is_tampered, 0) as is_tampered,
               batch_id, COALESCE(source, 'single') as source,
               COALESCE(in_blockchain, 0) as in_blockchain, created_at
        FROM reviews WHERE id = ?
    ''', (review_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_reviews_by_batch_id(batch_id):
    """
    Retrieves all reviews associated with a specific batch identifier.
    """
    if not batch_id:
        return []
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, review_text, COALESCE(original_text, review_text) as original_text,
               cleaned_text, prediction, is_suspicious, confidence,
               COALESCE(is_tampered, 0) as is_tampered,
               batch_id, COALESCE(source, 'single') as source,
               COALESCE(in_blockchain, 0) as in_blockchain, created_at
        FROM reviews WHERE batch_id = ?
        ORDER BY id ASC
    ''', (batch_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def tamper_review(review_id, tampered_text):
    """
    Demonstration feature: Alters a review text to simulate unauthorized data modification.
    Sets is_tampered flag to 1.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE reviews
        SET review_text = ?, is_tampered = 1
        WHERE id = ?
    ''', (tampered_text, review_id))
    conn.commit()
    conn.close()


def restore_review(review_id):
    """
    Restores the review text to its original pre-tampered content and resets is_tampered to 0.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT COALESCE(original_text, review_text) as original_text FROM reviews WHERE id = ?',
        (review_id,)
    )
    row = cursor.fetchone()
    if row:
        orig = row['original_text']
        cursor.execute('''
            UPDATE reviews
            SET review_text = ?, is_tampered = 0
            WHERE id = ?
        ''', (orig, review_id))
        conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    reviews = get_all_reviews()
    print(f"Database schema initialized. Total existing reviews: {len(reviews)}")
