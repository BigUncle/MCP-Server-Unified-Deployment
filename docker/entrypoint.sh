#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# Default user/group IDs
USER_ID=${LOCAL_USER_ID:-1000}
GROUP_ID=${LOCAL_GROUP_ID:-1000}

echo "Entrypoint: Running as $(id)"
echo "Entrypoint: Ensuring user 'mcp' (UID: $USER_ID, GID: $GROUP_ID) owns required directories..."

# List of directories that need correct permissions (based on docker-compose volumes)
# Note: /home/mcp should already be owned by mcp due to useradd in Dockerfile
# We focus on the mount points inside /app and /home/mcp that receive volumes
declare -a DIRS_TO_FIX=(
    "/app/config"
    "/app/logs"
    "/app/pids"
    "/app/mcp-data"
    "/app/mcp-servers"
    "/home/mcp/.npm"
    "/home/mcp/.local" # Ensure .local and subdirs are correct, pipx/pip install here
    "/home/mcp/.cache" # Ensure .cache and subdirs are correct, uv cache here
    # Add /home/mcp/.uvx if it's a separate volume mount target
)

# Create directories if they don't exist and set ownership
# Use find to only chown directories that actually exist (might not be mounted)
for dir in "${DIRS_TO_FIX[@]}"; do
    # Create directory if it doesn't exist first
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "Entrypoint: Created missing directory $dir"
    fi

    # Check current ownership
    if [ -d "$dir" ]; then
        current_uid=$(stat -c '%u' "$dir")
        current_gid=$(stat -c '%g' "$dir")
        
        if [ "$current_uid" != "$USER_ID" ] || [ "$current_gid" != "$GROUP_ID" ]; then
            echo "Entrypoint: Correcting permissions for $dir (UID:$current_uid->$USER_ID, GID:$current_gid->$GROUP_ID)..."
            chown -R "$USER_ID:$GROUP_ID" "$dir" || echo "Entrypoint: Warning - Failed to chown $dir"
        else
            echo "Entrypoint: Permissions OK for $dir (UID:$USER_ID, GID:$GROUP_ID)"
        fi
    else
        echo "Entrypoint: Directory $dir not found, skipping chown."
    fi
done

# Ensure the primary user's home directory itself is correct, just in case
echo "Entrypoint: Verifying ownership for /home/mcp..."
chown "$USER_ID:$GROUP_ID" /home/mcp || echo "Entrypoint: Warning - Failed to chown /home/mcp"

echo "Entrypoint: Permissions check complete."
echo "Entrypoint: Switching to user 'mcp' (UID: $USER_ID) to execute command: $@"

# Execute the command passed into the script (CMD in Dockerfile) as the 'mcp' user
exec gosu mcp "$@"