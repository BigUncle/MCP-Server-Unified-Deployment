#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCP Configuration Generator
Generate different client format configuration files based on mcp_servers.json
Supported formats:
- Cline
- Roo Code
- Cherry Studio
"""

import json
import os
import random
import string
import time
from pathlib import Path

# Import config module from parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp_manager.config import load_config

# Configuration file output directory
CONFIG_OUTPUT_DIR = Path(__file__).parent.parent / "config" / "client_configs"

# Ensure output directory exists
CONFIG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Default configurations for different clients
CLIENT_DEFAULTS = {
    "cline": {
        "timeout": 60,
        "transportType": "sse",
        "autoApprove": []
    },
    "roo_code": {
        "alwaysAllow": []
    },
    "cherry_studio": {
        "isActive": True,
        "description": ""
    }
}

# Default function authorization lists for different servers
DEFAULT_ALLOWED_FUNCTIONS = {
    "filesystem": [
        "read_file", "read_multiple_files", "write_file", "edit_file",
        "create_directory", "list_directory", "directory_tree", "move_file",
        "search_files", "get_file_info", "list_allowed_directories"
    ],
    "github": [
        "create_or_update_file", "search_repositories", "create_repository",
        "get_file_contents", "push_files", "create_issue", "create_pull_request",
        "fork_repository", "create_branch", "list_commits", "list_issues", 
        "update_issue", "add_issue_comment", "search_code", "search_issues",
        "search_users", "get_issue", "get_pull_request", "list_pull_requests",
        "create_pull_request_review", "merge_pull_request", "get_pull_request_files",
        "get_pull_request_status", "update_pull_request_branch", "get_pull_request_comments",
        "get_pull_request_reviews"
    ],
    "firecrawl": [
        "firecrawl_scrape", "firecrawl_map", "firecrawl_crawl", "firecrawl_batch_scrape",
        "firecrawl_check_batch_status", "firecrawl_check_crawl_status", "firecrawl_search",
        "firecrawl_extract", "firecrawl_deep_research", "firecrawl_generate_llmstxt"
    ],
    "duckduckgo": [
        "search", "fetch_content"
    ],
    "amap": [
        "search", "fetch_content", "maps_regeocode", "maps_geo", "maps_ip_location",
        "maps_weather", "maps_search_detail", "maps_bicycling", "maps_direction_walking",
        "maps_direction_driving", "maps_direction_transit_integrated", "maps_distance",
        "maps_text_search", "maps_around_search"
    ]
}

def generate_random_id(length=20):
    """Generate random ID for Cherry Studio configuration"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_server_ip_port(server_config):
    """Extract IP and port from server configuration"""
    host = server_config.get("sse_host", "127.0.0.1")
    # If sse_host is 0.0.0.0, use 127.0.0.1 as client connection address
    if host == "0.0.0.0":
        host = "127.0.0.1"
    port = server_config.get("sse_port", "3000")
    return host, port

def generate_cline_config(servers_config):
    """Generate Cline format configuration file"""
    config = {"mcpServers": {}}
    
    for server in servers_config["servers"]:
        if not server.get("enabled", True):
            # If server is disabled, set disabled flag
            config["mcpServers"][server["name"]] = {
                "disabled": True
            }
            continue
        
        host, port = get_server_ip_port(server)
        url = f"http://{host}:{port}/sse"
        
        server_config = {
            "timeout": 60,
            "url": url,
            "transportType": "sse"
        }
        
        # Add auto-approved function list
        if server["name"] in DEFAULT_ALLOWED_FUNCTIONS:
            server_config["autoApprove"] = DEFAULT_ALLOWED_FUNCTIONS[server["name"]]
        
        config["mcpServers"][server["name"]] = server_config
    
    return config

def generate_roo_code_config(servers_config):
    """Generate Roo Code format configuration file"""
    config = {"mcpServers": {}}
    
    for server in servers_config["servers"]:
        if not server.get("enabled", True):
            # If server is disabled, set disabled flag
            config["mcpServers"][server["name"]] = {
                "url": "",
                "disabled": True,
                "alwaysAllow": []
            }
            continue
        
        host, port = get_server_ip_port(server)
        url = f"http://{host}:{port}/sse"
        
        server_config = {
            "url": url
        }
        
        # Add auto-approved function list, called alwaysAllow in Roo Code
        if server["name"] in DEFAULT_ALLOWED_FUNCTIONS:
            server_config["alwaysAllow"] = DEFAULT_ALLOWED_FUNCTIONS[server["name"]]
        
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
    
    # Generate different format configurations
    cline_config = generate_cline_config(servers_config)
    roo_code_config = generate_roo_code_config(servers_config)
    cherry_studio_config = generate_cherry_studio_config(servers_config)
    
    # Generate filenames with timestamp
    timestamp = time.strftime("%Y%m%d%H%M%S")
    
    # Save configuration files
    cline_path = save_config_to_file(cline_config, f"mcp_cline_{timestamp}.json")
    roo_code_path = save_config_to_file(roo_code_config, f"mcp_roo_code_{timestamp}.json")
    cherry_studio_path = save_config_to_file(cherry_studio_config, f"mcp_cherry_studio_{timestamp}.json")
    
    # Also save a copy of the latest configuration (without timestamp)
    latest_cline_path = save_config_to_file(cline_config, "mcp_cline_latest.json")
    latest_roo_code_path = save_config_to_file(roo_code_config, "mcp_roo_code_latest.json")
    latest_cherry_studio_path = save_config_to_file(cherry_studio_config, "mcp_cherry_studio_latest.json")
    
    return {
        "cline": str(cline_path),
        "roo_code": str(roo_code_path),
        "cherry_studio": str(cherry_studio_path),
        "latest": {
            "cline": str(latest_cline_path),
            "roo_code": str(latest_roo_code_path),
            "cherry_studio": str(latest_cherry_studio_path)
        }
    }

if __name__ == "__main__":
    """Generate all configuration files when executed from command line"""
    result = generate_all_configs()
    print("Client configuration files generation completed:")
    for client_type, path in result.items():
        if client_type != "latest":
            print(f"- {client_type}: {path}")
