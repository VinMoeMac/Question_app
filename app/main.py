"""FastAPI entrypoint for the FineWeb Question Explorer."""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import Settings, get_settings
from .data_access import DatasetGateway

settings: Settings = get_settings()
gateway = DatasetGateway(settings.csv_path)

app = FastAPI(title=settings.app_title)

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(FileNotFoundError)
async def missing_file_handler(_: Request, exc: FileNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "settings": settings})


@app.get("/api/metadata")
async def metadata():
    payload = gateway.get_metadata()
    payload.update(
        {
            "default_page_size": settings.default_page_size,
            "max_page_size": settings.max_page_size,
            "csv_display_name": settings.csv_display_name,
        }
    )
    return payload


@app.get("/api/rows")
async def rows(
    *,
    page: int = Query(1, ge=1),
    page_size: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, min_length=1, max_length=200),
    sort_by: Optional[str] = Query(None),
    sort_dir: str = Query("asc"),
):
    effective_page_size = page_size or settings.default_page_size
    if effective_page_size > settings.max_page_size:
        raise HTTPException(
            status_code=400,
            detail=f"page_size cannot exceed {settings.max_page_size}",
        )

    offset = (page - 1) * effective_page_size

    try:
        result = gateway.get_rows(
            offset=offset,
            limit=effective_page_size,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except ValueError as exc:  # invalid arguments bubble up as 400s
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result.update({"page": page, "page_size": effective_page_size})
    return result


@app.post("/api/refresh")
async def refresh():
    gateway.refresh()
    return {"status": "ok", "row_count": gateway.get_row_count()}
