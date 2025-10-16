
import sqlite3
from datetime import datetime
from typing import List, Tuple
import os
from receipt_ocr.processors import ReceiptProcessor
from receipt_ocr.providers import OpenAIProvider
import json 
json_schema = {
    "merchant_name": "string",
    "merchant_address": "string",
    "transaction_date": "string",
    "transaction_time": "string",
    "total_amount": "number",
    "line_items": [
        {
            "item_name": "string",
            "item_quantity": "number",
            "item_price": "number",
        }
    ],
}
class ReceiptDB:
    def __init__(self, db_path="media/receipts.db"):
        # Ensure the media directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Connect to SQLite database (will create the file if it doesn't exist)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self.create_table()
        provider = OpenAIProvider()
        self.ocr_receipt = ReceiptProcessor(provider)

    def create_table(self):
        """Create the receipts table if it doesn't exist"""
        query = """
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            content TEXT NOT NULL
        )
        """
        self.conn.execute(query)
        self.conn.commit()

    def add(self, date: str, image_path: str):
        """Add a new receipt"""
        result = self.ocr_receipt.process_receipt(image_path, json_schema)
        if isinstance(result, dict) and "error" in result:
            raise ValueError(result["error"])  # raise exception with the error message
        ocr_str = json.dumps(result)
        query = "INSERT INTO receipts (date, content) VALUES (?, ?)"
        self.conn.execute(query, (date, ocr_str))
        self.conn.commit()

    def delete(self, receipt_id: int):
        """Delete a receipt by its ID"""
        query = "DELETE FROM receipts WHERE id = ?"
        self.conn.execute(query, (receipt_id,))
        self.conn.commit()

    def retrieve_by_date_range(self, start_date: str, end_date: str):
        """Retrieve receipts between start_date and end_date (inclusive)"""
        query = """
        SELECT * FROM receipts
        WHERE date BETWEEN ? AND ?
        ORDER BY date
        """
        cursor = self.conn.execute(query, (start_date, end_date))
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close the database connection"""
        self.conn.close()
