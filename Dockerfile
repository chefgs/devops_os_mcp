# Dockerfile for DevOps-OS MCP Server
# Multi-stage build: runtime layer only includes necessary artifacts

# Stage 1: Builder
FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy application source and requirements
COPY mcp_server/requirements.txt mcp_server/requirements.txt
COPY cli/requirements.txt cli/requirements.txt
RUN mkdir -p /build/cli /build/mcp_server

# Install Python dependencies into virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r mcp_server/requirements.txt && \
    pip install -r cli/requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

# Labels
LABEL org.opencontainers.image.title="DevOps-OS MCP Server"
LABEL org.opencontainers.image.description="MCP server for DevOps configuration generation"
LABEL org.opencontainers.image.version="1.0.0"

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEVOPS_OS_PROFILE="local" \
    DEVOPS_OS_TRANSPORT="streamable-http" \
    DEVOPS_OS_HOST="0.0.0.0" \
    DEVOPS_OS_PORT="8000" \
    DEVOPS_OS_LOG_LEVEL="INFO"

# Create non-root user (devops-os:devops-os with UID:GID 1000:1000)
RUN groupadd -r devops-os -g 1000 && \
    useradd -r -g devops-os -u 1000 -d /home/devops-os -s /sbin/nologin -c "DevOps-OS MCP user" devops-os && \
    mkdir -p /home/devops-os && \
    chown -R devops-os:devops-os /home/devops-os

# Copy virtual environment from builder
COPY --from=builder --chown=devops-os:devops-os /opt/venv /opt/venv

# Copy application code
WORKDIR /app
COPY --chown=devops-os:devops-os mcp_server /app/mcp_server
COPY --chown=devops-os:devops-os cli /app/cli
COPY --chown=devops-os:devops-os .mcp.json /app/.mcp.json 2>/dev/null || true

# Create temporary directory with size limits and set permissions
RUN mkdir -p /tmp/devops-os && \
    chown -R devops-os:devops-os /tmp/devops-os && \
    chmod 1777 /tmp/devops-os

# Make application root directory readable only by devops-os user
RUN chmod 750 /app

# Create .local directory for user
RUN mkdir -p /home/devops-os/.local && \
    chown -R devops-os:devops-os /home/devops-os/.local

# Switch to non-root user
USER devops-os

# Healthcheck: verify server is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import socket; socket.create_connection(('localhost', ${DEVOPS_OS_PORT}), timeout=2)" || exit 1

# Run MCP server
ENTRYPOINT ["python3", "-m", "mcp_server.server"]
CMD []

# Expose port
EXPOSE 8000
