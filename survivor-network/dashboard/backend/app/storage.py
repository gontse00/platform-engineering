"""
MinIO Storage Operations - Local Survivor Network
Handles avatar image upload and URL generation using local MinIO S3.
"""

import os
import io
from typing import Optional
from minio import Minio
from minio.error import S3Error

# =============================================================================
# Configuration
# =============================================================================

# Internal K8s DNS for the backend to talk to MinIO
S3_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "survivor-storage.data.svc.cluster.local:9000")
S3_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "survivor-admin")
S3_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "survivor-storage-pw")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "survivor-assets")

# External URL for the browser to fetch images
# This matches your Ingress rule in Terraform
PUBLIC_BASE_URL = os.environ.get("API_BASE_URL", "http://minio-api.127.0.0.1.nip.io")

_client: Optional[Minio] = None

def get_client() -> Minio:
    """Initialize the MinIO client."""
    global _client
    if _client is None:
        _client = Minio(
            S3_ENDPOINT,
            access_key=S3_ACCESS_KEY,
            secret_key=S3_SECRET_KEY,
            secure=False # Local cluster uses HTTP
        )
        
        # Ensure bucket exists on startup
        if not _client.bucket_exists(S3_BUCKET_NAME):
            _client.make_bucket(S3_BUCKET_NAME)
            # Set public read policy so browser can fetch avatars without tokens
            policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{S3_BUCKET_NAME}/*"]
                }]
            }
            import json
            _client.set_bucket_policy(S3_BUCKET_NAME, json.dumps(policy))
            
    return _client

async def upload_avatar_image(path: str, data: bytes, content_type: str) -> str:
    """
    Upload an image to MinIO.
    """
    client = get_client()
    
    # Wrap bytes in a stream for MinIO
    data_stream = io.BytesIO(data)
    
    client.put_object(
        S3_BUCKET_NAME,
        path,
        data_stream,
        length=len(data),
        content_type=content_type,
        metadata={"cache-control": "public, max-age=31536000"}
    )

    # Return the URL accessible via the Ingress
    return f"{PUBLIC_BASE_URL}/{S3_BUCKET_NAME}/{path}"

def get_avatar_url(path: str) -> str:
    """
    Construct the public URL for an avatar.
    """
    return f"{PUBLIC_BASE_URL}/{S3_BUCKET_NAME}/{path}"

async def delete_avatar_images(event_code: str, participant_id: str) -> None:
    """
    Delete all avatar images for a participant using a prefix search.
    """
    client = get_client()
    prefix = f"avatars/{event_code}/{participant_id}/"
    
    # List and delete
    objects_to_delete = client.list_objects(S3_BUCKET_NAME, prefix=prefix, recursive=True)
    for obj in objects_to_delete:
        client.remove_object(S3_BUCKET_NAME, obj.object_name)

async def delete_event_images(event_code: str) -> None:
    """
    Delete all images for an entire event.
    """
    client = get_client()
    prefix = f"avatars/{event_code}/"
    
    objects_to_delete = client.list_objects(S3_BUCKET_NAME, prefix=prefix, recursive=True)
    for obj in objects_to_delete:
        client.remove_object(S3_BUCKET_NAME, obj.object_name)