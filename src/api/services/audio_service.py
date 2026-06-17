"""Audio service — check call recording availability and generate SAS URLs.

Audio recordings live in Azure Data Lake Storage Gen2 under the container
``data`` in the directory ``custom_audiodata`` with the naming convention
``convo_{conversationId}_{timestamp}.wav``.

This service:
1. Lists blobs with the matching conversation ID prefix.
2. If found, generates a short-lived (15-minute) SAS read URL using
   a user-delegation key so no storage account key is needed at runtime.
"""

import logging
from datetime import datetime, timedelta, timezone

from azure.storage.filedatalake import (
    DataLakeServiceClient,
    FileSasPermissions,
    generate_file_sas,
)

from common.config.config import Config
from helpers.azure_credential_utils import get_azure_credential

logger = logging.getLogger(__name__)

FILE_SYSTEM_NAME = "data"
AUDIO_DIRECTORIES = ["audio_data", "custom_audiodata"]
SAS_TTL_MINUTES = 15


def get_audio_url(conversation_id: str) -> dict | None:
    """Return a SAS-signed URL for the call recording, or *None* if absent.

    The response dict has the shape:
        ``{"available": True, "url": "<SAS URL>", "filename": "convo_...wav"}``

    Returns ``None`` when no matching audio file exists.  Searches both
    ``audio_data/`` (default data seeding) and ``custom_audiodata/``
    (custom data ingestion) directories.
    """
    config = Config()
    storage_account = config.storage_account_name
    if not storage_account:
        logger.warning("STORAGE_ACCOUNT_NAME not configured — audio unavailable")
        return None

    credential = get_azure_credential(client_id=config.azure_client_id or None)
    account_url = f"https://{storage_account}.dfs.core.windows.net"

    try:
        service_client = DataLakeServiceClient(
            account_url, credential=credential, api_version="2023-01-03"
        )
        fs_client = service_client.get_file_system_client(FILE_SYSTEM_NAME)

        audio_path = None
        for audio_dir in AUDIO_DIRECTORIES:
            prefix = f"{audio_dir}/convo_{conversation_id}"
            try:
                matching_paths = list(fs_client.get_paths(path=audio_dir))
            except Exception:
                logger.exception("Failed to list paths in %s", audio_dir)
                continue
            for p in matching_paths:
                if p.name.startswith(prefix) and p.name.endswith(".wav"):
                    audio_path = p.name
                    break
            if audio_path is not None:
                break

        if audio_path is None:
            return None

        # Generate a user-delegation key for SAS signing (no account key needed).
        now = datetime.now(timezone.utc)
        udk = service_client.get_user_delegation_key(
            key_start_time=now - timedelta(minutes=5),
            key_expiry_time=now + timedelta(minutes=SAS_TTL_MINUTES + 5),
        )

        # The file path relative to the file system (container).
        file_name = audio_path.split("/")[-1]
        directory_name = "/".join(audio_path.split("/")[:-1])

        sas_token = generate_file_sas(
            account_name=storage_account,
            file_system_name=FILE_SYSTEM_NAME,
            directory_name=directory_name,
            file_name=file_name,
            credential=udk,
            permission=FileSasPermissions(read=True),
            expiry=now + timedelta(minutes=SAS_TTL_MINUTES),
            start=now - timedelta(minutes=5),
        )

        # Use the *blob* endpoint for browser <audio> compatibility.
        blob_url = (
            f"https://{storage_account}.blob.core.windows.net/"
            f"{FILE_SYSTEM_NAME}/{audio_path}?{sas_token}"
        )

        return {
            "available": True,
            "url": blob_url,
            "filename": file_name,
        }

    except Exception:
        logger.exception(
            "Error checking audio for conversation %s", conversation_id
        )
        return None
