import yaml # Use yaml instead of json
import os
import logging
from pathlib import Path
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration Paths ---
APP_DIR = Path('/app')
CONFIG_FILE = APP_DIR / 'config' / 'mcp_servers.yaml' # Changed to .yaml
NGINX_GENERATED_CONF_DIR_ENV = os.environ.get('NGINX_CONFIG_DIR', '/etc/nginx/generated_conf.d')
NGINX_GENERATED_CONF_DIR = Path(NGINX_GENERATED_CONF_DIR_ENV)

# Nginx location template - Updated path structure
# Matches /<service_name>/sse/ and proxies to internal /sse/
NGINX_LOCATION_TEMPLATE = """
# Config for service: {service_name}
location /{service_name}/sse/ {{
    # Use the Docker Compose service name 'mcp-server' for internal resolution
    # Trailing slash is important for proxy_pass with URI rewriting
    proxy_pass http://mcp-server:{internal_port}/sse/;

    # Standard proxy headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # WebSocket/SSE specific headers
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    # SSE specific settings
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 86400s; # Keep connection open for long time
    proxy_send_timeout 86400s;
    keepalive_timeout 86400s; # Keep upstream connection alive

    # Optional: Add access control here if needed
}}
"""

def load_mcp_config():
    """Loads the mcp_servers.yaml configuration."""
    if not CONFIG_FILE.exists():
        logging.error(f"MCP configuration file not found: {CONFIG_FILE}")
        return None
    try:
        with CONFIG_FILE.open('r', encoding='utf-8') as f:
            # Use yaml.safe_load()
            config = yaml.safe_load(f)
            if config is None: # Handle empty file case
                 logging.warning(f"MCP configuration file {CONFIG_FILE} is empty.")
                 return {'servers': []} # Return empty structure
            return config
    except yaml.YAMLError as e:
        logging.error(f"Error decoding YAML from {CONFIG_FILE}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error reading MCP configuration {CONFIG_FILE}: {e}")
        return None

def generate_configs():
    """Generates Nginx location config files for enabled MCP servers."""
    logging.info(f"Starting Nginx config generation...")
    logging.info(f"Reading MCP config from: {CONFIG_FILE}")
    logging.info(f"Writing Nginx configs to: {NGINX_GENERATED_CONF_DIR}")

    mcp_config = load_mcp_config()
    if mcp_config is None or 'servers' not in mcp_config:
        logging.error("Invalid or missing MCP server configuration.")
        return False

    if not NGINX_GENERATED_CONF_DIR.exists():
        logging.info(f"Creating Nginx generated config directory: {NGINX_GENERATED_CONF_DIR}")
        try:
            NGINX_GENERATED_CONF_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logging.error(f"Failed to create directory {NGINX_GENERATED_CONF_DIR}: {e}")
            return False

    # --- Cleanup old configs ---
    cleaned_count = 0
    for old_conf in NGINX_GENERATED_CONF_DIR.glob('*.conf'):
        try:
            old_conf.unlink()
            logging.debug(f"Removed old config: {old_conf.name}")
            cleaned_count += 1
        except Exception as e:
            logging.warning(f"Could not remove old config file {old_conf}: {e}")
    if cleaned_count > 0:
        logging.info(f"Cleaned up {cleaned_count} old Nginx config files.")

    # --- Generate new configs ---
    generated_count = 0
    for server in mcp_config.get('servers', []):
        if server.get('enabled', False): # Process only explicitly enabled servers
            service_name = server.get('name')
            internal_port = server.get('internal_port') # Use internal_port

            if not service_name:
                logging.warning(f"Skipping server due to missing 'name': {server}")
                continue
            if not internal_port:
                logging.warning(f"Skipping server '{service_name}' due to missing 'internal_port'.")
                continue

            # Basic validation for service name (URL path segment)
            # Allow alphanumeric, hyphen, underscore. Avoid slashes, etc.
            if not all(c.isalnum() or c in ['-', '_'] for c in service_name):
                 logging.warning(f"Skipping server '{service_name}' due to potentially unsafe characters in name. Use alphanumeric, hyphen, or underscore.")
                 continue

            logging.info(f"Generating Nginx config for '{service_name}' -> proxy to http://mcp-server:{internal_port}/sse/")

            nginx_conf_content = NGINX_LOCATION_TEMPLATE.format(
                service_name=service_name,
                internal_port=internal_port
            )

            conf_file_path = NGINX_GENERATED_CONF_DIR / f"{service_name}.conf"
            try:
                with conf_file_path.open('w', encoding='utf-8') as f:
                    f.write(nginx_conf_content.strip())
                generated_count += 1
                logging.debug(f"Successfully wrote config file: {conf_file_path}")
            except Exception as e:
                logging.error(f"Failed to write Nginx config for {service_name} to {conf_file_path}: {e}")
        else:
            logging.info(f"Skipping disabled server: {server.get('name', 'N/A')}")

    logging.info(f"Generated {generated_count} Nginx config files.")
    return generated_count > 0

def trigger_nginx_reload():
    """Logs that Nginx needs a reload."""
    logging.info("Nginx configuration generated. Nginx needs to reload to apply changes.")
    logging.info("Manual reload: 'docker exec mcp-proxy-nginx nginx -s reload'")
    # Automatic reload mechanism is out of scope for this script but recommended for production.

def main():
    if os.environ.get('GENERATE_NGINX_CONFIG', 'false').lower() == 'true':
        if generate_configs():
            trigger_nginx_reload()
        else:
            logging.warning("Nginx config generation ran, but no configs were generated.")
    else:
        logging.info("Nginx config generation is disabled (GENERATE_NGINX_CONFIG is not 'true').")

if __name__ == "__main__":
    main()