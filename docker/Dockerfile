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
COPY --chown=mcp:mcp package.json ./

# Install Python dependencies using uv as 'mcp' user
RUN python -m pip install --user --no-cache-dir -r requirements.txt

# Install node dependencies if package.json has entries (optional)
# RUN npm install --prefix /app

# ---- Final Stage ----
FROM base AS final

# Create directory structure as root first
WORKDIR /app

# 1. Create app directories with correct ownership
RUN mkdir -p \
    /app/config \
    /app/logs \
    /app/pids \
    /app/mcp-data \
    /app/mcp-servers \
    /app/client_configs

RUN chown -R mcp:mcp /app && \
    chmod 2775 /app && \
    find /app -type d -exec chmod 2775 {} \; && \
    find /app -type f -exec chmod 0664 {} \;    
# 2. Switch to mcp user for application setup
USER mcp

# Copy installed Python packages from builder stage to user's .local
COPY --from=builder --chown=mcp:mcp /home/mcp/.local /home/mcp/.local
# Copy node_modules if built in builder stage
# COPY --from=builder --chown=mcp:mcp /app/node_modules /app/node_modules


# Copy application code
COPY --chown=mcp:mcp scripts /app/scripts
COPY --chown=mcp:mcp scripts/mcp_manager /app/mcp_manager
COPY --chown=mcp:mcp config/mcp_servers.example.json /app/config/mcp_servers.example.json
# Copy requirements.txt again for reference if needed, though installed already
COPY --chown=mcp:mcp requirements.txt /app/requirements.txt

# Ensure necessary application directories exist and have correct ownership
# These paths should match the volumes in docker-compose.yml
# RUN mkdir -p /app/config /app/logs /app/pids /app/mcp-data /app/mcp-servers /app/client_configs && \
#     chown -R mcp:mcp /app

# Verify key tools are runnable by 'mcp' user
# Use full path if PATH isn't immediately active in RUN layer
RUN /home/mcp/.local/bin/uv --version && \
    /home/mcp/.local/bin/pipx --version && \
    /home/mcp/.local/bin/mcp-proxy --help && \
    node --version && npm --version && npx --version
# Switch back to root before EXPOSE and ENTRYPOINT
USER root

# Expose the typical MCP port range (adjust if needed)
EXPOSE 23001-23020

# Entrypoint script is copied and made executable in the base stage as root

# Define the entrypoint to run the wrapper script
# The wrapper script will handle permissions and then execute the original command as the 'mcp' user
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# The default command to be executed by the entrypoint script (passed as arguments "$@")
CMD ["/bin/bash", "-c", "python /app/scripts/container_startup.py && python /app/scripts/manage_mcp.py daemon"]

# CMD can provide default arguments to ENTRYPOINT, but not needed here.
# CMD ["daemon"]