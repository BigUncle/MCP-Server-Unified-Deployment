"""MCP Server Configuration Management Module

This module provides functionality for loading and saving MCP server configurations.
"""

import json
import os
import sys

# --- Constants ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_FILE = os.path.join(BASE_DIR, "config", "mcp_servers.json")
SOURCE_CODE_SERVERS_DIR = os.path.join(BASE_DIR, "mcp-servers")


# --- Helper Functions ---


def load_config():
    """Load server configuration and automatically correct paths"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {CONFIG_FILE}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Configuration file {CONFIG_FILE} is not valid JSON.")
        sys.exit(1)

    updated = False
    for server in config.get("servers", []):
        # Only process paths for source_code type servers
        if server.get("type") == "source_code":
            if server.get("repo") and server.get("subdir") is not None:
                repo_name = server["repo"].split("/")[-1].replace(".git", "")
                repo_base_path = os.path.join(SOURCE_CODE_SERVERS_DIR, repo_name)

                if server["subdir"] == ".":
                    expected_path = repo_base_path
                else:
                    expected_path = os.path.join(repo_base_path, server["subdir"])

                # Normalize paths for comparison
                expected_path_norm = os.path.normpath(expected_path).replace("\\", "/")
                current_path_norm = (
                    os.path.normpath(server.get("path", "")).replace("\\", "/")
                    if server.get("path")
                    else ""
                )

                # If the path in the configuration is incorrect or empty, update it to the expected path
                if current_path_norm != expected_path_norm:
                    print(
                        f"Updating server '{server['name']}' path to: {expected_path_norm}"
                    )
                    server["path"] = expected_path_norm
                    updated = True
            elif not server.get("path"):
                print(
                    f"Warning: source_code server '{server['name']}' is missing 'repo'/'subdir' or 'path' configuration."
                )

    # If there are updates, save the configuration
    if updated:
        save_config(config)

    return config


def save_config(config):
    """Save server configuration"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"Configuration updated and saved to {CONFIG_FILE}")
    except IOError:
        print(f"Error: Cannot write to configuration file {CONFIG_FILE}")
