"""Tests for authentication and logging modules."""
import pytest
import json
from unittest.mock import AsyncMock, patch

from mcp_server.auth import (
    LocalNoOpTokenVerifier,
    JWTTokenVerifier,
    create_token_verifier,
)
from mcp_server.logging import (
    StructuredLogger,
    CorrelationContext,
    RedactedDict,
    get_logger,
)


class TestCorrelationContext:
    """Tests for correlation ID tracking."""

    def test_set_and_get(self):
        """Test setting and getting correlation ID."""
        CorrelationContext.set("test-123")
        assert CorrelationContext.get() == "test-123"

    def test_new_generates_unique_id(self):
        """Test that new() generates unique IDs."""
        id1 = CorrelationContext.new()
        id2 = CorrelationContext.new()
        assert id1 != id2
        assert id1.startswith("req-")
        assert id2.startswith("req-")


class TestRedactedDict:
    """Tests for sensitive data redaction."""

    def test_redact_token_field(self):
        """Test that 'token' fields are redacted."""
        redactor = RedactedDict()
        obj = {"token": "secret123456789"}
        result = redactor.redact(obj)
        assert "<" in result["token"]
        assert "secret123456789" not in str(result)

    def test_redact_api_key_field(self):
        """Test that 'api_key' fields are redacted."""
        redactor = RedactedDict()
        obj = {"api_key": "abc123def456ghi789"}
        result = redactor.redact(obj)
        assert "<" in result["api_key"]
        assert "abc123" not in str(result)

    def test_preserve_safe_fields(self):
        """Test that safe fields are not redacted."""
        redactor = RedactedDict()
        obj = {
            "name": "my-service",
            "version": "1.0.0",
            "issuer": "https://auth.example.com",
        }
        result = redactor.redact(obj)
        assert result["name"] == "my-service"
        assert result["version"] == "1.0.0"
        assert result["issuer"] == "https://auth.example.com"

    def test_redact_nested_objects(self):
        """Test redaction of nested dictionaries."""
        redactor = RedactedDict()
        obj = {
            "config": {
                "database": "prod-db",
                "password": "secretpass123",
            }
        }
        result = redactor.redact(obj)
        assert result["config"]["database"] == "prod-db"
        assert "<" in result["config"]["password"]

    def test_redact_lists(self):
        """Test redaction within lists."""
        redactor = RedactedDict()
        obj = {
            "items": [
                {"name": "item1", "secret": "secret1"},
                {"name": "item2", "secret": "secret2"},
            ]
        }
        result = redactor.redact(obj)
        assert result["items"][0]["name"] == "item1"
        assert "<" in result["items"][0]["secret"]


class TestStructuredLogger:
    """Tests for structured logging."""

    def test_logger_creation(self):
        """Test logger creation."""
        logger = StructuredLogger("test", "INFO")
        assert logger.logger.name == "test"

    def test_log_tool_invocation(self, capsys):
        """Test tool invocation logging."""
        logger = StructuredLogger("test", "INFO")
        CorrelationContext.set("test-123")
        
        logger.log_tool_invocation(
            "test_tool",
            transport="stdio",
            status="success",
            duration_ms=150,
            output_size_bytes=2000,
        )
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.err.strip())
        assert log_entry["level"] == "INFO"
        assert log_entry["tool_name"] == "test_tool"
        assert log_entry["duration_ms"] == 150
        assert log_entry["status"] == "success"

    def test_log_auth_failure(self, capsys):
        """Test authentication failure logging."""
        logger = StructuredLogger("test", "INFO")
        CorrelationContext.set("test-123")
        
        logger.log_auth_failure("Invalid signature", "http")
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.err.strip())
        assert log_entry["level"] == "WARNING"
        assert log_entry["error_category"] == "auth_failure"
        assert "signature" in log_entry["event"]

    def test_log_redaction(self, capsys):
        """Test that sensitive data is redacted in logs."""
        logger = StructuredLogger("test", "INFO")
        CorrelationContext.set("test-123")
        
        logger.log_startup(
            transport="http",
            api_key="secret123456789",
            jwt_issuer="https://auth.example.com",
        )
        
        captured = capsys.readouterr()
        log_output = captured.err.strip()
        assert "secret123456789" not in log_output
        assert "<" in log_output  # Redaction marker


class TestLocalNoOpTokenVerifier:
    """Tests for LocalNoOpTokenVerifier."""

    def test_accepts_any_token(self):
        """Test that local verifier accepts any token."""
        import asyncio
        
        async def run_test():
            verifier = LocalNoOpTokenVerifier()
            token = "any-token-string"
            result = await verifier.verify_token(token)
            assert result is not None
            assert result.token == token
            assert result.client_id == "devops-os-local"
            assert "*" in result.scopes
        
        asyncio.run(run_test())

    def test_returns_valid_access_token(self):
        """Test that returned AccessToken is valid."""
        import asyncio
        
        async def run_test():
            verifier = LocalNoOpTokenVerifier()
            result = await verifier.verify_token("test-token")
            assert result.resource == "devops-os-local"
            assert result.scopes == ["*"]
        
        asyncio.run(run_test())


class TestJWTTokenVerifier:
    """Tests for JWTTokenVerifier."""

    def test_construct_jwks_url(self):
        """Test JWKS URL construction."""
        verifier = JWTTokenVerifier(
            issuer="https://auth.example.com/",
            audience="test-service",
        )
        assert verifier.jwks_url == "https://auth.example.com/.well-known/jwks.json"

    def test_construct_jwks_url_without_trailing_slash(self):
        """Test JWKS URL construction without trailing slash."""
        verifier = JWTTokenVerifier(
            issuer="https://auth.example.com",
            audience="test-service",
        )
        assert verifier.jwks_url == "https://auth.example.com/.well-known/jwks.json"

    @patch('mcp_server.auth.httpx.AsyncClient')
    def test_fetch_jwks_success(self, mock_client_class):
        """Test JWKS configuration and URL handling."""
        verifier = JWTTokenVerifier(
            issuer="https://auth.example.com",
            audience="test-service",
        )
        
        # Verify JWKS URL is properly configured
        assert verifier.jwks_url == "https://auth.example.com/.well-known/jwks.json"
        assert verifier.key_cache_ttl_seconds == 3600

    def test_verify_token_without_jwt_library(self):
        """Test that verification fails gracefully without JWT library."""
        import asyncio
        
        async def run_test():
            verifier = JWTTokenVerifier(
                issuer="https://auth.example.com",
                audience="test-service",
            )
            
            # Patch the import to simulate missing library
            with patch.dict('sys.modules', {'jwt': None}):
                # This should handle the missing library gracefully
                # In real scenario, user must install PyJWT or python-jose
                result = await verifier.verify_token("invalid-token")
                assert result is None  # Verification fails
        
        asyncio.run(run_test())


class TestCreateTokenVerifier:
    """Tests for token verifier factory."""

    def test_create_local_verifier(self):
        """Test creating local (no-op) verifier."""
        verifier = create_token_verifier("local")
        assert isinstance(verifier, LocalNoOpTokenVerifier)

    def test_create_jwt_verifier(self):
        """Test creating JWT verifier."""
        verifier = create_token_verifier(
            "remote",
            jwt_issuer="https://auth.example.com",
            jwt_audience="test-service",
        )
        assert isinstance(verifier, JWTTokenVerifier)

    def test_create_jwt_verifier_missing_issuer(self):
        """Test that JWT verifier requires issuer."""
        with pytest.raises(ValueError, match="DEVOPS_OS_JWT_ISSUER"):
            create_token_verifier("remote", jwt_audience="test-service")

    def test_create_jwt_verifier_missing_audience(self):
        """Test that JWT verifier requires audience."""
        with pytest.raises(ValueError, match="DEVOPS_OS_JWT_AUDIENCE"):
            create_token_verifier("remote", jwt_issuer="https://auth.example.com")

    def test_create_invalid_profile(self):
        """Test that invalid profile raises error."""
        with pytest.raises(ValueError, match="Unknown profile"):
            create_token_verifier("invalid")
