"""Split CET4 CSV into 3 books and import into ciye database."""
import csv
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from server.db import get_conn, init_db, now_iso, today

CSV_PATH = r"E:\Codex\danci\data\英语四级高频词汇_submission.csv"

def main():
    init_db()
    conn = get_conn()

    # Remove old demo book
    conn.execute("DELETE FROM progress")
    conn.execute("DELETE FROM words")
    conn.execute("DELETE FROM books")
    conn.commit()

    # Read CSV
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get("word", "").strip()]

    total = len(rows)
    chunk = total // 3
    parts = [
        ("英语四级高频词汇（一）", rows[:chunk]),
        ("英语四级高频词汇（二）", rows[chunk:chunk*2]),
        ("英语四级高频词汇（三）", rows[chunk*2:]),
    ]

    for name, words in parts:
        book_id = conn.execute(
            "INSERT INTO books(name, created_at) VALUES(?, ?)", (name, now_iso())
        ).lastrowid
        count = 0
        for r in words:
            word = r["word"].strip().lower()
            if not word:
                continue
            try:
                wid = conn.execute(
                    """INSERT INTO words(book_id, word, translation, definition, example, created_at)
                       VALUES(?, ?, ?, ?, ?, ?)""",
                    (book_id, word, r.get("translation", ""), r.get("definition", ""), r.get("example", ""), now_iso()),
                ).lastrowid
                conn.execute("INSERT OR IGNORE INTO progress(word_id, due_date) VALUES(?, ?)", (wid, today()))
                count += 1
            except Exception:
                continue
        conn.commit()
        print(f"[OK] {name}: {count} words")

    # Set first book as active
    first_id = conn.execute("SELECT id FROM books ORDER BY id ASC LIMIT 1").fetchone()
    if first_id:
        from server.db import set_setting
        set_setting("active_book_id", str(first_id["id"]))
        print(f"[OK] Default book set to id={first_id['id']}")

    print("Done!")

if __name__ == "__main__":
    main()
