from __future__ import annotations
from threading import Lock

class SessionStore:
    def __init__(self):
        self._items={}
        self._lock=Lock()
    def put(self, session):
        with self._lock:
            self._items[session.session_id]=session
        return session
    def get(self, session_id):
        with self._lock:
            if session_id not in self._items:
                raise KeyError(session_id)
            return self._items[session_id]
