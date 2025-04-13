# -*- coding: utf-8 -*-

"""
MCP Configuration Generator (YAML Input, Fixed Port Output)
Generates client configuration files based on mcp_servers.yaml.
All URLs point to the Nginx proxy using the format: http://<host_ip>:<nginx_port>/{server_name}/sse/
"""

import yaml # Use yaml instead of json
import os
import sys
import json
import random
import string
import time
from pathlib import Path
import logging

logger = logging.getLogger('config_generator')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration file paths
APP_DIR = Path(__file__).parent.parent
CONFIG_FILE = APP_DIR / "config" / "mcp_servers.yaml" # Changed to .yaml
CONFIG_OUTPUT_DIR = APP_DIR / "config" / "client_configs"
CONFIG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Get Nginx fixed port and host IP from environment variables
NGINX_HOST_PORT = os.environ.get('NGINX_HOST_PORT', '23000') # Default to 23000
HOST_IP = os.environ.get('REAL_HOST_IP', 'localhost') # Should be set correctly by container_startup.py

# Default configurations (can be kept or simplified)
CLIENT_DEFAULTS = {
    "cline": {"timeout": 60, "transportType": "sse"},
    "roo_code": {},
    "cherry_studio": {"isActive": True, "description": ""},
    "github_copilot": {"type": "sse"}
}

def load_mcp_config():
    """Loads the mcp_servers.yaml configuration."""
    if not CONFIG_FILE.exists():
        logger.error(f"MCP configuration file not found: {CONFIG_FILE}")
        return None
    try:
        with CONFIG_FILE.open('r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config is None:
                 logger.warning(f"MCP configuration file {CONFIG_FILE} is empty.")
                 return {'servers': []}
            return config
    except yaml.YAMLError as e:
        logger.error(f"Error decoding YAML from {CONFIG_FILE}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading MCP configuration {CONFIG_FILE}: {e}")
        return None

def generate_random_id(length=20):
    """Generate random ID for Cherry Studio configuration"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_client_facing_url(service_name):
    """Generates the client-facing URL via Nginx proxy."""
    if not HOST_IP or HOST_IP == 'localhost':
         logger.warning(f"REAL_HOST_IP environment variable not set or is 'localhost'. Client URLs may not work externally.")
    # Ensure trailing slash for consistency
    return f"http://{HOST_IP}:{NGINX_HOST_PORT}/{service_name}/sse/"

# --- Updated Generator Functions ---

def generate_cline_config(servers_config):
    """Generate Cline format configuration file"""
    config = {"mcpServers": {}}
    for server in servers_config.get("servers", []):
        service_name = server["name"]
        is_enabled = server.get("enabled", False)

        url = get_client_facing_url(service_name) if is_enabled else ""
        server_config = {
            "disabled": not is_enabled,
            "timeout": CLIENT_DEFAULTS["cline"]["timeout"],
            "url": url,
            "transportType": CLIENT_DEFAULTS["cline"]["transportType"]
        }
        if is_enabled and "autoApprove" in server:
             server_config["autoApprove"] = [] if server["autoApprove"] == "*" else server["autoApprove"]

        config["mcpServers"][service_name] = server_config
    return config

def generate_roo_code_config(servers_config):
    """Generate Roo Code format configuration file"""
    config = {"mcpServers": {}}
    for server in servers_config.get("servers", []):
        service_name = server["name"]
        is_enabled = server.get("enabled", False)

        url = get_client_facing_url(service_name) if is_enabled else ""
        server_config = {
            "disabled": not is_enabled, # Add disabled flag
            "url": url
        }
        if is_enabled and "autoApprove" in server:
             # Roo Code uses 'alwaysAllow'
             server_config["alwaysAllow"] = [] if server["autoApprove"] == "*" else server["autoApprove"]

        config["mcpServers"][service_name] = server_config
    return config

def generate_cherry_studio_config(servers_config):
    """Generate Cherry Studio format configuration file"""
    config = {"mcpServers": {}}
    # Add mcp-auto-install entry (remains the same)
    config["mcpServers"]["cPqOEdSHLwBLnukhxTppp"] = {
        "isActive": True, "name": "mcp-auto-install",
        "description": "Automatically install MCP services (Beta version)",
        "baseUrl": "", "command": "npx",
        "args": ["-y", "@mcpmarket/mcp-auto-install", "connect", "--json"],
        "registryUrl": "https://registry.npmmirror.com", "env": {}
    }

    for server in servers_config.get("servers", []):
        server_id = generate_random_id()
        service_name = server["name"]
        is_active = server.get("enabled", False)
        url = get_client_facing_url(service_name) if is_active else ""

        server_config = {
            "isActive": is_active,
            "name": service_name,
            "description": server.get("description", service_name),
            "baseUrl": url # Use the new URL format
        }
        config["mcpServers"][server_id] = server_config
    return config

def generate_github_copilot_config(servers_config):
    """Generate GitHub Copilot format configuration file"""
    config = {"mcp": {"servers": {}}}
    for server in servers_config.get("servers", []):
        service_name = server["name"]
        is_enabled = server.get("enabled", False)

        if not is_enabled:
            continue # Skip disabled servers entirely for this format

        url = get_client_facing_url(service_name)
        server_type = server.get("transport_type", CLIENT_DEFAULTS["github_copilot"]["type"]) # Keep transport type if needed

        server_config = {
            "type": server_type,
            "url": url # Use the new URL format
        }
        # No autoApprove in this format currently
        config["mcp"]["servers"][service_name] = server_config
    return config

# --- File Saving ---

def save_config_to_file(config_data, filename):
    """Save configuration data (dict) to a JSON file."""
    file_path = CONFIG_OUTPUT_DIR / filename
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            # Still save client configs as JSON
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        logger.debug(f"Saved client config: {file_path}")
        return str(file_path)
    except Exception as e:
        logger.error(f"Failed to save client config {filename}: {e}")
        return None

# --- Main Generation Logic ---

def generate_all_configs():
    """Load MCP config and generate all client configuration files."""
    servers_config = load_mcp_config()
    if not servers_config:
        logger.error("Failed to load server configuration. Cannot generate client configs.")
        return None

    logger.info("Generating client configurations...")
    configs = {
        "cline": generate_cline_config(servers_config),
        "roo_code": generate_roo_code_config(servers_config),
        "cherry_studio": generate_cherry_studio_config(servers_config),
        "github_copilot": generate_github_copilot_config(servers_config)
    }

    timestamp = time.strftime("%Y%m%d%H%M%S")
    saved_paths = {"latest": {}}

    for name, data in configs.items():
        # Save timestamped version
        ts_filename = f"mcp_{name}_{timestamp}.json"
        ts_path = save_config_to_file(data, ts_filename)
        if ts_path:
            saved_paths[name] = ts_path
        # Save latest version
        latest_filename = f"mcp_{name}_latest.json"
        latest_path = save_config_to_file(data, latest_filename)
        if latest_path:
            saved_paths["latest"][name] = latest_path

    if not any(saved_paths.values()): # Check if anything was saved
         logger.error("Failed to save any client configuration files.")
         return None

    return saved_paths

if __name__ == "__main__":
    result = generate_all_configs()
    if result:
        logger.info("Client configuration files generation completed:")
        # Log paths for clarity
    else:
        logger.error("Failed to generate client configuration files.")
        sys.exit(1) # Exit with error if generation failed