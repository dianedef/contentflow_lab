"""
Run History - Persistent memory for robot workflows.

Stores run metadata in SQLite so robots can consult their past runs
before making decisions ("when did I last publish?", "is my SEO score improving?")

Usage:
    from agents.shared.run_history import RunHistory

    # As a context manager (recommended)
    with RunHistory().start("scheduler", "weekly_analysis", inputs={"max_pages": 100}) as run:
        result = do_work()
        run.set_outputs({"score": 85, "issues": 3})
    # run.status is automatically set to "success" or "error"

    # Query history
    history = RunHistory()
    last = history.get_last_run("scheduler", "publish_content")
    recent = history.get_last_runs("site_health_monitor", n=5)
    stats = history.get_stats("scheduler")
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional


DB_PATH = Path(__file__).parent.parent.parent / "data" / "runs" / "runs.db"


def _get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Get a SQLite connection with row_factory set."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    """Initialize the database schema."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS robot_runs (
            run_id          TEXT PRIMARY KEY,
            robot_name      TEXT NOT NULL,
            workflow_type   TEXT NOT NULL,
            started_at      TEXT NOT NULL,
            finished_at     TEXT,
            status          TEXT NOT NULL DEFAULT 'running',
            inputs_json     TEXT,
            outputs_summary_json TEXT,
            error           TEXT,
            duration_ms     INTEGER
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_robot_name ON robot_runs(robot_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_started_at ON robot_runs(started_at)")
    conn.commit()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a sqlite3.Row to a plain dict with parsed JSON fields."""
    d = dict(row)
    for field in ("inputs_json", "outputs_summary_json"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


class _RunContext:
    """
    Mutable context object returned by RunHistory.start().
    Use .set_outputs() inside the with-block to record results.
    """

    def __init__(
        self,
        history: "RunHistory",
        run_id: str,
        robot_name: str,
        workflow_type: str,
        started_at: str,
    ):
        self._history = history
        self.run_id = run_id
        self.robot_name = robot_name
        self.workflow_type = workflow_type
        self.started_at = started_at
        self.status: str = "running"
        self._outputs: Optional[Dict[str, Any]] = None
        self._error: Optional[str] = None
        self._force_failed: Optional[str] = None  # set by mark_failed()

    def set_outputs(self, outputs: Dict[str, Any]) -> None:
        """Record output summary for this run."""
        self._outputs = outputs

    def mark_failed(self, reason: str = "") -> None:
        """
        Mark this run as failed even when no exception is raised
        (e.g. for early-return failure paths inside the with-block).

        Example:
            with rh.start("scheduler", "publish") as run:
                if not result.get("success"):
                    run.mark_failed("scheduling step failed")
                    return {"success": False, ...}
        """
        self._force_failed = reason

    def _finish(self, status: str, error: Optional[str] = None) -> None:
        # Honor explicit mark_failed() over the default "success" from clean exit
        if self._force_failed is not None and status == "success":
            status = "error"
            error = self._force_failed
        finished_at = datetime.utcnow().isoformat()
        started_dt = datetime.fromisoformat(self.started_at)
        finished_dt = datetime.fromisoformat(finished_at)
        duration_ms = int((finished_dt - started_dt).total_seconds() * 1000)
        self.status = status

        self._history._update_run(
            run_id=self.run_id,
            finished_at=finished_at,
            status=status,
            outputs_summary=self._outputs,
            error=error,
            duration_ms=duration_ms,
        )


class RunHistory:
    """
    Persistent run history backed by SQLite.

    Robots use this to:
    - Record their runs (via context manager)
    - Query past runs before making decisions
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or DB_PATH
        self._conn = _get_connection(self._db_path)
        _init_db(self._conn)

    @contextmanager
    def start(
        self,
        robot_name: str,
        workflow_type: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Generator[_RunContext, None, None]:
        """
        Context manager that creates a run record, yields a _RunContext,
        and finalises the record (success or error) on exit.

        Example:
            with RunHistory().start("scheduler", "weekly_analysis", {"max_pages": 50}) as run:
                result = do_heavy_work()
                run.set_outputs({"score": result["score"]})
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.utcnow().isoformat()

        self._conn.execute(
            """
            INSERT INTO robot_runs
                (run_id, robot_name, workflow_type, started_at, status, inputs_json)
            VALUES (?, ?, ?, ?, 'running', ?)
            """,
            (run_id, robot_name, workflow_type, started_at, json.dumps(inputs) if inputs else None),
        )
        self._conn.commit()

        ctx = _RunContext(
            history=self,
            run_id=run_id,
            robot_name=robot_name,
            workflow_type=workflow_type,
            started_at=started_at,
        )

        try:
            yield ctx
            ctx._finish("success")
        except Exception as exc:
            ctx._error = str(exc)
            ctx._finish("error", error=str(exc))
            raise

    def _update_run(
        self,
        run_id: str,
        finished_at: str,
        status: str,
        outputs_summary: Optional[Dict[str, Any]],
        error: Optional[str],
        duration_ms: int,
    ) -> None:
        self._conn.execute(
            """
            UPDATE robot_runs
            SET finished_at = ?,
                status = ?,
                outputs_summary_json = ?,
                error = ?,
                duration_ms = ?
            WHERE run_id = ?
            """,
            (
                finished_at,
                status,
                json.dumps(outputs_summary) if outputs_summary else None,
                error,
                duration_ms,
                run_id,
            ),
        )
        self._conn.commit()

    # ─── Query Methods ────────────────────────────────────────────────────────

    def get_last_run(
        self,
        robot_name: str,
        workflow_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Return the most recent run for a robot (optionally filtered by workflow_type and status).

        Example:
            last = history.get_last_run("scheduler", "publish_content")
            if last and last["status"] == "success":
                print(f"Last published at {last['finished_at']}")
        """
        query = "SELECT * FROM robot_runs WHERE robot_name = ?"
        params: list = [robot_name]
        if workflow_type:
            query += " AND workflow_type = ?"
            params.append(workflow_type)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY started_at DESC LIMIT 1"

        cursor = self._conn.execute(query, params)
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None

    def get_last_runs(
        self,
        robot_name: str,
        n: int = 10,
        workflow_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return the last n runs for a robot.

        Example:
            recent = history.get_last_runs("site_health_monitor", n=5)
            scores = [r["outputs_summary_json"].get("seo_score") for r in recent if r["outputs_summary_json"]]
        """
        query = "SELECT * FROM robot_runs WHERE robot_name = ?"
        params: list = [robot_name]
        if workflow_type:
            query += " AND workflow_type = ?"
            params.append(workflow_type)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(n)

        cursor = self._conn.execute(query, params)
        return [_row_to_dict(row) for row in cursor.fetchall()]

    def get_all_runs(
        self,
        robot_name: Optional[str] = None,
        workflow_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return runs across all robots, with optional filters."""
        query = "SELECT * FROM robot_runs WHERE 1=1"
        params: list = []
        if robot_name:
            query += " AND robot_name = ?"
            params.append(robot_name)
        if workflow_type:
            query += " AND workflow_type = ?"
            params.append(workflow_type)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        cursor = self._conn.execute(query, params)
        return [_row_to_dict(row) for row in cursor.fetchall()]

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Return a single run by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM robot_runs WHERE run_id = ?", (run_id,)
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None

    def get_stats(self, robot_name: str) -> Dict[str, Any]:
        """
        Return aggregate stats for a robot.

        Returns:
            {
                "total_runs": int,
                "success_runs": int,
                "error_runs": int,
                "success_rate": float,          # 0.0–1.0
                "avg_duration_ms": float | None,
                "last_run_at": str | None,
                "last_success_at": str | None,
            }
        """
        cursor = self._conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successes,
                SUM(CASE WHEN status = 'error'   THEN 1 ELSE 0 END) as errors,
                AVG(CASE WHEN duration_ms IS NOT NULL THEN duration_ms END) as avg_ms,
                MAX(started_at) as last_run,
                MAX(CASE WHEN status = 'success' THEN finished_at END) as last_success
            FROM robot_runs
            WHERE robot_name = ?
            """,
            (robot_name,),
        )
        row = cursor.fetchone()
        if not row or row["total"] == 0:
            return {
                "total_runs": 0,
                "success_runs": 0,
                "error_runs": 0,
                "success_rate": 0.0,
                "avg_duration_ms": None,
                "last_run_at": None,
                "last_success_at": None,
            }
        total = row["total"]
        successes = row["successes"] or 0
        return {
            "total_runs": total,
            "success_runs": successes,
            "error_runs": row["errors"] or 0,
            "success_rate": round(successes / total, 3),
            "avg_duration_ms": round(row["avg_ms"]) if row["avg_ms"] else None,
            "last_run_at": row["last_run"],
            "last_success_at": row["last_success"],
        }
