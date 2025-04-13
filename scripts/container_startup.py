#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Container Startup Script for MCP Server (YAML Version)
Handles initialization: directory checks, tool verification, YAML config handling,
IP detection, environment setup, and triggering config generators.
"""

import os
import socket
import sys
import yaml # Use yaml
from pathlib import Path
import subprocess
import time
import logging
import stat
import shutil
import importlib # To import generator scripts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger('container_startup')

# Constants
APP_DIR = Path('/app')
CONFIG_DIR = APP_DIR / 'config'
LOGS_DIR = APP_DIR / 'logs'
PIDS_DIR = APP_DIR / 'pids'
MCP_DATA_DIR = APP_DIR / 'mcp-data'
MCP_SERVERS_DIR = APP_DIR / 'mcp-servers'
CLIENT_CONFIGS_DIR = CONFIG_DIR / 'client_configs' # Output dir for JSON client configs

CONFIG_FILE = CONFIG_DIR / 'mcp_servers.yaml' # Changed to .yaml
EXAMPLE_CONFIG_FILE = CONFIG_DIR / 'mcp_servers.example.yaml' # Changed to .yaml

SCRIPTS_DIR = APP_DIR / 'scripts'
HOST_DETECTOR_SCRIPT = SCRIPTS_DIR / 'detect_host_ip.py'

# --- Helper Functions (ensure_directory, check_essential_tools remain the same) ---
def ensure_directory(dir_path: Path):
    # ... (Keep the existing implementation) ...
    try:
        if not dir_path.exists():
            logger.info(f"Creating directory: {dir_path}")
            dir_path.mkdir(parents=True, exist_ok=True)
        else:
            logger.debug(f"Directory already exists: {dir_path}")
        if not os.access(dir_path, os.W_OK):
            logger.error(f"FATAL: Directory {dir_path} is not writable by user {os.geteuid()}. Check volume permissions.")
            # Attempt fix (might fail on host volume issues)
            try:
                current_mode = dir_path.stat().st_mode
                os.chmod(dir_path, current_mode | stat.S_IWUSR)
                if not os.access(dir_path, os.W_OK): return False
                logger.info(f"Added write permission for user to {dir_path}.")
            except Exception as e:
                logger.error(f"Error attempting to fix permissions for {dir_path}: {e}")
                return False
        return True
    except Exception as e:
        logger.error(f"Failed to ensure directory {dir_path}: {e}")
        return False

def check_essential_tools():
    # ... (Keep the existing implementation) ...
    tools = ["python", "node", "npm", "npx", "git", "uv", "pipx", "mcp-proxy", "yaml"] # Check yaml via python import later
    all_found = True
    logger.info("Checking for essential tools in PATH...")
    for tool in tools:
         if tool == "yaml": continue # Check later
         tool_path = shutil.which(tool)
         if tool_path: logger.info(f"  [OK] Found: {tool} at {tool_path}")
         else: logger.error(f"  [MISSING] Tool not found in PATH: {tool}"); all_found = False
    # Check PyYAML
    try:
        import yaml
        logger.info(f"  [OK] Found: PyYAML library (version {yaml.__version__})")
    except ImportError:
        logger.error("  [MISSING] PyYAML library not found. Please install it (pip install PyYAML).")
        all_found = False

    if not all_found:
         logger.critical("One or more essential tools/libraries are missing.")
    return all_found

# --- Updated Config Check ---
def check_mcp_config():
    """Check if MCP server YAML configuration file exists and is valid."""
    logger.info(f"Checking MCP configuration file: {CONFIG_FILE}...")
    if not CONFIG_FILE.exists():
        logger.warning(f"Configuration file not found.")
        if EXAMPLE_CONFIG_FILE.exists():
            try:
                logger.info(f"Copying example configuration from {EXAMPLE_CONFIG_FILE} to {CONFIG_FILE}")
                shutil.copy(EXAMPLE_CONFIG_FILE, CONFIG_FILE)
                logger.info("Example configuration copied. Please review and customize it.")
                if not CONFIG_FILE.exists():
                     logger.error("Failed to create config file from example.")
                     return False
            except Exception as e:
                logger.error(f"Failed to copy example configuration: {e}")
                return False
        else:
             logger.error(f"No configuration file found at {CONFIG_FILE}, and no example file available at {EXAMPLE_CONFIG_FILE}.")
             return False

    # Check YAML content
    try:
        with CONFIG_FILE.open('r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if config is None: # Handle empty file
             logger.warning(f"Configuration file {CONFIG_FILE} is empty or contains only comments.")
             # Consider if an empty config is valid (e.g., no servers enabled)
             return True # Treat as valid for now, subsequent steps will handle no servers

        # Basic structure validation
        if not isinstance(config, dict) or 'servers' not in config:
            logger.error(f"Invalid format in {CONFIG_FILE}: Must be a YAML mapping with a 'servers' key (list).")
            return False
        if not isinstance(config['servers'], list):
            logger.error(f"Invalid format in {CONFIG_FILE}: 'servers' key must be a YAML list.")
            return False

        # Check if there are any enabled servers
        enabled_servers = [s for s in config.get('servers', []) if s.get('enabled', False)]
        if not enabled_servers:
            logger.warning(f"No enabled MCP servers found in configuration: {CONFIG_FILE}")
        else:
            logger.info(f"Found {len(enabled_servers)} enabled MCP servers in configuration.")

        logger.info(f"MCP configuration file {CONFIG_FILE} is valid YAML.")
        return True
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in configuration file {CONFIG_FILE}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error reading or parsing configuration file {CONFIG_FILE}: {e}")
        return False

# --- IP Detection and Environment Update (detect_host_ip, update_environment_variables remain the same) ---
def detect_host_ip():
    # ... (Keep the existing implementation, ensure iproute2 is installed in Dockerfile if 'ip' command is used) ...
    logger.info("Attempting to detect host IP...")
    detected_ip = None
    # Priority: REAL_HOST_IP env -> EXTERNAL_HOST env -> detect_host_ip.py script -> gateway -> hostname -I -> localhost
    env_ip = os.environ.get('REAL_HOST_IP')
    if env_ip and env_ip != 'localhost': # Trust explicitly set REAL_HOST_IP
        try:
            socket.inet_aton(env_ip); logger.info(f"Using IP from REAL_HOST_IP env var: {env_ip}"); return env_ip
        except socket.error: logger.warning(f"REAL_HOST_IP value '{env_ip}' is invalid.")

    env_ip = os.environ.get('EXTERNAL_HOST')
    if env_ip and env_ip != 'localhost':
        try:
            socket.inet_aton(env_ip); logger.info(f"Using IP from EXTERNAL_HOST env var: {env_ip}"); return env_ip
        except socket.error: logger.warning(f"EXTERNAL_HOST value '{env_ip}' is invalid.")

    if HOST_DETECTOR_SCRIPT.exists():
        # ... (Run script as before) ...
        try:
            result = subprocess.run([sys.executable, str(HOST_DETECTOR_SCRIPT)], capture_output=True, text=True, check=False, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "Detected host IP:" in line:
                        ip = line.split("Detected host IP:")[1].strip()
                        try: socket.inet_aton(ip); logger.info(f"Detected host IP via script: {ip}"); return ip
                        except socket.error: logger.warning(f"IP detected by script is invalid: {ip}")
        except Exception as e: logger.error(f"Error running host IP detector script: {e}")
    else: logger.warning(f"Host IP detector script not found at {HOST_DETECTOR_SCRIPT}.")

    # Fallback: Gateway (requires iproute2)
    try:
        result = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, check=False)
        if result.returncode == 0 and 'via' in result.stdout:
            gateway_ip = result.stdout.split('via ')[1].split()[0]
            try: socket.inet_aton(gateway_ip); logger.info(f"Using default gateway IP: {gateway_ip}"); return gateway_ip
            except socket.error: pass
    except FileNotFoundError: logger.warning("'ip' command not found, cannot detect gateway IP.")
    except Exception: pass # Ignore errors

    # Fallback: hostname -I (requires net-tools or similar)
    try:
        result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
             ips = result.stdout.strip().split()
             if ips:
                 for ip in ips: # Prefer non-internal if possible
                     if not ip.startswith('172.') and not ip.startswith('127.'):
                         try: socket.inet_aton(ip); logger.info(f"Using first non-internal IP from 'hostname -I': {ip}"); return ip
                         except socket.error: continue
                 # Fallback to first valid IP from hostname -I
                 for ip in ips:
                      try: socket.inet_aton(ip); logger.info(f"Using first valid IP from 'hostname -I': {ip}"); return ip
                      except socket.error: continue
    except FileNotFoundError: logger.warning("'hostname' command not found, cannot detect IP via hostname -I.")
    except Exception: pass

    logger.error("Could not determine a suitable host IP. Falling back to 'localhost'. External access will likely fail.")
    return 'localhost'


def update_environment_variables(host_ip):
    # ... (Keep the existing implementation) ...
    if not host_ip: logger.error("Cannot update environment variables: No host IP."); return
    logger.info(f"Setting container environment: REAL_HOST_IP={host_ip}, EXTERNAL_HOST={host_ip}")
    os.environ['REAL_HOST_IP'] = host_ip
    os.environ['EXTERNAL_HOST'] = host_ip


# --- Trigger Config Generators ---
def trigger_config_generators():
    """Import and run the main functions of config generator scripts."""
    generators = {
        "Nginx": "generate_nginx_configs",
        "Client": "integrate_config_generator"
    }
    all_ok = True
    for name, module_name in generators.items():
        logger.info(f"Triggering {name} configuration generator ({module_name}.py)...")
        try:
            # Dynamically import the module
            generator_module = importlib.import_module(module_name)
            # Call its main function
            if hasattr(generator_module, 'main'):
                generator_module.main() # Assuming main() handles its own logging/errors
                logger.info(f"{name} configuration generation process completed.")
            else:
                logger.error(f"Script {module_name}.py does not have a main() function.")
                all_ok = False
        except ImportError:
            logger.error(f"Failed to import generator script: {module_name}.py. Ensure it exists in scripts/.")
            all_ok = False
        except Exception as e:
            logger.error(f"Error occurred during {name} config generation ({module_name}.py): {e}")
            all_ok = False
    return all_ok

# --- Main Execution ---
def main():
    """Main container initialization sequence."""
    start_time = time.time()
    logger.info("--- Starting MCP Server Container Initialization (YAML Mode) ---")

    uid = os.geteuid(); gid = os.getegid(); home = os.environ.get('HOME', '/root')
    logger.info(f"Running as UID={uid}, GID={gid}, HOME={home}")
    logger.info(f"Current PATH: {os.environ.get('PATH', 'Not Set')}")

    # 1. Ensure essential directories
    logger.info("Step 1: Ensuring essential directories...")
    dirs_ok = all([
        ensure_directory(CONFIG_DIR), ensure_directory(LOGS_DIR), ensure_directory(PIDS_DIR),
        ensure_directory(CLIENT_CONFIGS_DIR), ensure_directory(MCP_DATA_DIR), ensure_directory(MCP_SERVERS_DIR),
        ensure_directory(Path(os.environ.get('NGINX_CONFIG_DIR', '/etc/nginx/generated_conf.d'))) # Ensure Nginx dir too
    ])
    if not dirs_ok: logger.critical("Directory check failed. Aborting."); return 1

    # 2. Check essential tools
    logger.info("Step 2: Checking for essential tools...")
    tools_ok = check_essential_tools()
    if not tools_ok: logger.critical("Essential tool check failed. Aborting."); return 1

    # 3. Check MCP server configuration (YAML)
    logger.info("Step 3: Checking MCP server configuration (YAML)...")
    config_ok = check_mcp_config()
    if not config_ok: logger.critical("MCP configuration check failed. Aborting."); return 1

    # 4. Detect host IP
    logger.info("Step 4: Detecting host IP...")
    host_ip = detect_host_ip()

    # 5. Update environment variables
    logger.info("Step 5: Updating environment variables...")
    update_environment_variables(host_ip)
    final_ip_for_clients = os.environ.get('REAL_HOST_IP', 'Not Set')

    # 6. Trigger Nginx and Client config generators
    logger.info("Step 6: Triggering configuration generators...")
    generators_ok = trigger_config_generators()
    if not generators_ok:
        logger.error("One or more configuration generators failed.")
        # Decide if this is fatal. Maybe Nginx can start with old/no configs?
        # return 1 # Make it fatal for now

    end_time = time.time()
    logger.info(f"--- Container initialization complete ({end_time - start_time:.2f} seconds). Effective host IP for clients: {final_ip_for_clients} ---")
    return 0 # Indicate success

if __name__ == "__main__":
    sys.exit(main())