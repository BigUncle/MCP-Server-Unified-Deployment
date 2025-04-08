#!/usr/bin/env python3

# -*- coding: utf-8 -*-

import json
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil

# Configuration file paths
CONFIG_FILE = Path(__file__).parent.parent / "config" / "mcp_servers.json"
PID_DIR = Path(__file__).parent.parent / "pids"
LOG_DIR = Path(__file__).parent.parent / "logs"

# Ensure directories exist
PID_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


# Load configuration
def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# Save PID to file
def save_pid(name, pid):
    with open(PID_DIR / f"{name}.pid", "w") as f:
        f.write(str(pid))


# Load PID from file
def load_pid(name):
    pid_file = PID_DIR / f"{name}.pid"
    if pid_file.exists():
        with open(pid_file, "r") as f:
            return int(f.read().strip())
    return None


# Remove PID file
def remove_pid_file(name):
    pid_file = PID_DIR / f"{name}.pid"
    if pid_file.exists():
        pid_file.unlink()


# Check if process is running
def is_running(pid):
    try:
        return psutil.pid_exists(pid)
    except psutil.NoSuchProcess:  # Be specific about expected errors
        # PID does not exist, which means it's not running
        return False
    except Exception as e:  # Catch other potential errors during check
        print(f"Error checking PID {pid}: {e}")
        return False  # Assume not running if error occurs


# Check if port is in use
def is_port_in_use(port):
    for conn in psutil.net_connections():
        if conn.laddr.port == port:
            return conn.pid
    return None


# Start server
def start_server(server):
    name = server["name"]

    # Check if already running
    pid = load_pid(name)
    if pid and is_running(pid):
        print(f"Server '{name}' is already running (PID: {pid})")
        return

    # Check if port is already in use
    port = server.get("sse_port", server.get("port"))
    if port:
        existing_pid = is_port_in_use(port)
        if existing_pid:
            print(f"Warning: Port {port} is already in use by process {existing_pid}")

    # Prepare environment variables
    env = os.environ.copy()
    for key, value in server.get("env", {}).items():
        env[key] = value

    # Prepare start command
    if "sse_host" in server and "sse_port" in server:
        print(f"Starting server '{name}' (SSE mode)")
        # SSE mode
        cmd = server["sse_start_command"]
        # Replace placeholders in command
        for key, value in server.items():
            # Always try to replace, and convert value to string to ensure compatibility
            cmd = cmd.replace("{" + key + "}", str(value))
        # Replace environment variable placeholders
        for key, value in server.get("env", {}).items():
            # cmd = cmd.replace("{" + key + "}", value)
            cmd += f" -e {key} {value}"
        # Replace start command
        start_cmd = server["start_command"]
        cmd = cmd.replace("{start_command}", start_cmd)
    else:
        # Non-SSE mode
        cmd = server["start_command"]
        if "port" in server:
            cmd = cmd.replace("{port}", str(server["port"]))

    # Create log file
    log_file = open(LOG_DIR / f"{name}_{time.strftime('%Y%m%d%H%M%S')}.log", "a")

    # Add log header information
    log_file.write(f"=== Service Start {time.ctime()} ===\n")
    log_file.write(f"Execute command: {cmd}\n\n")

    # Print startup information for debugging
    print(f"Starting server '{name}' with command: {cmd}")

    # Start server
    try:
        # Bandit B602: shell=True is a security risk if cmd contains untrusted input.
        print(f"Start command: {cmd}")

        process = subprocess.Popen(cmd, shell=True, env=env, stdout=log_file, stderr=log_file)
        save_pid(name, process.pid)
        print(f"Server '{name}' started (PID: {process.pid})")
    except Exception as e:
        print(f"Failed to start server '{name}': {e}")


# Stop server
def stop_server(server):
    name = server["name"]
    pid = load_pid(name)

    # Check if started by our script
    if pid and is_running(pid):
        try:
            # On Windows, use taskkill to kill process tree
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=False)
            else:
                os.kill(pid, signal.SIGTERM)
                # Give process some time to exit normally
                time.sleep(1)
                if is_running(pid):
                    os.kill(pid, signal.SIGKILL)
            print(f"Server '{name}' stopped (PID: {pid})")
        except Exception as e:
            print(f"Failed to stop server '{name}': {e}")
        finally:
            remove_pid_file(name)
    else:
        # Check if port is in use, try to kill the process using it
        port = server.get("sse_port", server.get("port"))
        if port:
            port_pid = is_port_in_use(port)
            if port_pid:
                try:
                    # On Windows, use taskkill to kill process tree
                    if platform.system() == "Windows":
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(port_pid)], check=False)
                    else:
                        os.kill(port_pid, signal.SIGTERM)
                        # Give process some time to exit normally
                        time.sleep(1)
                        if is_running(port_pid):
                            os.kill(port_pid, signal.SIGKILL)
                    print(f"Stopped server '{name}' running on port {port} (PID: {port_pid})")
                except Exception as e:
                    print(f"Failed to stop process on port {port}: {e}")
            else:
                print(f"Server '{name}' is not running.")
        else:
            print(f"Server '{name}' is not running under this script instance.")


# Restart server
def restart_server(server):
    stop_server(server)
    time.sleep(1)  # Wait one second to ensure complete shutdown
    start_server(server)


# Check server status
def server_status(server):
    name = server["name"]
    enabled = server.get("enabled", True)
    server_type = server.get("type", "unknown")
    host = server.get("host", "localhost")
    port = server.get("sse_port", server.get("port", "N/A"))
    # path = server.get("path", "unknown")
    url = f"http://{host}:{port}/sse"

    # Check PID file
    pid = load_pid(name)
    pid_running = pid and is_running(pid)

    # Check port
    port_pid = None
    if port != "N/A":
        port_pid = is_port_in_use(port)

    # Determine status
    if not enabled:
        status = "Disabled"
        pid_str = "N/A"
    elif port_pid:
        if pid_running and port_pid == pid:
            status = f"Running (port {port} listening)"
            pid_str = str(pid)
        else:
            status = f"Running (port {port} listening)"
            pid_str = "(External start)"
    elif pid_running:
        status = "Running"
        pid_str = str(pid)
    else:
        status = "Stopped"
        pid_str = "N/A"

    return {
        "name": name,
        "enabled": enabled,
        "type": server_type,
        "port": port,
        "status": status,
        "pid": pid_str,
        "url": url,
    }


# Get status of all servers
def get_all_status():
    config = load_config()
    status_list = []
    for server in config["servers"]:
        status_list.append(server_status(server))
    return status_list


# Display status table
def print_status_table():
    status_list = get_all_status()

    # Print header
    print("\n--- MCP Server Status ---")
    headers = ["Name", "Enabled", "Type", "Port", "Status", "PID (This Instance)", "Path"]
    col_widths = [20, 10, 15, 10, 30, 20, 70]

    print(
        "{:<{}} {:<{}} {:<{}} {:<{}} {:<{}} {:<{}} {:<{}}".format(
            headers[0],
            col_widths[0],
            headers[1],
            col_widths[1],
            headers[2],
            col_widths[2],
            headers[3],
            col_widths[3],
            headers[4],
            col_widths[4],
            headers[5],
            col_widths[5],
            headers[6],
            col_widths[6],
        )
    )

    print("-" * 100)

    # Print status for each server
    for status in status_list:
        print(
            "{:<{}} {:<{}} {:<{}} {:<{}} {:<{}} {:<{}} {:<{}}".format(
                status["name"],
                col_widths[0],
                str(status["enabled"]),
                col_widths[1],
                status["type"],
                col_widths[2],
                status["port"],
                col_widths[3],
                status["status"],
                col_widths[4],
                status["pid"],
                col_widths[5],
                status["url"],
                col_widths[6],
            )
        )


# Start all enabled servers
def start_all_servers():
    config = load_config()
    for server in config["servers"]:
        if server.get("enabled", True):
            start_server(server)


# Stop all servers
def stop_all_servers():
    config = load_config()
    for server in config["servers"]:
        stop_server(server)


# Main function
def main():
    if len(sys.argv) < 2:
        print("Usage: python manage_mcp.py <command> [server_name]")
        print("Commands: start, stop, restart, status, daemon")
        return

    command = sys.argv[1]
    server_name = sys.argv[2] if len(sys.argv) > 2 else None

    config = load_config()

    if command == "status":
        print_status_table()
        return

    if command == "start" and not server_name:
        # Start all enabled servers
        start_all_servers()
        # Check if running in daemon mode (Docker container)
        if os.environ.get("MCP_DAEMON_MODE", "false").lower() == "true":
            print("Running in daemon mode, keeping process alive...")
            try:
                # Keep the process running and periodically check server status
                while True:
                    time.sleep(30)  # Reduced check interval to 30 seconds

                    # Added health check logic
                    for server in config["servers"]:
                        if server.get("enabled", True):
                            pid = load_pid(server["name"])
                            port = server.get("sse_port", server.get("port"))

                            # Double check: process exists and port is listening
                            if pid and is_running(pid) and port:
                                if not is_port_in_use(port):
                                    print(f"Service '{server['name']}' process exists but port {port} is not listening, restarting...")
                                    stop_server(server)
                                    start_server(server)
                            elif pid and not is_running(pid):
                                print(f"Service '{server['name']}' abnormally stopped, restarting...")
                                start_server(server)
            except KeyboardInterrupt:
                print("Daemon mode interrupted, stopping all servers...")
                stop_all_servers()
        return

    if command == "daemon":
        # Explicit daemon mode command
        print("Starting all servers in daemon mode...")
        start_all_servers()
        try:
            # Keep the process running and periodically check server status
            while True:
                time.sleep(30)  # Reduced check interval to 30 seconds

                # Added health check logic
                for server in config["servers"]:
                    if server.get("enabled", True):
                        pid = load_pid(server["name"])
                        port = server.get("sse_port", server.get("port"))

                        # Double check: process exists and port is listening
                        if pid and is_running(pid) and port:
                            if not is_port_in_use(port):
                                print(f"Service '{server['name']}' process exists but port {port} is not listening, restarting...")
                                stop_server(server)
                                start_server(server)
                        elif pid and not is_running(pid):
                            print(f"Service '{server['name']}' abnormally stopped, restarting...")
                            start_server(server)
        except KeyboardInterrupt:
            print("Daemon mode interrupted, stopping all servers...")
            stop_all_servers()
        return

    if command == "stop" and not server_name:
        # Stop all servers
        stop_all_servers()
        return

    if not server_name:
        print("Please specify a server name")
        return

    # Find server configuration
    server = None
    for s in config["servers"]:
        if s["name"] == server_name:
            server = s
            break

    if not server:
        print(f"Server '{server_name}' not found")
        return

    # Check if server is enabled
    if not server.get("enabled", True):
        print(f"Server '{server_name}' is disabled. To enable it, please modify the configuration file.")
        return

    # Execute command
    if command == "start":
        start_server(server)
    elif command == "stop":
        stop_server(server)
    elif command == "restart":
        restart_server(server)
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
