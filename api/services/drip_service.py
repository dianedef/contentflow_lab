"""
Drip Service — Orchestrates progressive content publication.

Manages DripPlan CRUD in SQLite and delegates ContentRecord operations
to the existing StatusService.
"""

import hashlib
import json
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from status.service import StatusService, ContentNotFoundError
from status.audit import actor_from_agent
from api.services.frontmatter import (
    apply_frontmatter_patch,
    has_frontmatter,
    read_frontmatter,
    update_frontmatter as update_fm_file,
)
from zoneinfo import ZoneInfo


class DripPlanNotFoundError(Exception):
    pass


class DripService:
    """
    Orchestrate progressive content publication.
    Plans are stored in the drip_plans table.
    Items are ContentRecords with source_robot='drip'.
    """

    def __init__(self, status_svc: StatusService):
        self.svc = status_svc
        self._conn = status_svc._conn

    # ─── Plan CRUD ────────────────────────────────────

    def create_plan(
        self,
        name: str,
        user_id: str,
        cadence_config: Dict[str, Any],
        cluster_strategy: Optional[Dict[str, Any]] = None,
        ssg_config: Optional[Dict[str, Any]] = None,
        gsc_config: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new drip plan."""
        now = datetime.utcnow().isoformat()
        plan_id = str(uuid.uuid4())

        self._conn.execute(
            """
            INSERT INTO drip_plans
            (id, user_id, project_id, name, status,
             cadence_config, cluster_strategy, ssg_config, gsc_config,
             total_items, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'draft', ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                plan_id,
                user_id,
                project_id,
                name,
                json.dumps(cadence_config),
                json.dumps(cluster_strategy or {}),
                json.dumps(ssg_config or {}),
                json.dumps(gsc_config) if gsc_config else None,
                now,
                now,
            ),
        )
        self._conn.commit()
        return self.get_plan(plan_id)

    def get_plan(self, plan_id: str) -> Dict[str, Any]:
        """Get a drip plan by ID."""
        row = self._conn.execute(
            "SELECT * FROM drip_plans WHERE id = ?", (plan_id,)
        ).fetchone()
        if not row:
            raise DripPlanNotFoundError(f"Drip plan {plan_id} not found")
        return self._row_to_plan(row)

    def list_plans(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List drip plans with optional filters."""
        query = "SELECT * FROM drip_plans WHERE 1=1"
        params: List[Any] = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY updated_at DESC"
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_plan(row) for row in rows]

    def update_plan(self, plan_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Update a drip plan's fields."""
        self.get_plan(plan_id)  # Ensure exists

        allowed = {
            "name", "status", "cadence_config", "cluster_strategy",
            "ssg_config", "gsc_config", "total_items",
            "started_at", "completed_at", "last_drip_at", "next_drip_at",
            "schedule_job_id", "project_id",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return self.get_plan(plan_id)

        # Serialize JSON fields
        for json_field in ("cadence_config", "cluster_strategy", "ssg_config", "gsc_config"):
            if json_field in updates and updates[json_field] is not None:
                updates[json_field] = json.dumps(updates[json_field])

        updates["updated_at"] = datetime.utcnow().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [plan_id]

        self._conn.execute(
            f"UPDATE drip_plans SET {set_clause} WHERE id = ?",
            values,
        )
        self._conn.commit()
        return self.get_plan(plan_id)

    def delete_plan(self, plan_id: str) -> None:
        """Delete a drip plan and its associated ContentRecords."""
        self.get_plan(plan_id)  # Ensure exists

        # Delete associated ContentRecords (source_robot='drip' with matching plan_id in metadata)
        self._conn.execute(
            """
            DELETE FROM content_records
            WHERE source_robot = 'drip'
            AND json_extract(metadata, '$.drip_plan_id') = ?
            """,
            (plan_id,),
        )

        self._conn.execute("DELETE FROM drip_plans WHERE id = ?", (plan_id,))
        self._conn.commit()

    # ─── Plan Items (ContentRecords) ──────────────────

    def get_plan_items(
        self,
        plan_id: str,
        status: Optional[str] = None,
    ) -> List[Any]:
        """Get all ContentRecords belonging to a drip plan."""
        query = """
            SELECT * FROM content_records
            WHERE source_robot = 'drip'
            AND json_extract(metadata, '$.drip_plan_id') = ?
        """
        params: List[Any] = [plan_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY CAST(json_extract(metadata, '$.position') AS INTEGER) ASC"
        rows = self._conn.execute(query, params).fetchall()
        return [self.svc._row_to_record(row) for row in rows]

    def get_plan_stats(self, plan_id: str) -> Dict[str, Any]:
        """Get statistics for a drip plan's items."""
        rows = self._conn.execute(
            """
            SELECT status, COUNT(*) as count
            FROM content_records
            WHERE source_robot = 'drip'
            AND json_extract(metadata, '$.drip_plan_id') = ?
            GROUP BY status
            """,
            (plan_id,),
        ).fetchall()

        by_status = {row["status"]: row["count"] for row in rows}
        total = sum(by_status.values())

        # Get cluster breakdown
        cluster_rows = self._conn.execute(
            """
            SELECT
                json_extract(metadata, '$.cluster_name') as cluster_name,
                status,
                COUNT(*) as count
            FROM content_records
            WHERE source_robot = 'drip'
            AND json_extract(metadata, '$.drip_plan_id') = ?
            GROUP BY cluster_name, status
            """,
            (plan_id,),
        ).fetchall()

        clusters: Dict[str, Dict[str, int]] = {}
        for row in cluster_rows:
            cname = row["cluster_name"] or "orphans"
            if cname not in clusters:
                clusters[cname] = {}
            clusters[cname][row["status"]] = row["count"]

        cluster_list = [
            {"name": name, "by_status": statuses, "total": sum(statuses.values())}
            for name, statuses in clusters.items()
        ]

        return {
            "total_items": total,
            "by_status": by_status,
            "clusters": cluster_list,
        }

    # ─── Import Content ─────────────────────────────────

    def import_from_directory(
        self,
        plan_id: str,
        directory: str,
        extensions: Tuple[str, ...] = (".md", ".mdx"),
        exclude_drafts: bool = True,
    ) -> int:
        """Scan a directory for Markdown files, create a ContentRecord per file.

        Returns the number of items imported.
        """
        plan = self.get_plan(plan_id)
        ssg = plan.get("ssg_config", {}) or {}
        base = Path(directory)
        if not base.is_dir():
            raise ValueError(f"Directory not found: {directory}")

        date_field = ssg.get("frontmatter_date_field", "pubDate")
        draft_field = ssg.get("frontmatter_draft_field", "draft")
        robots_field = ssg.get("frontmatter_robots_field", "robots")
        opt_in_field = ssg.get("frontmatter_opt_in_field", "dripManaged")

        count = 0
        for ext in extensions:
            for file_path in sorted(base.rglob(f"*{ext}")):
                # Skip files starting with _ (templates, partials)
                if file_path.name.startswith("_"):
                    continue

                fm = read_frontmatter(str(file_path))

                # Skip drafts if requested
                if exclude_drafts and fm.get("draft") is True:
                    continue

                title = fm.get("title", file_path.stem)
                rel_path = str(file_path.relative_to(base))

                # Compute content hash for dedup
                raw = file_path.read_bytes()
                content_hash = hashlib.sha256(raw).hexdigest()[:16]

                # Check for existing record with same path in this plan
                existing = self._conn.execute(
                    """
                    SELECT id FROM content_records
                    WHERE source_robot = 'drip'
                    AND json_extract(metadata, '$.drip_plan_id') = ?
                    AND content_path = ?
                    """,
                    (plan_id, rel_path),
                ).fetchone()
                if existing:
                    continue  # Already imported

                # Extract tags for later clustering
                tags = fm.get("tags", [])
                if isinstance(tags, str):
                    tags = [tags]

                snapshot_fields = {
                    str(date_field): {"present": str(date_field) in fm, "value": fm.get(str(date_field))},
                    str(draft_field): {"present": str(draft_field) in fm, "value": fm.get(str(draft_field))},
                    str(robots_field): {"present": str(robots_field) in fm, "value": fm.get(str(robots_field))},
                    str(opt_in_field): {"present": str(opt_in_field) in fm, "value": fm.get(str(opt_in_field))},
                }

                self.svc.create_content(
                    title=title,
                    content_type="article",
                    source_robot="drip",
                    status="approved",  # Existing content, ready to schedule
                    project_id=plan.get("project_id"),
                    user_id=plan.get("user_id"),
                    content_path=rel_path,
                    content_preview=fm.get("description", "")[:500],
                    content_hash=content_hash,
                    tags=tags,
                    metadata={
                        "drip_plan_id": plan_id,
                        "position": count,
                        "cluster_id": None,
                        "cluster_name": None,
                        "is_pillar": False,
                        "frontmatter_pub_date": fm.get("pubDate", ""),
                        "abs_path": str(file_path),
                        "frontmatter_has_block": has_frontmatter(str(file_path)),
                        "frontmatter_snapshot": {
                            "captured_at": datetime.utcnow().isoformat(),
                            "fields": snapshot_fields,
                        },
                    },
                )
                count += 1

        # Update plan total
        self.update_plan(plan_id, total_items=count)
        return count

    # ─── Clustering ──────────────────────────────────

    def cluster_by_directory(self, plan_id: str) -> Dict[str, Any]:
        """Group plan items by their directory structure.

        Each subdirectory becomes a cluster. Files in the root are "orphans".
        index.md files are marked as pillars.
        """
        items = self.get_plan_items(plan_id)
        clusters: Dict[str, List] = defaultdict(list)

        for item in items:
            path = Path(item.content_path)
            parts = path.parts

            if len(parts) <= 1:
                # Root-level file
                cluster_name = "_root"
            else:
                # Use first 2 directory levels as cluster name
                # e.g. "seo/contenu/champ-semantique.md" → "seo/contenu"
                cluster_name = "/".join(parts[:-1])

            clusters[cluster_name].append(item)

        # Assign cluster info to each item
        cluster_id_map: Dict[str, str] = {}
        position = 0

        # Sort clusters: bigger clusters first (more topical authority)
        sorted_clusters = sorted(clusters.items(), key=lambda x: -len(x[1]))

        for cluster_name, cluster_items in sorted_clusters:
            if cluster_name not in cluster_id_map:
                cluster_id_map[cluster_name] = str(uuid.uuid4())[:8]
            cid = cluster_id_map[cluster_name]

            # Identify pillar: index.md or the file with the shortest name
            pillar_id = None
            for ci in cluster_items:
                fname = Path(ci.content_path).stem
                if fname in ("index", cluster_name.split("/")[-1] if "/" in cluster_name else ""):
                    pillar_id = ci.id
                    break

            # Sort within cluster: pillar first, then alphabetically
            def sort_key(item):
                is_pillar = item.id == pillar_id
                return (0 if is_pillar else 1, item.content_path)

            for ci in sorted(cluster_items, key=sort_key):
                is_pillar = ci.id == pillar_id
                metadata = ci.metadata.copy() if isinstance(ci.metadata, dict) else {}
                metadata.update({
                    "cluster_id": cid,
                    "cluster_name": cluster_name,
                    "is_pillar": is_pillar,
                    "position": position,
                })
                self.svc.update_content(ci.id, metadata=metadata)
                position += 1

        summary = {
            "total_clusters": len(clusters),
            "clusters": [
                {"name": name, "count": len(items), "cluster_id": cluster_id_map.get(name)}
                for name, items in sorted_clusters
            ],
            "total_items": position,
        }
        return summary

    def cluster_by_tags(self, plan_id: str) -> Dict[str, Any]:
        """Group plan items by their primary tag (first tag in the list).

        Items with no tags go into an '_untagged' cluster.
        The item with the most tags in a cluster is considered the pillar
        (broadest coverage = most likely a pillar page).
        """
        items = self.get_plan_items(plan_id)
        clusters: Dict[str, List] = defaultdict(list)

        for item in items:
            tags = item.tags or []
            primary_tag = tags[0].lower().strip() if tags else "_untagged"
            clusters[primary_tag].append(item)

        cluster_id_map: Dict[str, str] = {}
        position = 0
        sorted_clusters = sorted(clusters.items(), key=lambda x: -len(x[1]))

        for cluster_name, cluster_items in sorted_clusters:
            if cluster_name not in cluster_id_map:
                cluster_id_map[cluster_name] = str(uuid.uuid4())[:8]
            cid = cluster_id_map[cluster_name]

            # Pillar heuristic: most tags = broadest scope,
            # or shortest title (usually more general)
            pillar_item = max(
                cluster_items,
                key=lambda ci: (len(ci.tags or []), -len(ci.title)),
            )
            pillar_id = pillar_item.id

            def sort_key(item, _pid=pillar_id):
                return (0 if item.id == _pid else 1, item.title)

            for ci in sorted(cluster_items, key=sort_key):
                is_pillar = ci.id == pillar_id
                metadata = ci.metadata.copy() if isinstance(ci.metadata, dict) else {}
                metadata.update({
                    "cluster_id": cid,
                    "cluster_name": cluster_name,
                    "is_pillar": is_pillar,
                    "position": position,
                })
                self.svc.update_content(ci.id, metadata=metadata)
                position += 1

        return {
            "total_clusters": len(clusters),
            "clusters": [
                {"name": name, "count": len(items), "cluster_id": cluster_id_map.get(name)}
                for name, items in sorted_clusters
            ],
            "total_items": position,
        }

    def cluster_auto(
        self,
        plan_id: str,
        repo_url: Optional[str] = None,
        local_repo_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Detect semantic cocoons using the Topical Mesh Architect agent.

        Falls back to directory clustering if the mesh agent is unavailable.

        Args:
            repo_url: GitHub repo URL (for remote analysis)
            local_repo_path: Local path to the repo (preferred, avoids git clone)
        """
        if not repo_url and not local_repo_path:
            # Fallback: use directory clustering
            return self.cluster_by_directory(plan_id)

        try:
            from agents.seo.tools.mesh_analyzer import ExistingMeshAnalyzer
        except ImportError:
            # CrewAI/agents not available — fall back to directory clustering
            return self.cluster_by_directory(plan_id)

        analyzer = ExistingMeshAnalyzer()

        # Run the mesh analysis
        if local_repo_path:
            result = analyzer.analyze_existing_website(
                repo_url=repo_url or "local",
                local_repo_path=local_repo_path,
                force_update=False,
            )
        else:
            result = analyzer.analyze_existing_website(
                repo_url=repo_url,
                force_update=True,
            )

        # Extract clusters from mesh analysis
        existing_mesh = result.get("existing_mesh", {})
        cluster_pages = existing_mesh.get("cluster_pages", [])
        orphan_pages = existing_mesh.get("orphan_pages", [])
        pillar_page = existing_mesh.get("pillar_page")

        items = self.get_plan_items(plan_id)
        items_by_path: Dict[str, Any] = {}
        for item in items:
            # Normalize paths for matching
            items_by_path[item.content_path] = item
            items_by_path[Path(item.content_path).stem] = item

        assigned = set()
        position = 0
        cluster_summaries = []

        # Assign items to clusters detected by the mesh
        for cluster in cluster_pages:
            cluster_name = cluster.get("topic", cluster.get("name", "unknown"))
            cid = str(uuid.uuid4())[:8]
            pages = cluster.get("pages", [])
            matched = []

            for page_path in pages:
                # Try matching by path or stem
                item = items_by_path.get(page_path) or items_by_path.get(Path(page_path).stem)
                if item and item.id not in assigned:
                    matched.append(item)
                    assigned.add(item.id)

            if not matched:
                continue

            # Pillar: match against detected pillar or first page
            pillar_id = None
            if pillar_page:
                pi = items_by_path.get(pillar_page) or items_by_path.get(Path(pillar_page).stem)
                if pi and pi.id in {m.id for m in matched}:
                    pillar_id = pi.id
            if not pillar_id:
                pillar_id = matched[0].id

            for ci in matched:
                is_pillar = ci.id == pillar_id
                metadata = ci.metadata.copy() if isinstance(ci.metadata, dict) else {}
                metadata.update({
                    "cluster_id": cid,
                    "cluster_name": cluster_name,
                    "is_pillar": is_pillar,
                    "position": position,
                })
                self.svc.update_content(ci.id, metadata=metadata)
                position += 1

            cluster_summaries.append({"name": cluster_name, "count": len(matched), "cluster_id": cid})

        # Handle orphans (items not matched to any cluster)
        orphan_items = [i for i in items if i.id not in assigned]
        if orphan_items:
            cid = str(uuid.uuid4())[:8]
            for ci in orphan_items:
                metadata = ci.metadata.copy() if isinstance(ci.metadata, dict) else {}
                metadata.update({
                    "cluster_id": cid,
                    "cluster_name": "_orphans",
                    "is_pillar": False,
                    "position": position,
                })
                self.svc.update_content(ci.id, metadata=metadata)
                position += 1
            cluster_summaries.append({"name": "_orphans", "count": len(orphan_items), "cluster_id": cid})

        return {
            "total_clusters": len(cluster_summaries),
            "clusters": cluster_summaries,
            "total_items": position,
            "mesh_authority_score": result.get("authority_score"),
            "mesh_grade": result.get("authority_grade"),
        }

    # ─── Scheduling ──────────────────────────────────

    def generate_schedule(
        self,
        plan_id: str,
        dry_run: bool = False,
    ) -> List[Dict[str, Any]]:
        """Assign scheduled_for dates to all plan items based on cadence config.

        If dry_run=True, returns the schedule without writing to DB.
        """
        plan = self.get_plan(plan_id)
        cadence = plan["cadence_config"]
        cluster = plan.get("cluster_strategy", {}) or {}
        ssg = plan.get("ssg_config", {}) or {}
        items = self.get_plan_items(plan_id)

        if not items:
            return []

        start_date = date.fromisoformat(cadence["start_date"])
        publish_days = set(cadence.get("publish_days", [0, 1, 2, 3, 4]))
        mode = cadence.get("mode", "fixed")
        items_per_day = cadence.get("items_per_day", 3)
        ramp_schedule = cadence.get("ramp_schedule")
        publish_time = cadence.get("publish_time", "06:00")
        timezone = cadence.get("timezone", "Europe/Paris")
        spacing_minutes = int(cadence.get("spacing_minutes", 180) or 0)
        cluster_gap_days = int(cluster.get("cluster_gap_days", 0) or 0)
        gating = ssg.get("gating_method", "future_date")
        enforce_robots = bool(ssg.get("enforce_robots_noindex_until_publish", False))
        robots_field = ssg.get("frontmatter_robots_field", "robots")
        robots_noindex_value = ssg.get("robots_noindex_value", "noindex, follow")
        require_opt_in = bool(ssg.get("require_opt_in", False))
        opt_in_field = ssg.get("frontmatter_opt_in_field", "dripManaged")
        opt_in_value = ssg.get("frontmatter_opt_in_value", True)

        try:
            publish_hour, publish_minute = (int(x) for x in str(publish_time).split(":"))
        except Exception:
            publish_hour, publish_minute = 6, 0

        try:
            tz = ZoneInfo(str(timezone))
        except Exception:
            tz = ZoneInfo("UTC")

        # Build the schedule
        schedule: List[Dict[str, Any]] = []
        current_date = start_date
        day_offset = 0
        item_idx = 0
        last_cluster_name: Optional[str] = None

        while item_idx < len(items):
            current_item = items[item_idx]
            current_cluster_name = (current_item.metadata or {}).get("cluster_name")
            if (
                cluster_gap_days > 0
                and last_cluster_name is not None
                and current_cluster_name is not None
                and current_cluster_name != last_cluster_name
            ):
                current_date += timedelta(days=cluster_gap_days)
                day_offset += cluster_gap_days
                last_cluster_name = current_cluster_name

            # Skip non-publish days
            if current_date.weekday() not in publish_days:
                current_date += timedelta(days=1)
                day_offset += 1
                continue

            # Determine today's cadence
            today_count = items_per_day
            if mode == "ramp_up" and ramp_schedule:
                # Find the applicable ramp step
                for step in sorted(ramp_schedule, key=lambda s: s["from_day"], reverse=True):
                    if day_offset >= step["from_day"]:
                        today_count = step["items_per_day"]
                        break

            # Assign items for today
            for slot_index in range(today_count):
                if item_idx >= len(items):
                    break

                item = items[item_idx]
                entry = {
                    "item_id": item.id,
                    "title": item.title,
                    "content_path": item.content_path,
                    "scheduled_date": current_date.isoformat(),
                    "position": item_idx,
                    "cluster_name": (item.metadata or {}).get("cluster_name"),
                    "is_pillar": (item.metadata or {}).get("is_pillar", False),
                }
                schedule.append(entry)

                if not dry_run:
                    # scheduled_for is persisted in UTC (naive ISO string), but computed from local time.
                    local_dt = datetime(
                        current_date.year,
                        current_date.month,
                        current_date.day,
                        publish_hour,
                        publish_minute,
                        0,
                        tzinfo=tz,
                    )
                    if spacing_minutes > 0 and slot_index > 0:
                        local_dt = local_dt + timedelta(minutes=spacing_minutes * slot_index)
                    scheduled_dt = local_dt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
                    self.svc.update_content(
                        item.id,
                        scheduled_for=scheduled_dt,
                    )
                    self.svc.transition(item.id, "scheduled", actor_from_agent("drip_scheduler"))

                    # Optional "index-proof" gating: enforce noindex/draft until publish tick flips them.
                    abs_path = (item.metadata or {}).get("abs_path")
                    if abs_path and Path(abs_path).exists():
                        if require_opt_in:
                            fm = read_frontmatter(str(abs_path))
                            if fm.get(str(opt_in_field)) != opt_in_value:
                                item_idx += 1
                                continue
                        fm_updates: Dict[str, Any] = {}
                        if gating in ("draft_flag", "both"):
                            fm_updates[ssg.get("frontmatter_draft_field", "draft")] = True
                        if enforce_robots and robots_field:
                            fm_updates[str(robots_field)] = str(robots_noindex_value)
                        if fm_updates:
                            try:
                                update_fm_file(str(abs_path), fm_updates)
                            except Exception:
                                pass

                item_idx += 1
                last_cluster_name = (item.metadata or {}).get("cluster_name") or last_cluster_name

            current_date += timedelta(days=1)
            day_offset += 1

        # Update plan with next drip info
        if not dry_run and schedule:
            first_item = self.svc.get_content(schedule[0]["item_id"])
            self.update_plan(
                plan_id,
                next_drip_at=first_item.scheduled_for.isoformat() if first_item.scheduled_for else None,
            )

        return schedule

    # ─── Plan Lifecycle ────────────────────────────────

    def activate_plan(self, plan_id: str) -> Dict[str, Any]:
        """Activate a draft plan: create a ScheduleJob and set status to active."""
        plan = self.get_plan(plan_id)
        if plan["status"] not in ("draft", "paused"):
            raise ValueError(f"Cannot activate plan in status '{plan['status']}'")

        # Create a ScheduleJob for the cron tick
        job = self.svc.create_schedule_job(
            user_id=plan["user_id"],
            project_id=plan.get("project_id"),
            job_type="drip",
            configuration={"drip_plan_id": plan_id},
            schedule="hourly",
            schedule_time=plan["cadence_config"].get("publish_time", "06:00"),
            timezone=plan["cadence_config"].get("timezone", "Europe/Paris"),
            enabled=True,
            next_run_at=plan.get("next_drip_at") or datetime.utcnow().isoformat(),
        )

        return self.update_plan(
            plan_id,
            status="active",
            schedule_job_id=job["id"],
            started_at=plan.get("started_at") or datetime.utcnow().isoformat(),
        )

    def pause_plan(self, plan_id: str) -> Dict[str, Any]:
        """Pause an active plan."""
        plan = self.get_plan(plan_id)
        if plan["status"] != "active":
            raise ValueError(f"Cannot pause plan in status '{plan['status']}'")

        self.restore_plan_frontmatter(plan_id)

        # Disable the schedule job
        if plan.get("schedule_job_id"):
            try:
                self.svc.update_schedule_job(plan["schedule_job_id"], enabled=False)
            except ContentNotFoundError:
                pass

        return self.update_plan(plan_id, status="paused")

    def resume_plan(self, plan_id: str) -> Dict[str, Any]:
        """Resume a paused plan."""
        plan = self.get_plan(plan_id)
        if plan["status"] != "paused":
            raise ValueError(f"Cannot resume plan in status '{plan['status']}'")

        # Re-enable the schedule job
        if plan.get("schedule_job_id"):
            try:
                self.svc.update_schedule_job(
                    plan["schedule_job_id"],
                    enabled=True,
                    next_run_at=plan.get("next_drip_at") or datetime.utcnow().isoformat(),
                )
            except ContentNotFoundError:
                pass

        return self.update_plan(plan_id, status="active")

    def cancel_plan(self, plan_id: str) -> Dict[str, Any]:
        """Cancel a plan. Scheduled items stay as-is but no more drips execute."""
        plan = self.get_plan(plan_id)
        if plan["status"] in ("completed", "cancelled"):
            raise ValueError(f"Plan already in terminal status '{plan['status']}'")

        self.restore_plan_frontmatter(plan_id)

        # Disable the schedule job
        if plan.get("schedule_job_id"):
            try:
                self.svc.update_schedule_job(plan["schedule_job_id"], enabled=False)
            except ContentNotFoundError:
                pass

        return self.update_plan(plan_id, status="cancelled")

    # ─── Execution ───────────────────────────────────

    def execute_drip_tick(self, plan_id: str) -> Dict[str, Any]:
        """Publish items that are due today.

        For each due item:
        1. Update the frontmatter (pubDate or draft flag) in the source file
        2. Transition the ContentRecord to PUBLISHED

        Returns a summary of what was published. The caller is responsible
        for triggering the SSG rebuild after this method returns.
        """
        plan = self.get_plan(plan_id)
        if plan["status"] != "active":
            return {"published": 0, "skipped": True, "reason": f"Plan status is '{plan['status']}'"}

        ssg = plan.get("ssg_config", {})
        gating = ssg.get("gating_method", "future_date")
        date_field = ssg.get("frontmatter_date_field", "pubDate")
        draft_field = ssg.get("frontmatter_draft_field", "draft")
        enforce_robots = bool(ssg.get("enforce_robots_noindex_until_publish", False))
        robots_field = ssg.get("frontmatter_robots_field", "robots")
        robots_index_value = ssg.get("robots_index_value", "index, follow")
        require_opt_in = bool(ssg.get("require_opt_in", False))
        opt_in_field = ssg.get("frontmatter_opt_in_field", "dripManaged")
        opt_in_value = ssg.get("frontmatter_opt_in_value", True)

        now = datetime.utcnow()

        # Find scheduled items that are due
        items = self.get_plan_items(plan_id, status="scheduled")
        due_items = []
        for item in items:
            if item.scheduled_for and item.scheduled_for <= now:
                due_items.append(item)

        published = []
        errors = []

        for item in due_items:
            abs_path = (item.metadata or {}).get("abs_path")
            if not abs_path or not Path(abs_path).exists():
                errors.append({"item_id": item.id, "title": item.title, "error": "File not found"})
                continue

            try:
                if require_opt_in:
                    fm = read_frontmatter(str(abs_path))
                    if fm.get(str(opt_in_field)) != opt_in_value:
                        errors.append(
                            {
                                "item_id": item.id,
                                "title": item.title,
                                "error": f"Opt-in required: set {opt_in_field}: {opt_in_value}",
                            }
                        )
                        continue

                # Update the frontmatter based on gating method
                fm_updates = {}
                if gating in ("future_date", "both"):
                    fm_updates[date_field] = now.date().isoformat()
                if gating in ("draft_flag", "both"):
                    fm_updates[draft_field] = False
                if enforce_robots and robots_field:
                    fm_updates[str(robots_field)] = str(robots_index_value)

                if fm_updates:
                    update_fm_file(abs_path, fm_updates)

                # Transition: scheduled → publishing → published
                drip_executor = actor_from_agent("drip_executor")
                self.svc.transition(item.id, "publishing", drip_executor)
                self.svc.transition(item.id, "published", drip_executor)

                published.append({
                    "item_id": item.id,
                    "title": item.title,
                    "content_path": item.content_path,
                    "published_date": now.date().isoformat(),
                })

            except Exception as e:
                errors.append({"item_id": item.id, "title": item.title, "error": str(e)})

        # Update plan state
        update_fields: Dict[str, Any] = {"last_drip_at": now.isoformat()}

        # Check if all items are published
        remaining = self.get_plan_items(plan_id, status="scheduled")
        if not remaining:
            update_fields["status"] = "completed"
            update_fields["completed_at"] = now.isoformat()
            # Disable the schedule job
            if plan.get("schedule_job_id"):
                try:
                    self.svc.update_schedule_job(plan["schedule_job_id"], enabled=False)
                except ContentNotFoundError:
                    pass
        else:
            # Compute next drip date
            next_times = sorted(i.scheduled_for for i in remaining if i.scheduled_for)
            if next_times:
                update_fields["next_drip_at"] = next_times[0].isoformat()

        self.update_plan(plan_id, **update_fields)

        return {
            "published": len(published),
            "errors": len(errors),
            "items": published,
            "error_details": errors if errors else None,
            "plan_completed": update_fields.get("status") == "completed",
        }

    # ─── Safety & Diagnostics ─────────────────────────

    def restore_plan_frontmatter(self, plan_id: str) -> Dict[str, Any]:
        """Best-effort restore frontmatter fields for items that were pre-gated.

        Used when pausing/cancelling a plan in safe-mode contexts.
        """
        try:
            plan = self.get_plan(plan_id)
        except Exception:
            return {"success": False, "error": "Plan not found"}

        ssg = plan.get("ssg_config", {}) or {}
        date_field = str(ssg.get("frontmatter_date_field", "pubDate"))
        draft_field = str(ssg.get("frontmatter_draft_field", "draft"))
        robots_field = str(ssg.get("frontmatter_robots_field", "robots"))
        keys = {date_field, draft_field, robots_field}

        restored = 0
        skipped = 0
        errors = 0

        items = self.get_plan_items(plan_id)
        for item in items:
            if str(item.status) not in {"approved", "scheduled"}:
                skipped += 1
                continue
            abs_path = (item.metadata or {}).get("abs_path")
            if not abs_path or not Path(abs_path).exists():
                skipped += 1
                continue

            snapshot = (item.metadata or {}).get("frontmatter_snapshot") or {}
            fields = snapshot.get("fields") if isinstance(snapshot, dict) else None
            if not isinstance(fields, dict):
                skipped += 1
                continue

            updates: Dict[str, Any] = {}
            delete_keys: set[str] = set()
            for key in keys:
                record = fields.get(key)
                if not isinstance(record, dict):
                    continue
                present = bool(record.get("present"))
                if not present:
                    delete_keys.add(key)
                    continue
                if "value" in record:
                    updates[key] = record.get("value")

            if not updates and not delete_keys:
                skipped += 1
                continue

            try:
                apply_frontmatter_patch(str(abs_path), updates=updates, delete_keys=delete_keys)
                restored += 1
            except Exception:
                errors += 1

        return {"success": True, "restored": restored, "skipped": skipped, "errors": errors}

    def preflight_plan(self, plan_id: str) -> Dict[str, Any]:
        """Run a preflight check to catch index-proof and safe-mode issues."""
        plan = self.get_plan(plan_id)
        ssg = plan.get("ssg_config", {}) or {}
        require_opt_in = bool(ssg.get("require_opt_in", False))
        opt_in_field = str(ssg.get("frontmatter_opt_in_field", "dripManaged"))
        opt_in_value = ssg.get("frontmatter_opt_in_value", True)

        items = self.get_plan_items(plan_id)
        issues: List[Dict[str, Any]] = []

        for item in items:
            abs_path = (item.metadata or {}).get("abs_path")
            if not abs_path:
                issues.append({"item_id": item.id, "severity": "error", "message": "Missing abs_path metadata"})
                continue
            if not Path(abs_path).exists():
                issues.append({"item_id": item.id, "severity": "error", "message": f"File not found: {abs_path}"})
                continue
            if not has_frontmatter(str(abs_path)):
                issues.append({"item_id": item.id, "severity": "error", "message": "No YAML frontmatter block"})
                continue
            if require_opt_in:
                fm = read_frontmatter(str(abs_path))
                if fm.get(opt_in_field) != opt_in_value:
                    issues.append(
                        {
                            "item_id": item.id,
                            "severity": "warning",
                            "message": f"Opt-in missing: set {opt_in_field}: {opt_in_value}",
                        }
                    )

        severity_rank = {"error": 2, "warning": 1, "info": 0}
        worst = "info"
        for issue in issues:
            sev = issue.get("severity", "info")
            if severity_rank.get(sev, 0) > severity_rank.get(worst, 0):
                worst = sev

        return {
            "plan_id": plan_id,
            "status": plan.get("status"),
            "require_opt_in": require_opt_in,
            "opt_in_field": opt_in_field,
            "opt_in_value": opt_in_value,
            "issues": issues,
            "issue_count": len(issues),
            "severity": worst,
        }

    # ─── Private helpers ──────────────────────────────

    def _row_to_plan(self, row) -> Dict[str, Any]:
        """Convert a database row to a drip plan dict."""
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "project_id": row["project_id"],
            "name": row["name"],
            "status": row["status"],
            "cadence_config": json.loads(row["cadence_config"]) if row["cadence_config"] else {},
            "cluster_strategy": json.loads(row["cluster_strategy"]) if row["cluster_strategy"] else {},
            "ssg_config": json.loads(row["ssg_config"]) if row["ssg_config"] else {},
            "gsc_config": json.loads(row["gsc_config"]) if row["gsc_config"] else None,
            "total_items": row["total_items"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "last_drip_at": row["last_drip_at"],
            "next_drip_at": row["next_drip_at"],
            "schedule_job_id": row["schedule_job_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
