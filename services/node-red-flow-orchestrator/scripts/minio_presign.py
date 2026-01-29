#!/usr/bin/env python3
import json
import mimetypes
import os
import sys
from pathlib import Path

import boto3
from botocore.config import Config


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: minio_presign.py <file_path> [object_key]", file=sys.stderr)
        return 2

    file_path = Path(sys.argv[1]).expanduser().resolve()
    if not file_path.exists():
        print(f"File not found: {file_path}", file=sys.stderr)
        return 2

    object_key = sys.argv[2] if len(sys.argv) > 2 else file_path.name

    endpoint = os.environ.get("MINIO_ENDPOINT", "https://s3.delo.sh")
    bucket = os.environ.get("MINIO_BUCKET", "transcription-staging")
    access_key = os.environ.get("MINIO_ACCESS_KEY")
    secret_key = os.environ.get("MINIO_SECRET_KEY")
    region = os.environ.get("MINIO_REGION", "us-east-1")
    expires = int(os.environ.get("MINIO_PRESIGN_EXPIRES", "3600"))
    force_path = os.environ.get("MINIO_FORCE_PATH_STYLE", "true").lower() in ("1", "true", "yes")

    if not access_key or not secret_key:
        print("Missing MINIO_ACCESS_KEY or MINIO_SECRET_KEY", file=sys.stderr)
        return 2

    config = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path" if force_path else "virtual"},
    )

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=config,
    )

    content_type, _ = mimetypes.guess_type(str(file_path))
    extra_args = {"ContentType": content_type} if content_type else None

    if extra_args:
        s3.upload_file(str(file_path), bucket, object_key, ExtraArgs=extra_args)
    else:
        s3.upload_file(str(file_path), bucket, object_key)

    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": object_key},
        ExpiresIn=expires,
    )

    payload = {
        "bucket": bucket,
        "key": object_key,
        "url": presigned_url,
        "content_type": content_type or "application/octet-stream",
    }
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
