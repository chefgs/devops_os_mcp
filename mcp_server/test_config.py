"""Tests for MCP server configuration and validation."""
import os
import pytest
from mcp_server.config import Config
from mcp_server.validators import (
    ValidationError,
    validate_k8s_identifier,
    validate_image_reference,
    validate_port,
    validate_positive_int,
    validate_replica_count,
    validate_choice,
    validate_float_range,
    validate_slo_target,
    validate_string_length,
    validate_languages,
    validate_tool_inputs,
)


class TestConfig:
    """Tests for configuration loading."""

    def test_config_default_values(self):
        """Test that default values are correct."""
        config = Config()
        assert config.transport == "stdio"
        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.mcp_endpoint == "/mcp"
        assert config.request_size_mb == 10
        assert config.response_size_mb == 50
        assert config.execution_timeout == 30
        assert config.log_level == "INFO"
        assert config.profile == "local"

    def test_config_from_env(self, monkeypatch):
        """Test loading config from environment variables."""
        monkeypatch.setenv("DEVOPS_OS_TRANSPORT", "streamable-http")
        monkeypatch.setenv("DEVOPS_OS_PORT", "9000")
        monkeypatch.setenv("DEVOPS_OS_LOG_LEVEL", "debug")
        
        config = Config.from_env()
        assert config.transport == "streamable-http"
        assert config.port == 9000
        assert config.log_level == "DEBUG"  # Converted to uppercase

    def test_config_invalid_transport_from_env(self, monkeypatch):
        """Test that invalid transport is rejected by from_env."""
        monkeypatch.setenv("DEVOPS_OS_TRANSPORT", "invalid")
        
        with pytest.raises(ValueError, match="must be"):
            Config.from_env()

    def test_config_invalid_port(self):
        """Test that invalid port is rejected."""
        with pytest.raises(ValueError, match="Port must be"):
            Config(port=0)
        with pytest.raises(ValueError, match="Port must be"):
            Config(port=99999)

    def test_config_remote_profile_requires_auth(self):
        """Test that remote profile requires JWT configuration."""
        with pytest.raises(ValueError, match="DEVOPS_OS_JWT_ISSUER"):
            Config(profile="remote")
        
        with pytest.raises(ValueError, match="DEVOPS_OS_JWT_AUDIENCE"):
            Config(profile="remote", jwt_issuer="https://issuer.example.com")

    def test_config_size_limits(self):
        """Test size limit validation."""
        with pytest.raises(ValueError, match="REQUEST_SIZE_MB"):
            Config(request_size_mb=0)
        with pytest.raises(ValueError, match="REQUEST_SIZE_MB"):
            Config(request_size_mb=2000)


class TestValidators:
    """Tests for input validators."""

    def test_validate_k8s_identifier_valid(self):
        """Test valid Kubernetes identifiers."""
        assert validate_k8s_identifier("my-app", "app_name") == "my-app"
        assert validate_k8s_identifier("app123", "app_name") == "app123"
        assert validate_k8s_identifier("a", "app_name") == "a"
        assert validate_k8s_identifier("a" * 63, "app_name") == "a" * 63

    def test_validate_k8s_identifier_invalid(self):
        """Test invalid Kubernetes identifiers."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_k8s_identifier("", "app_name")
        
        with pytest.raises(ValidationError, match="must be 1-63"):
            validate_k8s_identifier("a" * 64, "app_name")
        
        with pytest.raises(ValidationError, match="lowercase alphanumeric"):
            validate_k8s_identifier("My-App", "app_name")
        
        with pytest.raises(ValidationError, match="lowercase alphanumeric"):
            validate_k8s_identifier("-app", "app_name")
        
        with pytest.raises(ValidationError, match="lowercase alphanumeric"):
            validate_k8s_identifier("app-", "app_name")

    def test_validate_image_reference_valid(self):
        """Test valid image references."""
        assert validate_image_reference("python") == "python"
        assert validate_image_reference("python:3.12") == "python:3.12"
        assert validate_image_reference("ghcr.io/org/app:v1.0.0") == "ghcr.io/org/app:v1.0.0"
        assert validate_image_reference("registry.example.com/app@sha256:abc123") == "registry.example.com/app@sha256:abc123"

    def test_validate_image_reference_invalid(self):
        """Test invalid image references."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_image_reference("")
        
        with pytest.raises(ValidationError, match="invalid character"):
            validate_image_reference("python$(malicious)")
        
        with pytest.raises(ValidationError, match="invalid character"):
            validate_image_reference("python;rm -rf /")

    def test_validate_port_valid(self):
        """Test valid port numbers."""
        assert validate_port(8080) == 8080
        assert validate_port("8080") == 8080
        assert validate_port(1) == 1
        assert validate_port(65535) == 65535

    def test_validate_port_invalid(self):
        """Test invalid port numbers."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_port("not-a-number")
        
        with pytest.raises(ValidationError, match="must be 1-65535"):
            validate_port(0)
        
        with pytest.raises(ValidationError, match="must be 1-65535"):
            validate_port(99999)

    def test_validate_replica_count_valid(self):
        """Test valid replica counts."""
        assert validate_replica_count(1) == 1
        assert validate_replica_count("50") == 50
        assert validate_replica_count(100) == 100

    def test_validate_replica_count_invalid(self):
        """Test invalid replica counts."""
        with pytest.raises(ValidationError, match="must be positive"):
            validate_replica_count(0)
        
        with pytest.raises(ValidationError, match="must be <= 100"):
            validate_replica_count(101)

    def test_validate_slo_target_valid(self):
        """Test valid SLO targets."""
        assert validate_slo_target(99.9) == 99.9
        assert validate_slo_target("99.99") == 99.99
        assert validate_slo_target(50.0) == 50.0

    def test_validate_slo_target_invalid(self):
        """Test invalid SLO targets."""
        with pytest.raises(ValidationError, match="must be 50"):
            validate_slo_target(49.9)
        
        with pytest.raises(ValidationError, match="must be 50"):
            validate_slo_target(100.0)

    def test_validate_languages_valid(self):
        """Test valid language lists."""
        assert validate_languages("python") == "python"
        assert validate_languages("python,javascript,go") == "python,javascript,go"

    def test_validate_languages_invalid(self):
        """Test invalid language lists."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_languages("")
        
        with pytest.raises(ValidationError, match="Invalid languages"):
            validate_languages("python,cobol")


class TestToolValidation:
    """Tests for tool-specific validation."""

    def test_validate_github_actions_workflow(self):
        """Test GitHub Actions workflow validation."""
        result = validate_tool_inputs("generate_github_actions_workflow", name="my-app")
        assert result["name"] == "my-app"
        
        with pytest.raises(ValidationError):
            validate_tool_inputs("generate_github_actions_workflow", name="Invalid-App")

    def test_validate_k8s_config(self):
        """Test Kubernetes config validation."""
        result = validate_tool_inputs(
            "generate_k8s_config",
            app_name="my-app",
            image="ghcr.io/org/app:v1",
            replicas=3,
            port=8080,
        )
        assert result["app_name"] == "my-app"
        assert result["replicas"] == 3
        
        with pytest.raises(ValidationError):
            validate_tool_inputs("generate_k8s_config", app_name="My-App")
        
        with pytest.raises(ValidationError):
            validate_tool_inputs("generate_k8s_config", image="python$(malicious)")
        
        with pytest.raises(ValidationError):
            validate_tool_inputs("generate_k8s_config", replicas=101)

    def test_validate_sre_configs(self):
        """Test SRE config validation."""
        result = validate_tool_inputs(
            "generate_sre_configs",
            name="api-svc",
            team="platform",
            namespace="production",
            slo_target=99.95,
        )
        assert result["name"] == "api-svc"
        assert result["slo_target"] == 99.95

    def test_validate_invalid_tool(self):
        """Test validation with unknown tool name."""
        # Should not raise, just pass through
        result = validate_tool_inputs("unknown_tool", foo="bar")
        assert result["foo"] == "bar"
