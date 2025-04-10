#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCP Configuration Generator
Generate different client format configuration files based on mcp_servers.json
Supported formats:
- Cline
- Roo Code
- Cherry Studio
- GitHub Copilot
"""

import json
import os
import random
import string
import time
from pathlib import Path

# Import functions from config.py to avoid duplication
from mcp_manager.config import load_config, get_server_ip_port

# Configuration file paths
CONFIG_FILE = Path(__file__).parent.parent / "config" / "mcp_servers.json"
CONFIG_OUTPUT_DIR = Path(__file__).parent.parent / "config" / "client_configs"

# Ensure output directory exists
CONFIG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Default configurations for different clients
CLIENT_DEFAULTS = {
    "cline": {
        "timeout": 60,
        "transportType": "sse"
    },
    "roo_code": {},
    "cherry_studio": {
        "isActive": True,
        "description": ""
    },
    "github_copilot": {
        "type": "sse"
    }
}

def generate_random_id(length=20):
    """Generate random ID for Cherry Studio configuration"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def generate_cline_config(servers_config):
    """Generate Cline format configuration file"""
    config = {"mcpServers": {}}
    
    for server in servers_config["servers"]:
        host, port = get_server_ip_port(server)
        url = f"http://{host}:{port}/sse"
        server_config = {
            "disabled": False,
            "timeout": 60,
            "url": url,
            "transportType": "sse"
        }
        if not server.get("enabled", True):
            # If server is disabled, set disabled flag
            server_config.update({
                "disabled": True
            })
            config["mcpServers"][server["name"]] = server_config
            continue
        
        # Add auto-approved function list from server configuration
        if "autoApprove" in server:
            if server["autoApprove"] == "*":
                # For now, just include an empty list for "*" - could be enhanced to fetch all available functions
                server_config["autoApprove"] = []
            else:
                server_config["autoApprove"] = server["autoApprove"]
        
        config["mcpServers"][server["name"]] = server_config
    
    return config

def generate_roo_code_config(servers_config):
    """Generate Roo Code format configuration file"""
    config = {"mcpServers": {}}
    
    for server in servers_config["servers"]:
        if not server.get("enabled", True):
            # If server is disabled, set disabled flag
            config["mcpServers"][server["name"]] = {
                "disabled": True,
                # "alwaysAllow": []
            }
            continue
        
        host, port = get_server_ip_port(server)
        url = f"http://{host}:{port}/sse"
        
        server_config = {
            "url": url
        }
        
        # Add auto-approved function list from server configuration (renamed to alwaysAllow for Roo Code)
        if "autoApprove" in server:
            if server["autoApprove"] == "*":
                # For now, just include an empty list for "*" - could be enhanced to fetch all available functions
                server_config["alwaysAllow"] = []
            else:
                server_config["alwaysAllow"] = server["autoApprove"]
        
        config["mcpServers"][server["name"]] = server_config
    
    return config

def generate_cherry_studio_config(servers_config):
    """Generate Cherry Studio format configuration file"""
    config = {"mcpServers": {}}
    
    # Add an mcp-auto-install entry
    config["mcpServers"]["cPqOEdSHLwBLnukhxTppp"] = {
        "isActive": True,
        "name": "mcp-auto-install",
        "description": "Automatically install MCP services (Beta version)",
        "baseUrl": "",
        "command": "npx",
        "args": ["-y", "@mcpmarket/mcp-auto-install", "connect", "--json"],
        "registryUrl": "https://registry.npmmirror.com",
        "env": {}
    }
    
    for server in servers_config["servers"]:
        server_id = generate_random_id()
        
        # If server is disabled, set isActive to false
        isActive = server.get("enabled", True)
        
        host, port = get_server_ip_port(server)
        url = f"http://{host}:{port}/sse"
        
        server_config = {
            "isActive": isActive,
            "name": server["name"],
            "description": server.get("description", server["name"]),
            "baseUrl": url
        }
        
        config["mcpServers"][server_id] = server_config
    
    return config

def generate_github_copilot_config(servers_config):
    """Generate GitHub Copilot format configuration file"""
    config = {"mcp": {"servers": {}}}
    
    for server in servers_config["servers"]:
        if not server.get("enabled", True):
            continue
        
        host, port = get_server_ip_port(server)
        url = f"http://{host}:{port}/sse"
        
        # Get server type from config, default to "sse" if not specified
        server_type = server.get("transport_type", "sse")
        
        server_config = {
            "type": server_type,
            "url": url
        }
        
        # GitHub Copilot format doesn't include autoApprove field
        # Uncomment this block if autoApprove field in GitHub Copilot was released
        # if "autoApprove" in server:
        #     if server["autoApprove"] == "*":
        #         # For "*", don't include the autoApprove field as this means "allow all"
        #         pass
        #     else:
        #         server_config["autoApprove"] = server["autoApprove"]
        
        config["mcp"]["servers"][server["name"]] = server_config
    
    return config

def save_config_to_file(config, filename):
    """Save configuration to file"""
    file_path = CONFIG_OUTPUT_DIR / filename
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return file_path

def generate_all_configs():
    """Generate all client configuration files"""
    # Load server configuration
    servers_config = load_config()
    if not servers_config:
        print("Failed to load server configuration")
        return None
    
    # Generate different format configurations
    cline_config = generate_cline_config(servers_config)
    roo_code_config = generate_roo_code_config(servers_config)
    cherry_studio_config = generate_cherry_studio_config(servers_config)
    github_copilot_config = generate_github_copilot_config(servers_config)
    
    # Generate filenames with timestamp
    timestamp = time.strftime("%Y%m%d%H%M%S")
    
    # Save configuration files
    cline_path = save_config_to_file(cline_config, f"mcp_cline_{timestamp}.json")
    roo_code_path = save_config_to_file(roo_code_config, f"mcp_roo_code_{timestamp}.json")
    cherry_studio_path = save_config_to_file(cherry_studio_config, f"mcp_cherry_studio_{timestamp}.json")
    github_copilot_path = save_config_to_file(github_copilot_config, f"mcp_github_copilot_{timestamp}.json")
    
    # Also save a copy of the latest configuration (without timestamp)
    latest_cline_path = save_config_to_file(cline_config, "mcp_cline_latest.json")
    latest_roo_code_path = save_config_to_file(roo_code_config, "mcp_roo_code_latest.json")
    latest_cherry_studio_path = save_config_to_file(cherry_studio_config, "mcp_cherry_studio_latest.json")
    latest_github_copilot_path = save_config_to_file(github_copilot_config, "mcp_github_copilot_latest.json")
    
    return {
        "cline": str(cline_path),
        "roo_code": str(roo_code_path),
        "cherry_studio": str(cherry_studio_path),
        "github_copilot": str(github_copilot_path),
        "latest": {
            "cline": str(latest_cline_path),
            "roo_code": str(latest_roo_code_path),
            "cherry_studio": str(latest_cherry_studio_path),
            "github_copilot": str(latest_github_copilot_path)
        }
    }

if __name__ == "__main__":
    """Generate all configuration files when executed from command line"""
    result = generate_all_configs()
    if result:
        print("Client configuration files generation completed:")
        for client_type, path in result.items():
            if client_type != "latest":
                print(f"- {client_type}: {path}")
        print("\nLatest configuration files:")
        for client_type, path in result["latest"].items():
            print(f"- {client_type}: {path}")
    else:
        print("Failed to generate client configuration files")