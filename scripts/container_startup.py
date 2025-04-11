#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Container Startup Script for MCP Server
This script runs during container initialization to:
1. Detect real host IP for external client access
2. Set up appropriate environment variables
3. Generate client configurations with correct IP addresses
4. Ensure MCP servers start correctly
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
import importlib.util

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('container_startup')

# Constants
CONFIG_DIR = Path('/app/config')
CONFIG_FILE = CONFIG_DIR / 'mcp_servers.json'
CLIENT_CONFIGS_DIR = CONFIG_DIR / 'client_configs'
SCRIPTS_DIR = Path('/app/scripts')
HOST_DETECTOR_SCRIPT = SCRIPTS_DIR / 'detect_host_ip.py'

def check_directory_permissions():
    """Verify and fix directory permissions if needed"""
    directories_to_check = [
        CONFIG_DIR,
        CLIENT_CONFIGS_DIR,
        Path('/app/logs'),
        Path('/app/pids')
    ]
    
    for directory in directories_to_check:
        if not directory.exists():
            try:
                logger.info(f"Creating directory: {directory}")
                directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                continue
        
        # Check if directory is writable
        if not os.access(directory, os.W_OK):
            try:
                logger.warning(f"Directory not writable, attempting to fix permissions: {directory}")
                # Try to make the directory writable
                os.chmod(directory, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                
                # Verify if fix worked
                if os.access(directory, os.W_OK):
                    logger.info(f"Successfully fixed permissions for: {directory}")
                else:
                    logger.error(f"Failed to make directory writable: {directory}")
            except Exception as e:
                logger.error(f"Error fixing permissions for {directory}: {e}")

def detect_host_ip():
    """
    Detect the real host IP address using our specialized detection script
    """
    if not HOST_DETECTOR_SCRIPT.exists():
        logger.error(f"Host IP detector script not found at {HOST_DETECTOR_SCRIPT}")
        return None
        
    try:
        # Run the detector script as a subprocess to get the result
        result = subprocess.run(
            [sys.executable, str(HOST_DETECTOR_SCRIPT)],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            # Extract the IP from the output
            for line in result.stdout.splitlines():
                if "Detected host IP:" in line:
                    ip = line.split("Detected host IP:")[1].strip()
                    logger.info(f"Detected real host IP: {ip}")
                    return ip
        
        logger.error(f"Host IP detector failed: {result.stderr}")
        return None
    except Exception as e:
        logger.error(f"Error running host IP detector: {e}")
        return None

def update_environment_variables(host_ip):
    """Update environment variables with the detected host IP"""
    if not host_ip:
        return
        
    # Set both EXTERNAL_HOST and REAL_HOST_IP to the same value
    logger.info(f"Setting EXTERNAL_HOST and REAL_HOST_IP to {host_ip}")
    os.environ['EXTERNAL_HOST'] = host_ip
    os.environ['REAL_HOST_IP'] = host_ip
    os.environ['DETECTED_HOST_IP'] = host_ip
        
    # Write to a file that can be sourced by other processes
    try:
        with open('/tmp/mcp_environment', 'w') as f:
            f.write(f'export EXTERNAL_HOST="{host_ip}"\n')
            f.write(f'export REAL_HOST_IP="{host_ip}"\n')
            f.write(f'export DETECTED_HOST_IP="{host_ip}"\n')
        logger.info("Environment variables saved to /tmp/mcp_environment")
    except Exception as e:
        logger.error(f"Failed to write environment file: {e}")

def generate_client_configs():
    """Generate client configurations with error handling"""
    try:
        logger.info("Generating client configurations")
        # Create the client_configs directory if it doesn't exist
        CLIENT_CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Run the config generator script
        result = subprocess.run(
            [sys.executable, "/app/scripts/integrate_config_generator.py"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to generate client configurations: {result.stderr}")
            return False
            
        logger.info("Client configurations generated successfully")
        return True
    except Exception as e:
        logger.error(f"Error generating client configurations: {e}")
        return False

def check_mcp_config():
    """Check if MCP server configuration file exists and is valid"""
    if not CONFIG_FILE.exists():
        logger.error(f"MCP server configuration file not found: {CONFIG_FILE}")
        logger.info("Please copy the example configuration file and modify it as needed:")
        logger.info(f"cp {CONFIG_FILE.parent / 'mcp_servers.example.json'} {CONFIG_FILE}")
        # Copy example config file if it exists
        example_config = CONFIG_DIR / 'mcp_servers.example.json'
        shutil.copy(example_config, CONFIG_FILE)
        logger.info(f"Copied example configuration to {CONFIG_FILE}")
        
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            
        # Verify basic structure of the config
        if not isinstance(config, dict) or 'servers' not in config:
            logger.error("Invalid MCP server configuration: missing 'servers' section")
            return False
            
        # Check if there are enabled servers
        enabled_servers = [s for s in config.get('servers', []) if s.get('enabled', True)]
        if not enabled_servers:
            logger.warning("No enabled MCP servers found in configuration")
            
        return True
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in MCP server configuration: {CONFIG_FILE}")
        return False
    except Exception as e:
        logger.error(f"Error checking MCP configuration: {e}")
        return False

def main():
    """Main entry point for container initialization"""
    logger.info("Starting MCP Server container initialization")
    
    # Check and fix directory permissions
    check_directory_permissions()
    
    # Check MCP server configuration
    if not check_mcp_config():
        logger.error("MCP server configuration check failed")
        sys.exit(1)
    
    # Detect real host IP
    host_ip = detect_host_ip()
    
    # If detection fails, fall back to environment variables or localhost
    if not host_ip:
        host_ip = os.environ.get('REAL_HOST_IP') or os.environ.get('EXTERNAL_HOST') or 'localhost'
        logger.warning(f"Using fallback host IP: {host_ip}")
    
    # Update environment variables
    update_environment_variables(host_ip)
    
    # Generate client configurations with the correct IP
    success = generate_client_configs()
    if not success:
        logger.warning("Client configuration generation failed")
    
    logger.info(f"Container initialization complete. Using host IP: {host_ip}")
    return 0

if __name__ == "__main__":
    sys.exit(main())