import asyncio
import sys
import os
sys.path.append(os.getcwd())
from sqlalchemy import text
from app.db.session import get_db

async def check_data():
    async for session in get_db():
        # Check current names
        print("--- Current Month (Jan 2026) Names ---")
        q_curr = text("""
            SELECT DISTINCT territory, COUNT(*) as count 
            FROM tbldeliveryinfo 
            WHERE delivery_date >= '2026-01-01' AND delivery_date < '2026-02-01' 
            AND territory LIKE '%Masum%'
            GROUP BY territory
        """)
        res = await session.execute(q_curr)
        for row in res:
            print(f"'{row[0]}': {row[1]} orders")

        # Check previous names
        print("\n--- Previous Month (Dec 2025) Names ---")
        q_prev = text("""
            SELECT DISTINCT territory, COUNT(*) as count 
            FROM tbldeliveryinfo 
            WHERE delivery_date >= '2025-12-01' AND delivery_date < '2026-01-01' 
            AND territory LIKE '%Masum%'
            GROUP BY territory
        """)
        res = await session.execute(q_prev)
        rows = res.fetchall()
        if not rows:
            print("No matches found for '%Masum%' in Dec 2025.")
        for row in rows:
            print(f"'{row[0]}': {row[1]} orders")

if __name__ == "__main__":
    asyncio.run(check_data())
