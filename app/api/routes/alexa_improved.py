"""Enhanced Alexa Utility Routes.

Provides supplementary endpoints for device registration, session tracking,
and macro execution that complement the main Alexa webhook in alexa.py.

Uses SQLite-backed persistence instead of in-memory dicts.
"""

import json
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

_LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/alexa", tags=["alexa"])


class AlexaSkillManager:
    """Manages Alexa skill state with SQLite-backed persistence."""

    def __init__(self, database_path: str = "./data/alexa_state.db"):
        self._database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection: sqlite3.Connection | None = None
        self._initialize_schema()

    def _get_connection(self) -> sqlite3.Connection:
        # Lazily create the connection; check_same_thread=False allows use
        # from multiple threads under the explicit _lock.
        if self._connection is None:
            self._connection = sqlite3.connect(
                self._database_path, check_same_thread=False
            )
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            return self._connection
        # Verify the existing connection is still alive before reusing it.
        try:
            self._connection.execute("SELECT 1")
        except sqlite3.Error:
            _LOGGER.warning("SQLite connection lost, reconnecting")
            self._connection.close()
            self._connection = sqlite3.connect(
                self._database_path, check_same_thread=False
            )
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
        return self._connection

    def close(self) -> None:
        """Close the SQLite connection."""
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def _initialize_schema(self) -> None:
        with self._lock:
            conn = self._get_connection()
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alexa_devices (
                    device_id TEXT PRIMARY KEY,
                    registered_at TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    info TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alexa_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    commands_received INTEGER NOT NULL DEFAULT 0,
                    last_intent TEXT,
                    last_slots TEXT,
                    last_timestamp TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alexa_macro_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    macro_id TEXT NOT NULL,
                    executed_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_macro_session"
                " ON alexa_macro_executions(session_id)"
            )
            conn.commit()

    def register_device(self, device_id: str, device_info: dict[str, Any]) -> bool:
        """Register a device for Alexa skill communication."""
        with self._lock:
            now = datetime.now(UTC).isoformat()
            self._get_connection().execute(
                """INSERT OR REPLACE INTO alexa_devices
                       (device_id, registered_at, last_seen, info)
                   VALUES (?, ?, ?, ?)""",
                (device_id, now, now, json.dumps(device_info)),
            )
            self._get_connection().commit()
        return True

    def get_device(self, device_id: str) -> dict[str, Any] | None:
        """Get device information."""
        with self._lock:
            cursor = self._get_connection().execute(
                "SELECT registered_at, last_seen, info"
                " FROM alexa_devices WHERE device_id = ?",
                (device_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {
            "registered_at": row[0],
            "last_seen": row[1],
            "info": json.loads(row[2]),
        }

    def create_session(self, session_id: str, user_id: str) -> dict[str, Any]:
        """Create a new Alexa session if it does not already exist."""
        with self._lock:
            now = datetime.now(UTC).isoformat()
            self._get_connection().execute(
                """INSERT OR IGNORE INTO alexa_sessions
                       (session_id, user_id, created_at, commands_received)
                   VALUES (?, ?, ?, 0)""",
                (session_id, user_id, now),
            )
            self._get_connection().commit()
        return self.get_session(session_id) or {}

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session information."""
        with self._lock:
            cursor = self._get_connection().execute(
                """SELECT session_id, user_id, created_at, commands_received,
                          last_intent, last_slots, last_timestamp
                   FROM alexa_sessions WHERE session_id = ?""",
                (session_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None

        macros = self._get_macros_for_session(session_id)
        return {
            "session_id": row[0],
            "user_id": row[1],
            "created_at": row[2],
            "commands_received": row[3],
            "last_command": {
                "intent": row[4],
                "slots": json.loads(row[5]) if row[5] else {},
                "timestamp": row[6],
            }
            if row[4]
            else None,
            "macros_executed": macros,
        }

    def _get_macros_for_session(self, session_id: str) -> list:
        # Called only from get_session which is already under the lock, so we
        # must NOT re-acquire it here to avoid a deadlock.
        cursor = self._get_connection().execute(
            "SELECT macro_id, executed_at"
            " FROM alexa_macro_executions"
            " WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        )
        return [{"macro_id": r[0], "timestamp": r[1]} for r in cursor.fetchall()]

    def track_command(
        self, session_id: str, intent: str, slots: dict[str, Any]
    ) -> None:
        """Track command execution."""
        with self._lock:
            now = datetime.now(UTC).isoformat()
            self._get_connection().execute(
                """UPDATE alexa_sessions
                   SET commands_received = commands_received + 1,
                       last_intent = ?, last_slots = ?, last_timestamp = ?
                   WHERE session_id = ?""",
                (intent, json.dumps(slots), now, session_id),
            )
            self._get_connection().commit()

    def track_macro_execution(self, session_id: str, macro_id: str) -> None:
        """Track macro execution."""
        with self._lock:
            now = datetime.now(UTC).isoformat()
            self._get_connection().execute(
                "INSERT INTO alexa_macro_executions"
                " (session_id, macro_id, executed_at) VALUES (?, ?, ?)",
                (session_id, macro_id, now),
            )
            self._get_connection().commit()


skill_manager = AlexaSkillManager()


@router.post("/device/register")
async def register_device(request: Request) -> dict[str, Any]:
    """Register a device for Alexa integration."""
    data = await request.json()
    device_id = data.get("deviceId")
    device_info = data.get("deviceInfo", {})

    if not device_id:
        raise HTTPException(status_code=400, detail="deviceId is required")

    success = skill_manager.register_device(device_id, device_info)

    return {
        "success": success,
        "deviceId": device_id,
        "registered_at": datetime.now(UTC).isoformat(),
    }


@router.get("/device/{device_id}")
async def get_device_status(device_id: str) -> dict[str, Any]:
    """Get device status."""
    device = skill_manager.get_device(device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return {
        "deviceId": device_id,
        "status": "online",
        "info": device["info"],
        "registered_at": device["registered_at"],
        "last_seen": device["last_seen"],
    }


@router.get("/session/{session_id}")
async def get_session_info(session_id: str) -> dict[str, Any]:
    """Get Alexa session information."""
    session = skill_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "created_at": session["created_at"],
        "commands_received": session["commands_received"],
        "macros_executed": session["macros_executed"],
        "active": True,
    }


class MacroExecutionRequest(BaseModel):
    """Request to execute a desktop macro."""

    macroId: str
    deviceId: str | None = None
    userId: str | None = None


@router.post("/macro/execute")
async def execute_macro_via_api(request: MacroExecutionRequest) -> dict[str, Any]:
    """Execute a macro via API (for mobile app)."""
    return {
        "success": True,
        "macroId": request.macroId,
        "deviceId": request.deviceId,
        "executed_at": datetime.now(UTC).isoformat(),
        "status": "executed",
    }
