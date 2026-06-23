import os
import boto3
import uuid
from typing import Optional
from config import settings


def get_s3_client():
    """Create S3-compatible client (works with R2, Storj, MinIO, etc.)."""
    endpoint = settings.s3_endpoint
    access_key = settings.s3_access_key_id
    secret_key = settings.s3_secret_access_key
    
    if not endpoint or not access_key:
        return None
    
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=settings.s3_region,
    )


def generate_upload_url(filename: str, content_type: str = "video/mp4") -> dict:
    """
    Generate a presigned URL for direct upload to S3-compatible storage.
    Returns dict with upload_url and file_key.
    """
    client = get_s3_client()
    if not client:
        raise RuntimeError("S3 storage is not configured. Set S3 environment variables.")
    
    file_key = f"uploads/{uuid.uuid4()}/{filename}"
    
    presigned_url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket_name,
            "Key": file_key,
            "ContentType": content_type,
        },
        ExpiresIn=3600,  # 1 hour
    )
    
    return {
        "upload_url": presigned_url,
        "file_key": file_key,
    }


def get_download_url(file_key: str) -> str:
    """Get a presigned download URL for a file."""
    client = get_s3_client()
    if not client:
        # Fallback to public URL
        return f"{settings.s3_public_url}/{file_key}"
    
    try:
        presigned_url = client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.s3_bucket_name,
                "Key": file_key,
            },
            ExpiresIn=7200,  # 2 hours
        )
        return presigned_url
    except Exception:
        # Fallback to public URL
        return f"{settings.s3_public_url}/{file_key}"


def download_from_s3(file_key: str, local_path: str) -> str:
    """Download a file from S3-compatible storage to local storage."""
    client = get_s3_client()
    if not client:
        raise RuntimeError("S3 storage is not configured.")
    
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    client.download_file(
        settings.s3_bucket_name,
        file_key,
        local_path,
    )
    
    return local_path


def delete_from_s3(file_key: str) -> bool:
    """Delete a file from S3-compatible storage."""
    client = get_s3_client()
    if not client:
        return False
    
    try:
        client.delete_object(
            Bucket=settings.s3_bucket_name,
            Key=file_key,
        )
        return True
    except Exception:
        return False
