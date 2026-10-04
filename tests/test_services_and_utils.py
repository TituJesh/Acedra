import io
import json
from unittest.mock import MagicMock, patch

import pytest
from jose import jwt

from app.services.s3_service import (
    delete_file_from_s3,
    generate_download_url,
    upload_file_to_s3,
)
from app.utils.jwt import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_secret_key,
)
from app.utils.security import hash_password, verify_password


# ==============================================================================
# S3 Service Unit Tests
# ==============================================================================

def test_s3_upload_file_with_content_type():
    """Verify upload_file_to_s3 passes content-type in ExtraArgs."""
    mock_file = io.BytesIO(b"sample file content")
    with patch("app.services.s3_service.s3_client") as mock_client:
        upload_file_to_s3(
            file_object=mock_file,
            s3_key="students/1/sample.pdf",
            content_type="application/pdf"
        )
        mock_client.upload_fileobj.assert_called_once_with(
            mock_file,
            "test-acedra-documents-bucket",
            "students/1/sample.pdf",
            ExtraArgs={"ContentType": "application/pdf"}
        )


def test_s3_upload_file_without_content_type():
    """Verify upload_file_to_s3 works without content-type."""
    mock_file = io.BytesIO(b"raw binary data")
    with patch("app.services.s3_service.s3_client") as mock_client:
        upload_file_to_s3(
            file_object=mock_file,
            s3_key="students/1/raw.bin",
            content_type=None
        )
        mock_client.upload_fileobj.assert_called_once_with(
            mock_file,
            "test-acedra-documents-bucket",
            "students/1/raw.bin",
            ExtraArgs={}
        )


def test_s3_delete_file():
    """Verify delete_file_from_s3 calls delete_object with correct bucket and key."""
    with patch("app.services.s3_service.s3_client") as mock_client:
        delete_file_from_s3("students/1/to_delete.pdf")
        mock_client.delete_object.assert_called_once_with(
            Bucket="test-acedra-documents-bucket",
            Key="students/1/to_delete.pdf"
        )


def test_s3_generate_download_url_defaults():
    """Verify generate_download_url uses default 300s expiration."""
    with patch("app.services.s3_service.s3_client") as mock_client:
        mock_client.generate_presigned_url.return_value = "https://s3.example.com/presigned-url"
        url = generate_download_url("students/1/test.pdf")
        assert url == "https://s3.example.com/presigned-url"
        mock_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-acedra-documents-bucket", "Key": "students/1/test.pdf"},
            ExpiresIn=300
        )


def test_s3_generate_download_url_custom_expiration():
    """Verify generate_download_url respects custom expiration parameter."""
    with patch("app.services.s3_service.s3_client") as mock_client:
        mock_client.generate_presigned_url.return_value = "https://s3.example.com/custom-url"
        url = generate_download_url("students/1/test.pdf", expiration=600)
        assert url == "https://s3.example.com/custom-url"
        mock_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-acedra-documents-bucket", "Key": "students/1/test.pdf"},
            ExpiresIn=600
        )


# ==============================================================================
# Security Utilities Unit Tests
# ==============================================================================

def test_hash_and_verify_password():
    """Verify password hashing produces verifiable and distinct hashes."""
    raw_password = "SecureTestPassword456!"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword789!", hashed) is False


# ==============================================================================
# JWT Utilities Unit Tests
# ==============================================================================

def test_create_access_token_payload_and_expiry():
    """Verify access token payload, signature, and expiration claim."""
    payload = {"user_id": 42, "role": "admin"}
    token = create_access_token(payload)

    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["user_id"] == 42
    assert decoded["role"] == "admin"
    assert "exp" in decoded


def test_get_secret_key_production():
    """Verify get_secret_key retrieves key from AWS Secrets Manager in production."""
    with patch("app.utils.jwt.ENVIRONMENT", "production"), \
         patch("boto3.client") as mock_boto:
        mock_secrets_client = MagicMock()
        mock_secrets_client.get_secret_value.return_value = {
            "SecretString": json.dumps({"SECRET_KEY": "production-secret-from-aws-secretsmanager-32b"})
        }
        mock_boto.return_value = mock_secrets_client

        key = get_secret_key()
        assert key == "production-secret-from-aws-secretsmanager-32b"
        mock_secrets_client.get_secret_value.assert_called_once_with(SecretId="acedra/jwt")


def test_get_secret_key_non_production(monkeypatch):
    """Verify get_secret_key falls back to SECRET_KEY environment variable."""
    with patch("app.utils.jwt.ENVIRONMENT", "development"):
        monkeypatch.setenv("SECRET_KEY", "custom-development-secret-key-32-chars")
        key = get_secret_key()
        assert key == "custom-development-secret-key-32-chars"
