from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class JobCheckRequest(BaseModel):
    content_hash: str


class JobCheckResponse(BaseModel):
    exists: bool
    job: dict | None


class JobCreateRequest(BaseModel):
    content_hash: str
    source_path: str
    source_filename: str
    source_mime: str | None = None
    source_size_bytes: int | None = None
    event_id: str | None = None


class JobUpdateRequest(BaseModel):
    status: str | None = None
    minio_bucket: str | None = None
    minio_key: str | None = None
    minio_url: str | None = None
    fireflies_id: str | None = None
    fireflies_ref: str | None = None
    transcript_path: str | None = None
    csv_path: str | None = None
    error_message: str | None = None
    error_stage: str | None = None


# Statuses that indicate a retry is being attempted
RETRY_ELIGIBLE_STATUSES = {"detected", "hashing", "uploading", "transcribing"}


class JobResponse(BaseModel):
    content_hash: str
    job_id: UUID
    status: str
    source_path: str | None
    source_filename: str | None
    source_mime: str | None
    source_size_bytes: int | None
    minio_bucket: str | None
    minio_key: str | None
    minio_url: str | None
    fireflies_id: str | None
    fireflies_ref: str | None
    transcript_path: str | None
    csv_path: str | None
    event_id: UUID | None
    correlation_ids: list[str]
    error_message: str | None
    error_stage: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    pending_jobs: int
