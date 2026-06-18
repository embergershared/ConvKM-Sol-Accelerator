"""Tests for src/api/services/audio_service.py — blob check + SAS generation."""

from unittest.mock import MagicMock, patch

import pytest

from services.audio_service import get_audio_url


CONV_ID = "03b0e193-5b55-42d3-a258-b0ff9336ae18"
AUDIO_FILE = f"audio_data/convo_{CONV_ID}_2024-12-05 18_00_00.wav"


def _mock_path(name: str):
    p = MagicMock()
    p.name = name
    return p


@patch("services.audio_service.generate_file_sas", return_value="sig=abc&se=2026")
@patch("services.audio_service.get_azure_credential")
@patch("services.audio_service.DataLakeServiceClient")
@patch("services.audio_service.Config")
def test_audio_found(mock_config_cls, mock_dl_cls, mock_cred, mock_sas):
    cfg = MagicMock()
    cfg.storage_account_name = "sttest"
    cfg.azure_client_id = ""
    mock_config_cls.return_value = cfg

    mock_fs = MagicMock()
    mock_fs.get_paths.return_value = [_mock_path(AUDIO_FILE)]
    mock_dl = MagicMock()
    mock_dl.get_file_system_client.return_value = mock_fs
    mock_dl.get_user_delegation_key.return_value = MagicMock()
    mock_dl_cls.return_value = mock_dl

    result = get_audio_url(CONV_ID)

    assert result is not None
    assert result["available"] is True
    assert "blob.core.windows.net" in result["url"]
    assert result["filename"].endswith(".wav")


@patch("services.audio_service.get_azure_credential")
@patch("services.audio_service.DataLakeServiceClient")
@patch("services.audio_service.Config")
def test_audio_not_found(mock_config_cls, mock_dl_cls, mock_cred):
    cfg = MagicMock()
    cfg.storage_account_name = "sttest"
    cfg.azure_client_id = ""
    mock_config_cls.return_value = cfg

    mock_fs = MagicMock()
    mock_fs.get_paths.return_value = [
        _mock_path("custom_audiodata/convo_OTHER-ID_2024-12-05 18_00_00.wav")
    ]
    mock_dl = MagicMock()
    mock_dl.get_file_system_client.return_value = mock_fs
    mock_dl_cls.return_value = mock_dl

    result = get_audio_url(CONV_ID)
    assert result is None


@patch("services.audio_service.Config")
def test_audio_no_storage_configured(mock_config_cls):
    cfg = MagicMock()
    cfg.storage_account_name = ""
    mock_config_cls.return_value = cfg

    result = get_audio_url(CONV_ID)
    assert result is None
