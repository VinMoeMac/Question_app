"""Data access helpers built on top of DuckDB."""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

import duckdb


class DatasetGateway:
    """Expose metadata and row retrieval for a large CSV file."""

    def __init__(self, csv_path: Path):
        self.csv_path = csv_path
        self._lock = Lock()
        self._conn = duckdb.connect(database=":memory:")
        self._conn.execute("SET GLOBAL memory_limit='8GB'")
        self._register_view()
        self._columns = self._fetch_columns()
        self._row_count: Optional[int] = None
        self._default_sort = self._determine_default_sort()
        self._searchable_column = self._find_searchable_column()

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------
    def _register_view(self) -> None:
        """Register the CSV as a de-duplicated in-memory DuckDB table."""

        with self._lock:
            # DuckDB doesn't like prepared statements for read_csv_auto
            # so we'll escape the path and embed it directly.
            escaped_csv_path = str(self.csv_path).replace("'", "''")

            # The QUALIFY clause partitions by question and takes the first row for each,
            # effectively de-duplicating the dataset based on the question text.
            # By creating a TABLE instead of a VIEW, we materialize the de-duplicated
            # results once at startup for much better query performance.
            dedupe_query = f"""
                CREATE OR REPLACE TABLE dataset AS
                SELECT *
                FROM read_csv_auto('{escaped_csv_path}', HEADER=TRUE, SAMPLE_SIZE=100000)
                QUALIFY ROW_NUMBER() OVER (PARTITION BY question) = 1
            """
            self._conn.execute(dedupe_query)

    def _fetch_columns(self) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("DESCRIBE dataset").fetchall()

        columns: List[Dict[str, Any]] = []
        for row in rows:
            column_name, column_type = row[0], row[1]
            columns.append({"name": column_name, "type": column_type})
        return columns

    def _determine_default_sort(self) -> str:
        preferred = ["question_id", "doc_id", "question"]
        column_names = [col["name"] for col in self._columns]
        for candidate in preferred:
            if candidate in column_names:
                return candidate
        return column_names[0]

    def _find_searchable_column(self) -> Optional[str]:
        column_names = [col["name"].lower() for col in self._columns]
        if "question" in column_names:
            idx = column_names.index("question")
            return self._columns[idx]["name"]
        return None

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "row_count": self.get_row_count(),
            "columns": self._columns,
            "csv_path": str(self.csv_path),
            "default_sort": self._default_sort,
            "searchable_column": self._searchable_column,
        }

    def get_row_count(self) -> int:
        if self._row_count is None:
            with self._lock:
                self._row_count = self._conn.execute("SELECT COUNT(*) FROM dataset").fetchone()[0]
        return self._row_count

    def refresh(self) -> None:
        """Reload the DuckDB table if the CSV has changed."""

        self._row_count = None
        self._register_view()
        self._columns = self._fetch_columns()
        self._default_sort = self._determine_default_sort()
        self._searchable_column = self._find_searchable_column()

    def get_rows(
        self,
        *,
        offset: int,
        limit: int,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_dir: str = "asc",
    ) -> Dict[str, Any]:
        if offset < 0:
            raise ValueError("offset must be >= 0")
        if limit < 1:
            raise ValueError("limit must be >= 1")

        column_names = {col["name"] for col in self._columns}

        if sort_by is None or sort_by not in column_names:
            sort_column = self._default_sort
        else:
            sort_column = sort_by

        sort_direction = sort_dir.lower()
        if sort_direction not in {"asc", "desc"}:
            sort_direction = "asc"

        params: List[Any] = []
        where_clause = ""

        if search:
            if not self._searchable_column:
                raise ValueError("Search is not available because the CSV does not expose a 'question' column.")
            # Use double quotes to escape column names, as duckdb.escape_identifier is not available
            where_clause = f'WHERE "{self._searchable_column}" ILIKE ?'
            params.append(f"%{search}%")

        # Use double quotes to escape column names, as duckdb.escape_identifier is not available
        order_clause = f'ORDER BY "{sort_column}" {sort_direction.upper()}'
        limit_clause = "LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        query = " ".join(part for part in ["SELECT * FROM dataset", where_clause, order_clause, limit_clause] if part)

        with self._lock:
            relation = self._conn.execute(query, params)
            rows = relation.fetchall()
            description = relation.description or []

        column_headers = [col[0] for col in description]
        records = [dict(zip(column_headers, row)) for row in rows]

        if search:
            # Use double quotes to escape column names here as well
            where_clause_for_count = f'WHERE "{self._searchable_column}" ILIKE ?'
            count_query = f"SELECT COUNT(*) FROM dataset {where_clause_for_count}".strip()
            count_params = params[: len(params) - 2]  # remove limit & offset
            with self._lock:
                filtered_total = self._conn.execute(count_query, count_params).fetchone()[0]
        else:
            filtered_total = self.get_row_count()

        return {
            "rows": records,
            "total_rows": self.get_row_count(),
            "total_filtered": filtered_total,
            "offset": offset,
            "limit": limit,
            "sort_by": sort_column,
            "sort_dir": sort_direction,
            "search": search or "",
        }


__all__ = ["DatasetGateway"]
