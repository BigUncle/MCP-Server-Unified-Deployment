#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Container Startup Script for MCP Server
This script runs during container initialization to:
1. Verify essential directories exist and have correct permissions.
2. Verify essential tools (installed in Dockerfile) are accessible.
3. Check and potentially copy the default MCP server configuration.
4. Detect the real host IP address for external client access.
5. Set up appropriate environment variables based on detected IP.
6. Generate client configurations with correct IP addresses.
"""

import os
import socket
import sys
import json
from pathlib import Path
import subprocess
import time
import logging
import stat
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger('container_startup')

# Constants - Define paths relative to the application root (/app)
APP_DIR = Path('/app')
CONFIG_DIR = APP_DIR / 'config'
LOGS_DIR = APP_DIR / 'logs'
PIDS_DIR = APP_DIR / 'pids'
MCP_DATA_DIR = APP_DIR / 'mcp-data'
MCP_SERVERS_DIR = APP_DIR / 'mcp-servers'
CLIENT_CONFIGS_DIR = CONFIG_DIR / 'client_configs'

CONFIG_FILE = CONFIG_DIR / 'mcp_servers.json'
EXAMPLE_CONFIG_FILE = CONFIG_DIR / 'mcp_servers.example.json'

SCRIPTS_DIR = APP_DIR / 'scripts'
HOST_DETECTOR_SCRIPT = SCRIPTS_DIR / 'detect_host_ip.py'

# --- Helper Functions ---

def ensure_directory(dir_path: Path):
    """Ensure directory exists and is writable by the current user."""
    try:
        if not dir_path.exists():
            logger.info(f"Creating directory: {dir_path}")
            # Create directory with default permissions (should be usable by user mcp)
            dir_path.mkdir(parents=True, exist_ok=True)
        else:
            logger.debug(f"Directory already exists: {dir_path}")

        # Check writability for the current user
        if not os.access(dir_path, os.W_OK):
            logger.error(f"FATAL: Directory {dir_path} is not writable by user {os.geteuid()}. Check volume permissions on the host.")
            # Attempting chmod might fail if it's a volume mount issue
            try:
                current_mode = dir_path.stat().st_mode
                # Add write permission for the owner (user mcp)
                os.chmod(dir_path, current_mode | stat.S_IWUSR)
                if os.access(dir_path, os.W_OK):
                    logger.info(f"Added write permission for user to {dir_path}.")
                else:
                     # This is likely a host volume permission issue
                     return False
            except Exception as e:
                logger.error(f"Error attempting to fix permissions for {dir_path}: {e}")
                return False
        return True

    except Exception as e:
        logger.error(f"Failed to ensure directory {dir_path}: {e}")
        return False

def check_essential_tools():
    """Verify that essential command-line tools (expected in PATH) are available."""
    # Tools expected to be installed in the Docker image for user 'mcp'
    tools = ["python", "node", "npm", "npx", "git", "uv", "pipx", "mcp-proxy"]
    all_found = True
    logger.info("Checking for essential tools in PATH...")
    for tool in tools:
        tool_path = shutil.which(tool)
        if tool_path:
            logger.info(f"  [OK] Found: {tool} at {tool_path}")
        else:
            logger.error(f"  [MISSING] Tool not found in PATH: {tool}")
            all_found = False

    if not all_found:
         logger.critical("One or more essential tools are missing from PATH. Check Dockerfile installation and PATH environment variable.")
         # Consider exiting if critical tools like python or mcp-proxy are missing
         # sys.exit(1)
    return all_found

def check_mcp_config():
    """Check if MCP server configuration file exists and is valid JSON."""
    logger.info(f"Checking MCP configuration file: {CONFIG_FILE}...")
    if not CONFIG_FILE.exists():
        logger.warning(f"Configuration file not found.")
        if EXAMPLE_CONFIG_FILE.exists():
            try:
                logger.info(f"Copying example configuration from {EXAMPLE_CONFIG_FILE} to {CONFIG_FILE}")
                shutil.copy(EXAMPLE_CONFIG_FILE, CONFIG_FILE)
                logger.info("Example configuration copied. Please review and customize it as needed.")
                # Re-check existence after copy
                if not CONFIG_FILE.exists():
                     logger.error("Failed to create config file from example.")
                     return False
            except Exception as e:
                logger.error(f"Failed to copy example configuration: {e}")
                return False
        else:
             logger.error(f"No configuration file found at {CONFIG_FILE}, and no example file available at {EXAMPLE_CONFIG_FILE}.")
             return False

    # Now check the content of the config file (whether copied or pre-existing)
    try:
        with CONFIG_FILE.open('r', encoding='utf-8') as f:
            config = json.load(f)

        # Basic structure validation
        if not isinstance(config, dict) or 'servers' not in config:
            logger.error(f"Invalid format in {CONFIG_FILE}: Must be a JSON object with a 'servers' key (list).")
            return False
        if not isinstance(config['servers'], list):
            logger.error(f"Invalid format in {CONFIG_FILE}: 'servers' key must be a JSON list.")
            return False

        # Check if there are any enabled servers
        enabled_servers = [s for s in config.get('servers', []) if s.get('enabled', True)]
        if not enabled_servers:
            logger.warning(f"No enabled MCP servers found in configuration: {CONFIG_FILE}")
        else:
            logger.info(f"Found {len(enabled_servers)} enabled MCP servers in configuration.")

        logger.info(f"MCP configuration file {CONFIG_FILE} is valid.")
        return True
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file {CONFIG_FILE}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error reading or parsing configuration file {CONFIG_FILE}: {e}")
        return False

def detect_host_ip():
    """Detect the real host IP address using the detection script or fallbacks."""
    logger.info("Attempting to detect host IP...")
    detected_ip = None

    if HOST_DETECTOR_SCRIPT.exists():
        logger.info(f"Running host IP detector script: {HOST_DETECTOR_SCRIPT}")
        try:
            result = subprocess.run(
                [sys.executable, str(HOST_DETECTOR_SCRIPT)],
                capture_output=True, text=True, check=False, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "Detected host IP:" in line:
                        ip = line.split("Detected host IP:")[1].strip()
                        try:
                            socket.inet_aton(ip) # Basic IPv4 check
                            logger.info(f"Detected host IP via script: {ip}")
                            detected_ip = ip
                            break
                        except socket.error:
                            logger.warning(f"IP detected by script is invalid: {ip}")
                if not detected_ip:
                     logger.warning(f"Host IP detector script ran but did not output a valid IP. Output:\n{result.stdout}\n{result.stderr}")
            else:
                logger.error(f"Host IP detector script failed (exit code {result.returncode}):\n{result.stderr}")
        except subprocess.TimeoutExpired:
            logger.error("Host IP detector script timed out.")
        except Exception as e:
            logger.error(f"Error running host IP detector script: {e}")
    else:
        logger.warning(f"Host IP detector script not found at {HOST_DETECTOR_SCRIPT}. Using fallback methods.")

    # Fallback methods if script fails or doesn't exist
    if not detected_ip:
        logger.info("Attempting fallback IP detection methods...")
        try:
            # Method 1: Check REAL_HOST_IP env var (set externally, highest priority fallback)
            env_ip = os.environ.get('REAL_HOST_IP')
            if env_ip:
                 logger.info(f"Using IP from REAL_HOST_IP environment variable: {env_ip}")
                 return env_ip # Trust externally set IP

            # Method 2: Check EXTERNAL_HOST env var
            env_ip = os.environ.get('EXTERNAL_HOST')
            if env_ip:
                try:
                     socket.inet_aton(env_ip)
                     logger.info(f"Using IP from EXTERNAL_HOST environment variable: {env_ip}")
                     return env_ip
                except socket.error:
                     logger.warning(f"EXTERNAL_HOST value '{env_ip}' is not a valid IP. Ignoring.")

            # Method 3: Try default gateway (often the host in bridge network)
            result = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                parts = result.stdout.split()
                if 'via' in parts:
                    gateway_ip = parts[parts.index('via') + 1]
                    try:
                        socket.inet_aton(gateway_ip)
                        logger.info(f"Using default gateway IP as potential host IP: {gateway_ip}")
                        return gateway_ip
                    except socket.error:
                        logger.debug(f"Default gateway value '{gateway_ip}' is not a valid IP.")

            # Method 4: Use `hostname -I` (may give multiple IPs)
            result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                 ips = result.stdout.strip().split()
                 if ips:
                      for ip in ips: # Prefer non-internal IPs if possible
                          if not ip.startswith('172.') and not ip.startswith('127.'):
                              try:
                                  socket.inet_aton(ip)
                                  logger.info(f"Using first non-internal IP from 'hostname -I': {ip}")
                                  return ip
                              except socket.error: continue
                      # If only internal IPs found, return the first valid one
                      for ip in ips:
                           try:
                               socket.inet_aton(ip)
                               logger.info(f"Using first valid IP from 'hostname -I': {ip}")
                               return ip
                           except socket.error: continue
        except Exception as e:
             logger.warning(f"Internal host IP detection methods failed: {e}")

    # Final fallback if no IP found
    if not detected_ip:
         logger.error("Could not determine a suitable host IP. Falling back to 'localhost'. External access will likely fail.")
         return 'localhost'
    else:
         return detected_ip

def update_environment_variables(host_ip):
    """Update environment variables REAL_HOST_IP and EXTERNAL_HOST."""
    if not host_ip:
        logger.error("Cannot update environment variables: No host IP provided.")
        return

    # Always set REAL_HOST_IP and EXTERNAL_HOST based on the final determined IP
    logger.info(f"Setting container environment: REAL_HOST_IP={host_ip}, EXTERNAL_HOST={host_ip}")
    os.environ['REAL_HOST_IP'] = host_ip
    os.environ['EXTERNAL_HOST'] = host_ip

    # Optionally write to a file, though less necessary now
    try:
        env_file = Path('/tmp/mcp_environment')
        with env_file.open('w') as f:
            f.write(f'export REAL_HOST_IP="{host_ip}"\n')
            f.write(f'export EXTERNAL_HOST="{host_ip}"\n')
        logger.debug(f"Environment variables also saved to {env_file}")
    except Exception as e:
        logger.warning(f"Failed to write environment file {env_file}: {e}")

def generate_client_configs():
    """Generate client configurations using the dedicated script."""
    config_generator_script = SCRIPTS_DIR / "integrate_config_generator.py"
    logger.info(f"Attempting to generate client configurations using {config_generator_script}...")

    if not config_generator_script.exists():
        logger.error(f"Client config generator script not found.")
        return False

    try:
        # Ensure output directory exists and is writable
        if not ensure_directory(CLIENT_CONFIGS_DIR):
             logger.error(f"Cannot generate client configs: Output directory {CLIENT_CONFIGS_DIR} is not writable.")
             return False

        # Run the config generator script
        result = subprocess.run(
            [sys.executable, str(config_generator_script)],
            capture_output=True, text=True, check=False, timeout=30
        )

        if result.returncode != 0:
            logger.error(f"Client configuration generator script failed (exit code {result.returncode}):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
            return False

        logger.info("Client configurations generated successfully.")
        logger.debug(f"Generator output:\n{result.stdout}")
        return True
    except subprocess.TimeoutExpired:
        logger.error("Client config generator script timed out.")
        return False
    except Exception as e:
        logger.error(f"Error running client config generator: {e}")
        return False

# --- Main Execution ---

def main():
    """Main container initialization sequence."""
    start_time = time.time()
    logger.info("--- Starting MCP Server Container Initialization ---")

    # 0. Log basic environment info
    uid = os.geteuid()
    gid = os.getegid()
    home = os.environ.get('HOME', '/root') # Default to /root if HOME not set
    logger.info(f"Running initialization as UID={uid}, GID={gid}, HOME={home}")
    logger.info(f"Current PATH: {os.environ.get('PATH', 'Not Set')}")

    # 1. Ensure essential directories exist and are writable
    logger.info("Step 1: Ensuring essential directories...")
    dirs_ok = all([
        ensure_directory(CONFIG_DIR),
        ensure_directory(LOGS_DIR),
        ensure_directory(PIDS_DIR),
        ensure_directory(CLIENT_CONFIGS_DIR),
        ensure_directory(MCP_DATA_DIR),
        ensure_directory(MCP_SERVERS_DIR),
    ])
    if not dirs_ok:
         logger.critical("One or more essential directories are not writable. Aborting initialization.")
         return 1 # Exit if directories are not usable

    # 2. Check for essential tools
    logger.info("Step 2: Checking for essential tools...")
    tools_ok = check_essential_tools()
    if not tools_ok:
        # Decide whether to proceed if tools are missing
        logger.warning("Essential tool check failed. Continuing, but functionality may be impaired.")
        # return 1 # Or exit

    # 3. Check MCP server configuration file
    logger.info("Step 3: Checking MCP server configuration...")
    config_ok = check_mcp_config()
    if not config_ok:
        logger.critical("MCP server configuration check failed. Aborting initialization.")
        return 1 # Exit if config is bad

    # 4. Detect host IP
    logger.info("Step 4: Detecting host IP...")
    host_ip = detect_host_ip() # Handles fallbacks internally

    # 5. Update environment variables
    logger.info("Step 5: Updating environment variables...")
    update_environment_variables(host_ip)
    final_ip_for_clients = os.environ.get('REAL_HOST_IP', 'Not Set')

    # 6. Generate client configurations
    logger.info("Step 6: Generating client configurations...")
    generate_client_configs() # Errors logged within the function

    end_time = time.time()
    logger.info(f"--- Container initialization complete ({end_time - start_time:.2f} seconds). Effective host IP for clients: {final_ip_for_clients} ---")
    return 0 # Indicate success to the entrypoint script

if __name__ == "__main__":
    sys.exit(main())