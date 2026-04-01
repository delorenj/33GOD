from fastapi import APIRouter, HTTPException

from .db import get_pool
from .models import (
    RETRY_ELIGIBLE_STATUSES,
    HealthResponse,
    JobCheckRequest,
    JobCheckResponse,
    JobCreateRequest,
    JobResponse,
    JobUpdateRequest,
)

router = APIRouter()


def _row_to_dict(row) -> dict:
    return dict(row)


@router.post("/jobs/check", response_model=JobCheckResponse)
async def check_job(req: JobCheckRequest) -> JobCheckResponse:
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM echobox_ledger WHERE content_hash = $1",
        req.content_hash,
    )
    if row is None:
        return JobCheckResponse(exists=False, job=None)
    return JobCheckResponse(exists=True, job=_row_to_dict(row))


@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(req: JobCreateRequest) -> JobResponse:
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO echobox_ledger (
            content_hash, source_path, source_filename,
            source_mime, source_size_bytes, event_id
        )
        VALUES ($1, $2, $3, $4, $5, $6::uuid)
        RETURNING *
        """,
        req.content_hash,
        req.source_path,
        req.source_filename,
        req.source_mime,
        req.source_size_bytes,
        req.event_id,
    )
    if row is None:
        raise HTTPException(status_code=500, detail="Insert returned no row")
    return JobResponse(**_row_to_dict(row))


@router.patch("/jobs/{content_hash}", response_model=JobResponse)
async def update_job(content_hash: str, req: JobUpdateRequest) -> JobResponse:
    pool = get_pool()

    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields provided to update")

    # Increment retry_count when the caller is cycling the job back into an
    # active state — this signals a deliberate retry rather than a forward
    # progression through the normal lifecycle.
    increment_retry = (
        "status" in updates and updates["status"] in RETRY_ELIGIBLE_STATUSES
    )

    fields = list(updates.keys())
    values = list(updates.values())

    set_clauses = [f"{f} = ${i + 1}" for i, f in enumerate(fields)]
    if increment_retry:
        set_clauses.append("retry_count = retry_count + 1")

    param_idx = len(values) + 1
    query = (
        f"UPDATE echobox_ledger SET {', '.join(set_clauses)} "
        f"WHERE content_hash = ${param_idx} "
        f"RETURNING *"
    )

    row = await pool.fetchrow(query, *values, content_hash)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(**_row_to_dict(row))


@router.get("/jobs", response_model=list[JobResponse])
async def get_all_jobs() -> list[JobResponse]:
    pool = get_pool()
    rows = await pool.fetch(
        "SELECT * FROM echobox_ledger ORDER BY created_at DESC LIMIT 200"
    )
    return [JobResponse(**_row_to_dict(r)) for r in rows]


@router.get("/jobs/pending", response_model=list[JobResponse])
async def get_pending_jobs() -> list[JobResponse]:
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT * FROM echobox_ledger
        WHERE status NOT IN ('completed', 'failed', 'skipped')
        ORDER BY created_at ASC
        """
    )
    return [JobResponse(**_row_to_dict(r)) for r in rows]


@router.get("/jobs/by-ref/{fireflies_ref}", response_model=JobResponse)
async def get_job_by_ref(fireflies_ref: str) -> JobResponse:
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM echobox_ledger WHERE fireflies_ref = $1",
        fireflies_ref,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(**_row_to_dict(row))


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    pool = get_pool()
    try:
        await pool.fetchval("SELECT 1")
        db_connected = True
    except Exception:
        db_connected = False

    pending = 0
    if db_connected:
        pending = await pool.fetchval(
            """
            SELECT COUNT(*) FROM echobox_ledger
            WHERE status NOT IN ('completed', 'failed', 'skipped')
            """
        )

    return HealthResponse(
        status="ok" if db_connected else "degraded",
        db_connected=db_connected,
        pending_jobs=pending,
    )
