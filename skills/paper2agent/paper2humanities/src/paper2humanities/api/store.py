from __future__ import annotations
from pathlib import Path
from threading import RLock
from datetime import datetime, timezone
import json, sqlite3

from ..debate.models import DebateSession

def _now():
    return datetime.now(timezone.utc).isoformat()

class SQLiteSessionStore:
    def __init__(self, db_path: str|Path):
        self.db_path=Path(db_path)
        self.db_path.parent.mkdir(parents=True,exist_ok=True)
        self._lock=RLock()
        self._init_db()
        self.mark_running_interrupted()

    def _connect(self):
        conn=sqlite3.connect(self.db_path,timeout=30,check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory=sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock,self._connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS sessions(
                session_id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                participant_ids TEXT NOT NULL,
                max_turns INTEGER NOT NULL,
                current_turn INTEGER NOT NULL,
                status TEXT NOT NULL,
                active_issue TEXT,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id,id);
            """)

    def put(self,session:DebateSession):
        data=session.to_dict()
        now=_now()
        with self._lock,self._connect() as c:
            row=c.execute("SELECT created_at FROM sessions WHERE session_id=?",(session.session_id,)).fetchone()
            created=row["created_at"] if row else now
            c.execute("""
                INSERT INTO sessions(session_id,topic,participant_ids,max_turns,current_turn,status,active_issue,payload_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(session_id) DO UPDATE SET
                  topic=excluded.topic,
                  participant_ids=excluded.participant_ids,
                  max_turns=excluded.max_turns,
                  current_turn=excluded.current_turn,
                  status=excluded.status,
                  active_issue=excluded.active_issue,
                  payload_json=excluded.payload_json,
                  updated_at=excluded.updated_at
            """,(
                session.session_id,session.topic,json.dumps(session.participant_ids,ensure_ascii=False),
                session.max_turns,session.current_turn,session.status,session.active_issue,
                json.dumps(data,ensure_ascii=False),created,now
            ))
        return session

    def get(self,session_id:str)->DebateSession:
        with self._lock,self._connect() as c:
            row=c.execute("SELECT payload_json FROM sessions WHERE session_id=?",(session_id,)).fetchone()
            if not row: raise KeyError(session_id)
        return DebateSession.from_dict(json.loads(row["payload_json"]))

    def list(self,limit:int=100)->list[DebateSession]:
        with self._lock,self._connect() as c:
            rows=c.execute("SELECT payload_json FROM sessions ORDER BY updated_at DESC LIMIT ?",(limit,)).fetchall()
        return [DebateSession.from_dict(json.loads(r["payload_json"])) for r in rows]

    def append_event(self,session_id:str,event_type:str,data:dict)->int:
        with self._lock,self._connect() as c:
            cur=c.execute(
                "INSERT INTO events(session_id,event_type,data_json,created_at) VALUES(?,?,?,?)",
                (session_id,event_type,json.dumps(data,ensure_ascii=False),_now())
            )
            return int(cur.lastrowid)

    def events_after(self,session_id:str,after_id:int=0)->list[dict]:
        with self._lock,self._connect() as c:
            rows=c.execute(
                "SELECT id,event_type,data_json,created_at FROM events WHERE session_id=? AND id>? ORDER BY id",
                (session_id,after_id)
            ).fetchall()
        return [{
            "id":int(r["id"]),
            "event":r["event_type"],
            "data":json.loads(r["data_json"]),
            "created_at":r["created_at"],
        } for r in rows]

    def mark_running_interrupted(self)->int:
        with self._lock,self._connect() as c:
            rows=c.execute("SELECT session_id,payload_json FROM sessions WHERE status='RUNNING'").fetchall()
            count=0
            for row in rows:
                data=json.loads(row["payload_json"])
                data["status"]="INTERRUPTED"
                c.execute(
                    "UPDATE sessions SET status='INTERRUPTED',payload_json=?,updated_at=? WHERE session_id=?",
                    (json.dumps(data,ensure_ascii=False),_now(),row["session_id"])
                )
                c.execute(
                    "INSERT INTO events(session_id,event_type,data_json,created_at) VALUES(?,?,?,?)",
                    (row["session_id"],"session_interrupted",
                     json.dumps({"reason":"server_restart"},ensure_ascii=False),_now())
                )
                count+=1
            return count

    def counts(self)->dict:
        with self._lock,self._connect() as c:
            rows=c.execute("SELECT status,COUNT(*) AS n FROM sessions GROUP BY status").fetchall()
        return {r["status"]:int(r["n"]) for r in rows}

SessionStore=SQLiteSessionStore
