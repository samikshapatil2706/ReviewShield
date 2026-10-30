import hashlib
import json
import sqlite3
import os
from datetime import datetime
import database


class Block:
    """
    Represents an individual block in the application-level blockchain.
    Stores cryptographic hashes and metadata to ensure tamper-evidence.
    """

    def __init__(
        self,
        index,
        review_id,
        review_hash,
        prediction,
        confidence,
        previous_hash,
        timestamp=None,
        current_hash=None
    ):
        self.index = index
        self.review_id = review_id
        self.review_hash = review_hash
        self.prediction = prediction
        self.confidence = confidence
        self.previous_hash = previous_hash
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_hash = current_hash or self.calculate_block_hash()

    def calculate_block_hash(self):
        """
        Computes SHA-256 cryptographic digest over all block payload attributes.
        """
        block_string = (
            f"{self.index}{self.review_id}{self.review_hash}"
            f"{self.prediction}{self.confidence}{self.previous_hash}{self.timestamp}"
        )
        return hashlib.sha256(block_string.encode('utf-8')).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "review_id": self.review_id,
            "review_hash": self.review_hash,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "previous_hash": self.previous_hash,
            "current_hash": self.current_hash,
            "timestamp": self.timestamp
        }


class Blockchain:
    """
    Application-level SHA-256 linked blockchain.
    Maintains an immutable cryptographic audit trail of review submissions
    and their ML classifications.
    Note: This is a private, application-level audit ledger for demonstration,
    not a public decentralized cryptocurrency network.
    """

    def __init__(self):
        self.init_blockchain_table()
        self.ensure_genesis_block()

    def init_blockchain_table(self):
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blockchain_blocks (
                block_index INTEGER PRIMARY KEY,
                review_id INTEGER,
                review_hash TEXT NOT NULL,
                prediction TEXT NOT NULL,
                confidence REAL NOT NULL,
                previous_hash TEXT NOT NULL,
                current_hash TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def ensure_genesis_block(self):
        chain = self.get_chain()
        if len(chain) == 0:
            genesis_hash = hashlib.sha256(b"GENESIS_REVIEW_DATA").hexdigest()
            genesis_block = Block(
                index=0,
                review_id=0,
                review_hash=genesis_hash,
                prediction="Genesis",
                confidence=100.0,
                previous_hash="0" * 64,
                timestamp="2026-01-01 00:00:00"
            )
            self._save_block_to_db(genesis_block)

    def _save_block_to_db(self, block):
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO blockchain_blocks (
                block_index,
                review_id,
                review_hash,
                prediction,
                confidence,
                previous_hash,
                current_hash,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            block.index,
            block.review_id,
            block.review_hash,
            block.prediction,
            block.confidence,
            block.previous_hash,
            block.current_hash,
            block.timestamp
        ))
        conn.commit()
        conn.close()

    def get_chain(self):
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM blockchain_blocks ORDER BY block_index ASC')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_latest_block(self):
        chain = self.get_chain()
        return chain[-1] if chain else None

    @staticmethod
    def hash_review_text(review_text):
        if not isinstance(review_text, str):
            review_text = ""
        return hashlib.sha256(review_text.encode('utf-8')).hexdigest()

    def add_review_block(self, review_id, review_text, prediction, confidence):
        """
        Creates and appends a single review block to the blockchain ledger.
        """
        latest = self.get_latest_block()
        new_index = latest['block_index'] + 1 if latest else 0
        prev_hash = latest['current_hash'] if latest else "0" * 64

        rev_hash = self.hash_review_text(review_text)

        new_block = Block(
            index=new_index,
            review_id=review_id,
            review_hash=rev_hash,
            prediction=prediction,
            confidence=confidence,
            previous_hash=prev_hash
        )

        self._save_block_to_db(new_block)
        database.mark_reviews_in_blockchain([review_id])
        return new_block

    def add_review_blocks_batch(self, reviews_data):
        """
        Appends multiple review blocks in sequence in a single transaction.
        Each block links to the previous block's hash.
        """
        if not reviews_data:
            return []

        conn = database.get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT block_index, current_hash FROM blockchain_blocks ORDER BY block_index DESC LIMIT 1')
        latest = cursor.fetchone()

        current_index = (latest['block_index'] + 1) if latest else 0
        current_prev_hash = latest['current_hash'] if latest else "0" * 64

        created_blocks = []
        review_ids_to_mark = []

        try:
            cursor.execute("BEGIN TRANSACTION")
            for item in reviews_data:
                rev_id = item.get("review_id", 0)
                rev_text = item.get("review_text", "")
                pred = item.get("prediction", "Unknown")
                conf = float(item.get("confidence", 0.0))

                rev_hash = self.hash_review_text(rev_text)
                block = Block(
                    index=current_index,
                    review_id=rev_id,
                    review_hash=rev_hash,
                    prediction=pred,
                    confidence=conf,
                    previous_hash=current_prev_hash
                )

                cursor.execute('''
                    INSERT INTO blockchain_blocks (
                        block_index,
                        review_id,
                        review_hash,
                        prediction,
                        confidence,
                        previous_hash,
                        current_hash,
                        timestamp
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    block.index,
                    block.review_id,
                    block.review_hash,
                    block.prediction,
                    block.confidence,
                    block.previous_hash,
                    block.current_hash,
                    block.timestamp
                ))

                current_prev_hash = block.current_hash
                current_index += 1
                created_blocks.append(block)
                if rev_id > 0:
                    review_ids_to_mark.append(rev_id)

            conn.commit()
        except Exception:
            conn.rollback()
            conn.close()
            raise

        conn.close()

        if review_ids_to_mark:
            database.mark_reviews_in_blockchain(review_ids_to_mark)

        return created_blocks

    def get_block_by_review_id(self, review_id):
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM blockchain_blocks WHERE review_id = ?', (review_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def verify_review_integrity(self, review_id, current_review_text):
        """
        Cryptographically verifies whether current_review_text matches
        the recorded SHA-256 hash in its corresponding blockchain block.
        Also checks continuity of the chain up to that block.
        """
        block = self.get_block_by_review_id(review_id)
        if not block:
            return {
                "status": "NOT_FOUND",
                "is_valid": False,
                "review_id": review_id,
                "message": f"No blockchain block found for Review #{review_id}"
            }

        recorded_hash = block['review_hash']
        calculated_hash = self.hash_review_text(current_review_text)

        hashes_match = (recorded_hash == calculated_hash)

        # Check chain continuity across all blocks
        chain = self.get_chain()
        chain_intact = True
        for i in range(1, len(chain)):
            if chain[i]['previous_hash'] != chain[i - 1]['current_hash']:
                chain_intact = False
                break

        return {
            "review_id": review_id,
            "block_index": block['block_index'],
            "status": "VALID" if (hashes_match and chain_intact) else "TAMPERED",
            "is_valid": bool(hashes_match and chain_intact),
            "hashes_match": hashes_match,
            "chain_intact": chain_intact,
            "recorded_hash": recorded_hash,
            "calculated_hash": calculated_hash,
            "block": block
        }
