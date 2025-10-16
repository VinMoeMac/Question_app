# FineWeb Question Explorer

A FastAPI + DuckDB powered web interface for showcasing large question datasets
(10M+ rows) generated from the FineWeb corpus using the two stage extraction and
recommendation filtering scripts.

## Features

- **Stream-from-disk queries:** DuckDB reads the CSV lazily so you can explore
  datasets with tens of millions of rows without a preprocessing step.
- **Server-side pagination & filtering:** keyword search with case-insensitive
  `ILIKE`, configurable sorting, and next/previous paging optimised for huge
  files.
- **Pipeline context built in:** the landing page highlights the Stage 1 and
  Stage 2 scripts used to create the dataset so you can tell the story while you
  demo it.
- **One-command launch:** run a single `uvicorn` command and share the resulting
  dashboard.

## Quick start

1. Install dependencies (Python 3.10+ recommended):

   ```bash
   pip install -r requirements.txt
   ```

2. Point the app at your CSV (defaults to `data/sample_questions.csv` for a
   tiny demo dataset):

   ```bash
   export CSV_PATH=/path/to/filtered_all_dumps.csv
   ```

3. Launch the web server:

   ```bash
   uvicorn app.main:app --reload
   ```

4. Open <http://127.0.0.1:8000> in your browser.

The toolbar lets you change the page size (capped by `MAX_PAGE_SIZE`, default
500), adjust ordering, and run keyword searches across the `question` column.
Hit **Refresh CSV** if you overwrite the file and want DuckDB to re-read it
without restarting the server.

## Environment variables

| Variable             | Description                                           | Default                     |
| -------------------- | ----------------------------------------------------- | --------------------------- |
| `CSV_PATH`           | Absolute or relative path to the CSV to showcase.     | `data/sample_questions.csv` |
| `DEFAULT_PAGE_SIZE`  | Initial page size shown in the UI.                    | `100`                       |
| `MAX_PAGE_SIZE`      | Upper limit for selectable page sizes.                | `500`                       |

Invalid integer values for the page size variables raise an error at startup,
helping you catch misconfiguration early.

## Dataset creation pipeline (recap)

Stage 1 (`stage1_extract_from_parquet.py`) streams FineWeb parquet shards either
from Google Cloud Storage or local disk, extracts question-like sentences with a
permissive heuristic, and writes the output incrementally to CSV with
checkpoints/resume support. Stage 2 (`stage2_filter_no_scores_parallel_local.py`)
then works on local CSV batches using multiprocessing to keep disk IO hot,
filters for recommendation intent + context independence, enriches rows with
industry tags, and finally merges the surviving questions into your showcase CSV.

This UI simply connects to the Stage 2 output—no ETL or schema changes required.

## Development tips

- The `DatasetGateway` in `app/data_access.py` encapsulates all DuckDB access.
  Extend it if you want aggregations or additional filters.
- Static assets live in `app/static/`. If you change the JS or CSS during local
  development, reload the page; no bundler is required.
- For production deployment consider running `uvicorn` behind a process manager
  such as `gunicorn` or deploying via Cloud Run.
