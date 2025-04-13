# Production Dockerfile for MCP Server Unified Deployment
# Uses multi-stage build, non-root user, and installs tools efficiently.

# ---- Base Stage ----
# Use a specific Python version for reproducibility
FROM python:3.12-slim AS base

# Set environment variables for locale, timezone, Python, and tool paths for non-root user
ENV LANG=zh_CN.UTF-8 \
    LANGUAGE=zh_CN:zh \
    LC_ALL=zh_CN.UTF-8 \
    TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Paths for tools installed as non-root user 'mcp'
    PATH="/home/mcp/.local/bin:/home/mcp/.uv/bin:$PATH" \
    PIPX_HOME="/home/mcp/.local/pipx" \
    PIPX_BIN_DIR="/home/mcp/.local/bin" \
    UV_CACHE_DIR="/home/mcp/.cache/uv" \
    NPM_CONFIG_PREFIX="/home/mcp/.npm" \
    NODE_PATH="/app/node_modules:/home/mcp/.npm/lib/node_modules"

# Create a non-root user and group first
RUN groupadd --gid 1000 mcp && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home mcp

# Install essential OS packages + Node.js + Git + Set timezone/locale
# Use mirrors for faster downloads (optional)
RUN printf "deb http://mirrors.aliyun.com/debian/ bookworm main contrib non-free non-free-firmware\n\
deb http://mirrors.aliyun.com/debian/ bookworm-updates main contrib non-free non-free-firmware\n\
deb http://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free non-free-firmware\n" > /etc/apt/sources.list \
    && rm -rf /etc/apt/sources.list.d/* \
    && apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    locales \
    nginx \
    net-tools \
    iproute2 \
    # Install Node.js (e.g., LTS version 22.x)
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    # Configure timezone (optional)
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    # Configure locale (optional)
    && echo "zh_CN.UTF-8 UTF-8" >> /etc/locale.gen && locale-gen zh_CN.UTF-8 \
    # Install gosu for entrypoint privilege drop
    && apt-get install -y --no-install-recommends gosu \
    # Clean up
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the entrypoint script early and set permissions as root
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set WORKDIR for user installs first
WORKDIR /home/mcp

# Switch to mcp only for the commands that need it
USER mcp
# Upgrade pip and set pip mirrors (Optional)
RUN python -m pip install --upgrade pip && \
    python -m pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

# Install uv and pipx for the 'mcp' user
# Use --user flag for non-root install
RUN python -m pip install --user --no-cache-dir uv pipx
# Ensure pipx paths are recognised (redundant with ENV PATH but safe)
RUN python -m pipx ensurepath

# Install mcp-proxy using pipx as the 'mcp' user
# No need for symlink if PATH is correct
RUN pipx install mcp-proxy
# Switch back to root after mcp-specific commands
USER root
# Reset WORKDIR to root's default or /
WORKDIR / 

# ---- Builder Stage (Optional but good practice for deps) ----
FROM base AS builder

USER mcp
WORKDIR /app

# Copy only necessary files for dependency installation
COPY --chown=mcp:mcp requirements.txt ./
# Optional, if you have a package.json
COPY --chown=mcp:mcp package.json ./ 

# Install Python dependencies using uv as 'mcp' user
# Ensure PyYAML is in requirements.txt or install explicitly
RUN python -m pip install --user --no-cache-dir PyYAML # Add PyYAML here or in requirements.txt
RUN python -m pip install --user --no-cache-dir -r requirements.txt

# Install node dependencies if package.json has entries (optional)
# RUN npm install --prefix /app

# ---- Final Stage ----
FROM base AS final

# ... (Create directories, set ownership as before) ...
RUN mkdir -p \
    /app/config \
    /app/logs \
    /app/pids \
    /app/mcp-data \
    /app/mcp-servers \
    /app/client_configs \
    /etc/nginx/generated_conf.d # Ensure Nginx config dir exists for generator script

RUN chown -R mcp:mcp /app /etc/nginx/generated_conf.d && \
    chmod 2775 /app /etc/nginx/generated_conf.d && \
    find /app /etc/nginx/generated_conf.d -type d -exec chmod 2775 {} \; && \
    find /app -type f -exec chmod 0664 {} \;

USER mcp
WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder --chown=mcp:mcp /home/mcp/.local /home/mcp/.local
# Copy node_modules if built
# COPY --from=builder --chown=mcp:mcp /app/node_modules /app/node_modules

# Copy application code
COPY --chown=mcp:mcp scripts /app/scripts
COPY --chown=mcp:mcp scripts/mcp_manager /app/mcp_manager
# Copy the EXAMPLE YAML config file
COPY --chown=mcp:mcp config/mcp_servers.example.yaml /app/config/mcp_servers.example.yaml
# For reference
COPY --chown=mcp:mcp requirements.txt /app/requirements.txt
# Example - Your actual paths might differ slightly
COPY --chown=mcp:mcp docker/entrypoint.sh /usr/local/bin/entrypoint.sh

# ... (Verify tools) ...
RUN /home/mcp/.local/bin/uv --version && \
    /home/mcp/.local/bin/pipx --version && \
    /home/mcp/.local/bin/mcp-proxy --help && \
    node --version && npm --version && npx --version && \
    python -c "import yaml; print(f'PyYAML version: {yaml.__version__}')" # Verify PyYAML

USER root

# --- NO LONGER EXPOSE internal ports ---
# EXPOSE 23001-23020

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# CMD remains the same, container_startup.py handles YAML and generators
CMD ["/bin/bash", "-c", "python /app/scripts/container_startup.py && python /app/scripts/manage_mcp.py daemon"]