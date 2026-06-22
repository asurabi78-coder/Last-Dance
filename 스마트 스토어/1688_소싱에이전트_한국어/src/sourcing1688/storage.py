from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from sourcing1688.models import ProductDetail, ProductSearchResult, SourcingScore
from sourcing1688.reports.csv_export import shortlist_to_csv
from sourcing1688.reports.markdown import shortlist_to_markdown


class SourcingStorage:
    def __init__(self, db_path: str | Path = "data/sourcing1688.duckdb") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS search_results (
                project VARCHAR,
                keyword VARCHAR,
                offer_id VARCHAR,
                provider VARCHAR,
                live_verified BOOLEAN,
                source_keyword VARCHAR,
                payload JSON,
                created_at TIMESTAMP DEFAULT now()
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS product_details (
                offer_id VARCHAR PRIMARY KEY,
                provider VARCHAR,
                live_verified BOOLEAN,
                raw_html_path VARCHAR,
                payload JSON,
                updated_at TIMESTAMP DEFAULT now()
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sourcing_scores (
                offer_id VARCHAR PRIMARY KEY,
                payload JSON,
                updated_at TIMESTAMP DEFAULT now()
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shortlist (
                project VARCHAR,
                offer_id VARCHAR,
                notes VARCHAR,
                created_at TIMESTAMP DEFAULT now(),
                PRIMARY KEY(project, offer_id)
            )
            """
        )
        self._ensure_column("search_results", "provider", "VARCHAR")
        self._ensure_column("search_results", "live_verified", "BOOLEAN")
        self._ensure_column("search_results", "source_keyword", "VARCHAR")
        self._ensure_column("product_details", "provider", "VARCHAR")
        self._ensure_column("product_details", "live_verified", "BOOLEAN")
        self._ensure_column("product_details", "raw_html_path", "VARCHAR")

    def _ensure_column(self, table: str, column: str, type_name: str) -> None:
        columns = {row[1] for row in self.conn.execute(f"PRAGMA table_info('{table}')").fetchall()}
        if column not in columns:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {type_name}")

    def save_search_results(self, project: str, keyword: str, results: list[ProductSearchResult]) -> None:
        for result in results:
            self.conn.execute(
                "INSERT INTO search_results(project, keyword, offer_id, provider, live_verified, source_keyword, payload) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [project, keyword, result.offer_id, result.provider, result.live_verified, result.source_keyword, result.model_dump_json()],
            )

    def save_product_detail(self, detail: ProductDetail) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO product_details(offer_id, provider, live_verified, raw_html_path, payload, updated_at)
            VALUES (?, ?, ?, ?, ?, now())
            """,
            [detail.offer_id, detail.provider, detail.live_verified, detail.raw_reference_path, detail.model_dump_json()],
        )

    def save_sourcing_score(self, score: SourcingScore) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO sourcing_scores(offer_id, payload, updated_at)
            VALUES (?, ?, now())
            """,
            [score.offer_id, score.model_dump_json()],
        )

    def add_to_shortlist(self, project: str, offer_id: str, notes: str | None = None) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO shortlist(project, offer_id, notes, created_at)
            VALUES (?, ?, ?, now())
            """,
            [project, offer_id, notes],
        )

    def list_shortlist(self, project: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT
                s.project,
                s.offer_id,
                s.notes,
                sr.payload,
                sc.payload AS score_payload
            FROM shortlist s
            LEFT JOIN (
                SELECT offer_id, any_value(payload) AS payload
                FROM search_results
                GROUP BY offer_id
            ) sr ON s.offer_id = sr.offer_id
            LEFT JOIN sourcing_scores sc ON s.offer_id = sc.offer_id
            WHERE s.project = ?
            ORDER BY s.created_at DESC
            """,
            [project],
        ).fetchall()
        items: list[dict[str, Any]] = []
        for project_name, offer_id, notes, payload, score_payload in rows:
            item: dict[str, Any] = {"project": project_name, "offer_id": offer_id, "notes": notes}
            if payload:
                item.update(json.loads(payload))
            if score_payload:
                item["score"] = json.loads(score_payload)
            items.append(item)
        return items

    def export_project(self, project: str, format: str) -> dict[str, Any]:
        items = self.list_shortlist(project)
        normalized = format.lower()
        if normalized == "json":
            return {"status": "ok", "project": project, "format": "json", "items": items}
        if normalized == "markdown":
            return {"status": "ok", "project": project, "format": "markdown", "content": shortlist_to_markdown(project, items)}
        if normalized == "csv":
            return {"status": "ok", "project": project, "format": "csv", "content": shortlist_to_csv(items)}
        return {
            "status": "error",
            "project": project,
            "format": normalized,
            "message": "Unsupported export format. Use markdown, csv, or json.",
        }

    def close(self) -> None:
        self.conn.close()
