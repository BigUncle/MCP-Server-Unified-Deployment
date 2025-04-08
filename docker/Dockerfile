# Production Dockerfile for MCP Server Unified Deployment
# Based on python:3.12-slim with minimal dependencies for production use

# Build stage for optimizing image size
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Set environment variables to reduce Python bytecode generation and enable unbuffered mode
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git curl \
    connect-proxy ffmpeg locales locales-all \
    nodejs npm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install uv, pipx, debugpy
RUN pip install --no-cache-dir uv pipx debugpy
# Adjust pipx path configuration to ensure scripts are usable
RUN pipx ensurepath && \
    echo 'export PATH="$PATH:$HOME/.local/bin"' >> /root/.bashrc && \
    . /root/.bashrc

# Install uvx (uv extension commands) and verify it's available
##############################################################################
# DO NOT USE `pip install uvx`, AS IT WILL INSTALL ANOTHER UV PACKAGE,
# WHICH ISN A DEPRECATED PACKAGE(https://pypi.org/project/uvx/), NOT WHATT WE WANT
# THE ACTUAL UVX PACKAGE WE WANT TO USE IS AT: https://pypi.org/project/uv/
##############################################################################
RUN pip install --no-cache-dir uv && \
    ln -sf $(which uvx) /usr/local/bin/uvx && \
    which uvx || echo "uvx installation failed"

# Install mcp-proxy and verify it's installed correctly
RUN pipx install mcp-proxy && \
    ln -sf /root/.local/bin/mcp-proxy /usr/local/bin/mcp-proxy && \
    which mcp-proxy || echo "mcp-proxy installation failed"

# Copy requirements
COPY requirements.txt requirements.txt

# Install Python dependencies
RUN if [ -f requirements.txt ]; then uv pip install -r requirements.txt --system; fi

# Final stage
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set timezone if needed
# ENV TZ=Asia/Shanghai
# RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    git curl \
    connect-proxy ffmpeg locales locales-all \
    nodejs npm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install pipx and mcp-proxy in the final image
RUN pip install --no-cache-dir pipx && \
    pipx ensurepath && \
    pipx install mcp-proxy && \
    ln -sf /root/.local/bin/mcp-proxy /usr/local/bin/mcp-proxy

# Install uvx in the final image and verify it works
##############################################################################
# DO NOT USE `pip install uvx`, AS IT WILL INSTALL ANOTHER UV PACKAGE,
# WHICH ISN A DEPRECATED PACKAGE(https://pypi.org/project/uvx/), NOT WHATT WE WANT
# THE ACTUAL UVX PACKAGE WE WANT TO USE IS AT: https://pypi.org/project/uv/
##############################################################################

RUN pip install --no-cache-dir uv && \
    ln -sf $(which uvx) /usr/local/bin/uvx && \
    uvx --help && \
    which uvx || echo "uvx installation failed"

# Set locale if needed
# RUN echo "zh_CN.UTF-8 UTF-8" > /etc/locale.gen && locale-gen zh_CN.UTF-8 && update-locale LANG=zh_CN.UTF-8 LANGUAGE=zh_CN:zh LC_ALL=zh_CN.UTF-8
# ENV LANG=zh_CN.UTF-8 \
#     LANGUAGE=zh_CN:zh \
#     LC_ALL=zh_CN.UTF-8

# Verify required dependencies are installed
RUN pip list | grep psutil || pip install --no-cache-dir psutil>=5.9.0
RUN node --version && npm --version && npx --version || (echo "Node.js, npm, or npx is not installed correctly" && exit 1)

# Create necessary directories
RUN mkdir -p /app/logs /app/pids

# Copy application code
COPY . .

# Set daemon mode environment variable
ENV MCP_DAEMON_MODE=true

# Command to run the application in daemon mode
CMD ["python", "scripts/manage_mcp.py", "daemon"]
