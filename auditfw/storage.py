
"""SQLite storage. A single-writer connection serializes sequence numbers,
guaranteeing gap-free, monotonically increasing seq under concurrency."""
import json, sqlite3, threading

class LogStorage:
    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.conn.execute("""CREATE TABLE IF NOT EXISTS log_entries(
            seq INTEGER PRIMARY KEY,
            event_id TEXT, timestamp INTEGER,
            entry_json TEXT NOT NULL,
            entry_hash TEXT NOT NULL)""")
        self.conn.commit()

    def next_seq_and_prev(self):
        with self.lock:
            row = self.conn.execute(
                "SELECT entry_hash FROM log_entries ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            seq = 1 if row is None else self.conn.execute(
                "SELECT COALESCE(MAX(seq),0)+1 FROM log_entries").fetchone()[0]
            return seq, row[0] if row else "GENESIS"

    def insert(self, entry: dict):
        with self.lock:
            self.conn.execute(
                "INSERT INTO log_entries(seq,event_id,timestamp,entry_json,entry_hash)"
                " VALUES(?,?,?,?,?)",
                (entry["seq"], entry["event_id"], entry["timestamp"],
                 json.dumps(entry), entry["entry_hash"]))
            self.conn.commit()

    def iter_entries(self):
        cur = self.conn.execute(
            "SELECT entry_json FROM log_entries ORDER BY seq")
        for (js,) in cur:
            yield json.loads(js)

    def checkpoint_record(self):
        row = self.conn.execute(
            "SELECT seq, entry_hash FROM log_entries ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        return {"head_seq": row[0], "head_hash": row[1]} if row else None
