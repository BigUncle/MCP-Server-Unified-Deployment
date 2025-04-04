#!/usr/bin/env python3
"""
Setup virtual environment for MCP Server Unified Deployment Tool

This script uses uv to create a virtual environment and install required dependencies.
uv is a fast Python package manager and virtual environment tool.
"""

import os
import subprocess
import sys

def run_command(command):
    """Run command and print output"""
    print(f"Executing: {command}")
    result = subprocess.run(command, shell=True, check=False)
    if result.returncode != 0:
        print(f"Command execution failed, exit code: {result.returncode}")
        sys.exit(result.returncode)
    return result

def main():
    # Get the parent directory of the script directory (project root directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    # Change to project root directory
    os.chdir(project_dir)
    print(f"Changed to project directory: {project_dir}")

    # Check if uv is installed
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        print("uv is already installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("uv is not installed, installing...")
        run_command("pip install uv")

    # Create virtual environment
    print("\nCreating virtual environment...")
    run_command("uv venv --python=3.12")

    # Display command to activate virtual environment
    venv_activate_cmd = ".venv\\Scripts\\activate" if sys.platform == "win32" else "source .venv/bin/activate"
    print(f"\nPlease use the following command to activate the virtual environment:\n{venv_activate_cmd}")

    # Install dependencies
    print("\nInstalling dependencies...")
    run_command("uv pip install -e .")
    print("\nOr install dependencies using requirements.txt:")
    print("uv pip install -r requirements.txt")

    # Suggest installing mcp-proxy
    print("\nRecommended to install mcp-proxy using pipx:")
    print("pip install pipx")
    print("pipx ensurepath")
    print("pipx install mcp-proxy")

    print("\nEnvironment setup complete! Please follow these steps to continue:")
    print(f"1. Activate virtual environment: {venv_activate_cmd}")
    print("2. Configure MCP server: Edit config/mcp_servers.json file")
    print("3. Start MCP server: python scripts/manage_mcp.py start")
    print("\nFor more information, please refer to the README.md file")

    print("\nEnvironment setup complete!")
    print("Use the following command to activate the virtual environment:")
    if os.name == 'nt':  # Windows
        print(".venv\\Scripts\\activate")
    else:  # Unix/Linux/MacOS
        print("source .venv/bin/activate")

if __name__ == "__main__":
    main()