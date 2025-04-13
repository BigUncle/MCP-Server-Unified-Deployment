#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCP Server Management Script (YAML Version with CORRECT mcp-proxy integration)
Manages starting (via mcp-proxy), stopping, restarting, and checking status
of MCP services defined in mcp_servers.yaml, using the official mcp-proxy syntax.
"""

import yaml
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path
import psutil
import logging
import shlex # Needed to correctly split the start_command string

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('manage_mcp')

# Configuration file paths
APP_DIR = Path(__file__).parent.parent
CONFIG_FILE = APP_DIR / "config" / "mcp_servers.yaml"
PID_DIR = APP_DIR / "pids"
LOG_DIR = APP_DIR / "logs"
MCP_SERVERS_DIR = APP_DIR.parent / "mcp-servers" # Define base dir for server code/scripts

# Ensure directories exist
PID_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
MCP_SERVERS_DIR.mkdir(exist_ok=True) # Ensure base server dir exists

# --- Config Loading (ensure it handles potential errors gracefully) ---
def load_config():
    """Loads the mcp_servers.yaml configuration."""
    if not CONFIG_FILE.exists():
        logger.error(f"Configuration file not found: {CONFIG_FILE}")
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            if config is None:
                 logger.warning(f"Configuration file {CONFIG_FILE} is empty.")
                 return {'servers': []}
            if not isinstance(config, dict) or 'servers' not in config or not isinstance(config['servers'], list):
                 logger.error(f"Invalid YAML structure in {CONFIG_FILE}. Expected a dict with a 'servers' list.")
                 return None
            return config
    except yaml.YAMLError as e:
        logger.error(f"Error decoding YAML from {CONFIG_FILE}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading configuration file {CONFIG_FILE}: {e}")
        return None

# --- PID and Process Utilities (save_pid, load_pid, remove_pid_file, is_running, is_port_in_use remain the same) ---
def save_pid(name, pid):
    try:
        with open(PID_DIR / f"{name}.pid", "w") as f: f.write(str(pid))
    except Exception as e: logger.error(f"Failed to save PID for {name}: {e}")

def load_pid(name):
    pid_file = PID_DIR / f"{name}.pid"
    if pid_file.exists():
        try:
            with open(pid_file, "r") as f: return int(f.read().strip())
        except Exception as e: logger.error(f"Failed to load PID for {name}: {e}")
    return None

def remove_pid_file(name):
    pid_file = PID_DIR / f"{name}.pid"
    if pid_file.exists():
        try: pid_file.unlink()
        except Exception as e: logger.error(f"Failed to remove PID file for {name}: {e}")

def is_running(pid):
    if pid is None: return False
    try: return psutil.pid_exists(pid)
    except Exception: return False

def is_port_in_use(port):
    if port is None: return None
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port:
                # Check if listening on 0.0.0.0 or specific interface relevant to container
                # For simplicity, just check port number for now
                return conn.pid if conn.pid else -1 # Used by unknown/system
        return None
    except psutil.AccessDenied:
        logger.warning(f"Access denied when checking port {port}. Assuming not in use by managed process.")
        return None
    except Exception as e:
        logger.debug(f"Error checking port {port}: {e}")
        return None

# --- Server Management Functions ---

def start_server(server):
    """Starts a single MCP server by running mcp-proxy according to official syntax."""
    name = server.get("name")
    if not name: logger.error("Server config missing 'name'."); return

    internal_port = server.get("internal_port")
    if not internal_port: logger.error(f"Server '{name}' missing 'internal_port'."); return

    # This is the ORIGINAL command string to be executed by mcp-proxy
    original_start_command_str = server.get("start_command")
    if not original_start_command_str: logger.error(f"Server '{name}' missing 'start_command'."); return

    # Get proxy settings from YAML
    # Default to 0.0.0.0 for host inside container, allowing Nginx connection
    proxy_listen_host = server.get("proxy_listen_host", "0.0.0.0")
    proxy_allow_origin = server.get("allow_origin", "*") # Get from correct field
    server_env = server.get("env", {}) # Environment vars for the child process

    # --- Check if already running ---
    pid = load_pid(name)
    if pid and is_running(pid):
        logger.info(f"Server '{name}' (mcp-proxy) is already running (PID: {pid}). Verifying port...")
        port_pid = is_port_in_use(internal_port)
        if port_pid == pid:
             logger.info(f"Port {internal_port} confirmed listening by mcp-proxy PID {pid}.")
             return # Already running correctly
        elif port_pid is not None:
             logger.warning(f"Server '{name}' (PID {pid}) is running, but port {internal_port} is used by PID {port_pid}. Check for conflicts.")
             # Optionally stop the existing process if it's ours but port is wrong? Risky.
        else:
             logger.warning(f"Server '{name}' (PID {pid}) is running, but port {internal_port} is not listening. Process might be stuck. Attempting restart.")
             stop_server(server) # Stop the potentially defunct process first
             time.sleep(1)
    elif pid and not is_running(pid):
         logger.warning(f"Found stale PID file for server '{name}' (PID {pid}). Removing it.")
         remove_pid_file(name)

    # --- Check if port is already in use by another process ---
    port_pid = is_port_in_use(internal_port)
    if port_pid is not None:
        logger.error(f"Cannot start server '{name}': Internal port {internal_port} is already in use by PID {port_pid}.")
        return

    # --- Parse the original start command string ---
    try:
        # Use shlex.split to handle spaces and quotes correctly in the command string
        original_command_parts = shlex.split(original_start_command_str)
        if not original_command_parts:
            logger.error(f"Server '{name}' has an empty 'start_command'.")
            return
        original_cmd = original_command_parts[0]
        original_args = original_command_parts[1:]
    except ValueError as e:
        logger.error(f"Error parsing 'start_command' for server '{name}': {e}. Command: '{original_start_command_str}'")
        return

    # --- Construct the mcp-proxy command LIST (for shell=False) ---
    mcp_proxy_command_list = [
        "mcp-proxy",
        "--sse-host", str(proxy_listen_host),
        "--sse-port", str(internal_port),
        "--allow-origin", str(proxy_allow_origin), # Pass as single string
    ]

    # Add environment variables using -e KEY VALUE for the child process
    for key, value in server_env.items():
        mcp_proxy_command_list.extend(["-e", str(key), str(value)])

    # Add the original command and its arguments
    mcp_proxy_command_list.append(original_cmd)
    mcp_proxy_command_list.extend(original_args)

    # --- Determine working directory ---
    cwd = None
    # Assume servers needing specific CWD are located under MCP_SERVERS_DIR/<name>
    server_specific_dir = MCP_SERVERS_DIR / name
    if server_specific_dir.is_dir():
        cwd = str(server_specific_dir)
        logger.info(f"Setting working directory for '{name}' to: {cwd}")
    else:
        # Log if expected dir doesn't exist, but proceed with default CWD
        logger.debug(f"Server directory '{server_specific_dir}' not found for '{name}'. Using default CWD.")
        # Fallback to APP_DIR or None (which defaults to Popen's default)
        # cwd = str(APP_DIR) # Or leave as None

    # --- Prepare environment for mcp-proxy itself ---
    # Usually just inherit the current environment.
    # Do NOT add server_env here; it's passed via '-e' for the child.
    process_env = os.environ.copy()

    # --- Create log file ---
    log_filename = LOG_DIR / f"{name}_{time.strftime('%Y%m%d%H%M%S')}.log"
    try:
        # Use 'w' to overwrite/create fresh log on each start attempt
        log_file = open(log_filename, "w", encoding='utf-8')
        log_file.write(f"=== Service Start (via mcp-proxy): {time.ctime()} ===\n")
        log_file.write(f"Working Directory: {cwd or os.getcwd()}\n")
        # Log the command as a list for clarity
        log_file.write(f"Executing Proxy Command List: {mcp_proxy_command_list}\n")
        log_file.write(f"  (Original Command String: {original_start_command_str})\n")
        log_file.write(f"Child Environment Additions via '-e': {server_env}\n")
        log_file.write("-" * 20 + "\n\n")
        log_file.flush()
    except Exception as e:
        logger.error(f"Failed to open log file {log_filename} for server '{name}': {e}")
        return

    logger.info(f"Starting server '{name}' via mcp-proxy...")
    # Log the command list being executed
    logger.info(f"  Command List: {' '.join(shlex.quote(str(p)) for p in mcp_proxy_command_list)}") # Log quoted string for readability
    logger.info(f"  Log File: {log_filename}")
    if cwd: logger.info(f"  Working Dir: {cwd}")

    # --- Start mcp-proxy process ---
    try:
        process = subprocess.Popen(
            mcp_proxy_command_list, # Pass the list of arguments
            shell=False,            # IMPORTANT: Use shell=False with list arguments
            env=process_env,        # Environment for mcp-proxy itself
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            # preexec_fn=os.setsid # Optional: Run in new session on Unix-like systems if needed
            close_fds=(os.name != 'nt')
        )
        save_pid(name, process.pid) # Save the PID of the mcp-proxy process
        logger.info(f"Server '{name}' (mcp-proxy) started successfully (PID: {process.pid}).")
    except FileNotFoundError:
         logger.error(f"Failed to start server '{name}': 'mcp-proxy' command not found. Is it installed and in PATH?")
         log_file.write("\n\n!!! FAILED TO START PROXY: 'mcp-proxy' not found !!!\n")
         log_file.close()
    except Exception as e:
        logger.error(f"Failed to start server '{name}' via mcp-proxy: {e}")
        log_file.write(f"\n\n!!! FAILED TO START PROXY: {e} !!!\n")
        log_file.close()


# --- stop_server, restart_server, server_status, print_status_table ---
# --- start_all_servers, stop_all_servers, run_daemon, main ---
# These functions should generally work as before, as they rely on managing
# the PID saved by start_server (which is the mcp-proxy PID) and checking
# the internal_port. The status display might benefit from minor text adjustments
# to clarify it's the proxy being monitored.

def stop_server(server):
    """Stops a single MCP server (the mcp-proxy process)."""
    name = server.get("name")
    if not name: logger.error("Server config missing 'name'."); return

    pid = load_pid(name) # Get PID of the mcp-proxy process
    if pid and is_running(pid):
        logger.info(f"Stopping server '{name}' (mcp-proxy PID: {pid})...")
        try:
            process = psutil.Process(pid)
            # Terminate children first (the actual service process started by mcp-proxy)
            children = process.children(recursive=True)
            for child in children:
                try:
                    logger.debug(f"  Terminating child process {child.pid}...")
                    child.terminate()
                except psutil.NoSuchProcess: pass
                except Exception as e: logger.warning(f"  Failed to terminate child {child.pid}: {e}")

            gone, alive = psutil.wait_procs(children, timeout=3)
            for child in alive:
                try:
                    logger.warning(f"  Force killing child process {child.pid}...")
                    child.kill()
                except psutil.NoSuchProcess: pass
                except Exception as e: logger.warning(f"  Failed to kill child {child.pid}: {e}")

            # Terminate the main mcp-proxy process
            logger.debug(f"  Terminating mcp-proxy process {pid}...")
            process.terminate()
            try:
                process.wait(timeout=5)
                logger.info(f"Server '{name}' (mcp-proxy PID: {pid}) stopped gracefully.")
            except psutil.TimeoutExpired:
                logger.warning(f"Server '{name}' (mcp-proxy PID: {pid}) did not stop gracefully, force killing...")
                process.kill()
                process.wait(timeout=2)
                logger.info(f"Server '{name}' (mcp-proxy PID: {pid}) forcibly stopped.")

        except psutil.NoSuchProcess:
            logger.info(f"Server '{name}' (mcp-proxy PID: {pid}) was already stopped.")
        except Exception as e:
            logger.error(f"Failed to stop server '{name}' (mcp-proxy PID: {pid}): {e}")
            # Fallback kill attempt
            try:
                 if is_running(pid): psutil.Process(pid).kill(); logger.info(f"Server '{name}' (PID: {pid}) forcibly stopped after error.")
            except Exception as kill_err: logger.error(f"Failed to force kill server '{name}' after error: {kill_err}")
        finally:
            remove_pid_file(name) # Clean up PID file
    elif pid and not is_running(pid):
        logger.info(f"Server '{name}' (mcp-proxy PID: {pid}) was not running. Removing stale PID file.")
        remove_pid_file(name)
    else:
        logger.info(f"Server '{name}' is not running (no PID file found).")

def restart_server(server):
    """Restarts a single MCP server (via mcp-proxy)."""
    name = server.get("name", "Unknown")
    logger.info(f"Restarting server '{name}' (via mcp-proxy)...")
    stop_server(server)
    time.sleep(2) # Give resources time to release
    start_server(server)

def server_status(server):
    """Gets the status of a single server (mcp-proxy)."""
    name = server.get("name", "N/A")
    enabled = server.get("enabled", False)
    stype = server.get("type", "unknown")
    internal_port = server.get("internal_port")
    original_cmd_str = server.get("start_command", "N/A") # For display maybe

    # Client-facing URL (via Nginx) - Calculation remains the same
    host_ip = os.environ.get('REAL_HOST_IP', 'localhost')
    nginx_port = os.environ.get('NGINX_HOST_PORT', '23000')
    client_url = f"http://{host_ip}:{nginx_port}/{name}/sse/" if enabled else "N/A (Disabled)"

    status_str = "Unknown"
    pid_str = "N/A"

    if not enabled:
        status_str = "Disabled"
    else:
        pid = load_pid(name) # PID of mcp-proxy
        pid_running = pid and is_running(pid)
        port_pid = is_port_in_use(internal_port) if internal_port else None

        if pid_running:
            pid_str = str(pid)
            if port_pid == pid:
                status_str = f"Running (Proxy Port {internal_port} OK)"
            elif port_pid is not None and port_pid != pid:
                status_str = f"Running (Proxy Port Conflict: {internal_port} used by PID {port_pid})"
            elif internal_port and port_pid is None:
                 status_str = f"Running (Proxy Port {internal_port} Not Listening?)"
            else: # No internal port defined or check failed/denied
                 status_str = "Running (Proxy Port status unknown)"
        elif port_pid is not None: # Not running by our PID, but port is used
             pid_str = f"Ext ({port_pid})" if port_pid != -1 else "Ext (Unknown PID)"
             status_str = f"Stopped (Proxy Port {internal_port} In Use Externally)"
        else: # Not running, port free
             status_str = "Stopped"
             if pid: # Stale PID file?
                  status_str = "Stopped (Stale Proxy PID?)"
                  remove_pid_file(name) # Clean up

    return {
        "name": name,
        "enabled": enabled,
        "type": stype,
        "internal_port": internal_port or "N/A",
        "status": status_str,
        "pid": pid_str, # This is the PID of mcp-proxy
        "client_url": client_url,
        # "original_command": original_cmd_str # Optional: add to status output if desired
    }

def print_status_table():
    """Prints the status of all configured servers in a table."""
    config = load_config()
    if config is None: return

    status_list = [server_status(s) for s in config.get("servers", [])]

    if not status_list:
        logger.info("No servers defined in the configuration.")
        return

    logger.info("\n--- MCP Server Status (via mcp-proxy) ---")
    headers = ["Name", "Enabled", "Type", "Proxy Port", "Status", "Proxy PID", "Client URL"]
    # Adjust widths as needed
    col_widths = [20, 8, 12, 12, 35, 18, 60]

    header_line = " | ".join(f"{h:<{w}}" for h, w in zip(headers, col_widths))
    logger.info(header_line)
    logger.info("-" * len(header_line))

    for status in status_list:
        row_data = [
            status["name"],
            str(status["enabled"]),
            status["type"],
            str(status["internal_port"]),
            status["status"],
            status["pid"],
            status["client_url"],
        ]
        # Truncate long URLs if necessary
        row_data[6] = (row_data[6][:col_widths[6]-3] + '...') if len(row_data[6]) > col_widths[6] else row_data[6]
        logger.info(" | ".join(f"{str(d):<{w}}" for d, w in zip(row_data, col_widths)))

def start_all_servers():
    """Starts all enabled servers defined in the configuration."""
    config = load_config()
    if config is None: return
    logger.info("Starting all enabled servers (via mcp-proxy)...")
    started_count = 0
    for server in config.get("servers", []):
        if server.get("enabled", False):
            start_server(server) # Calls the updated start_server
            started_count += 1
    if started_count == 0:
         logger.info("No enabled servers found to start.")

def stop_all_servers():
    """Stops all servers managed by this script instance."""
    config = load_config()
    if config is None: return
    logger.info("Stopping all managed mcp-proxy servers...")
    stopped_count = 0
    # Iterate through config to find potential PIDs to stop
    for server in config.get("servers", []):
        # Check if we have a PID file for this server
        name = server.get("name")
        if name and load_pid(name):
             stop_server(server) # Calls the updated stop_server
             stopped_count += 1
    if stopped_count == 0:
         logger.info("No running servers managed by this script were found to stop (based on PID files).")

def run_daemon():
    """Starts all servers via mcp-proxy and monitors them."""
    logger.info("Starting MCP Manager in daemon mode (using mcp-proxy)...")
    start_all_servers()
    logger.info("Initial startup complete. Monitoring proxied services...")

    config = load_config()
    if config is None: logger.error("Cannot run daemon without valid config."); return

    try:
        while True:
            time.sleep(30) # Check interval
            logger.debug("Daemon check running...")
            current_config = load_config() # Reload config in case it changed
            if current_config is None:
                 logger.error("Daemon failed to reload config. Skipping check cycle.")
                 continue

            for server in current_config.get("servers", []):
                if server.get("enabled", False):
                    name = server.get("name")
                    pid = load_pid(name) # mcp-proxy PID
                    internal_port = server.get("internal_port")

                    if pid and not is_running(pid):
                        logger.warning(f"Daemon detected mcp-proxy for '{name}' (PID {pid}) stopped unexpectedly. Restarting...")
                        remove_pid_file(name)
                        start_server(server) # Restart using the proxy logic
                    elif pid and is_running(pid) and internal_port:
                        # Optional: Deeper health check - is the port still listening?
                        port_pid = is_port_in_use(internal_port)
                        if port_pid != pid:
                             logger.warning(f"Daemon detected mcp-proxy for '{name}' (PID {pid}) running, but port {internal_port} not listening or used by PID {port_pid}. Restarting...")
                             stop_server(server)
                             time.sleep(1)
                             start_server(server)
                    elif not pid and is_port_in_use(internal_port):
                         # Server not started by us, but port is used. Log warning.
                         logger.warning(f"Daemon detected port {internal_port} for '{name}' is in use, but no mcp-proxy PID file found. Manual intervention might be needed.")
                    elif not pid and not is_port_in_use(internal_port):
                         # Server should be running but isn't, and port is free. Start it.
                         logger.warning(f"Daemon detected server '{name}' should be running but isn't. Starting...")
                         start_server(server)


    except KeyboardInterrupt: logger.info("Daemon mode interrupted by user (Ctrl+C).")
    except Exception as e: logger.error(f"Daemon mode encountered an error: {e}", exc_info=True) # Log traceback
    finally:
        logger.info("Stopping all managed mcp-proxy servers before exiting daemon mode...")
        stop_all_servers()
        logger.info("MCP Manager daemon finished.")


def main():
    """Parses command-line arguments and executes the corresponding action."""
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <command> [server_name]")
        print("Commands: start|stop|restart|status|daemon|start-all|stop-all")
        sys.exit(1)

    command = sys.argv[1].lower()
    server_name = sys.argv[2] if len(sys.argv) > 2 else None

    # Handle commands that don't need a server name
    if command == "status":
        print_status_table()
        sys.exit(0)
    if command == "daemon":
        run_daemon()
        sys.exit(0)
    if command == "start-all":
        start_all_servers()
        sys.exit(0)
    if command == "stop-all":
        stop_all_servers()
        sys.exit(0)

    # Commands requiring a server name (or implicit 'all' for start/stop)
    if command in ["start", "stop", "restart"]:
        if not server_name:
             # Allow 'start' and 'stop' without server_name to mean 'all'
             if command == "start": start_all_servers(); sys.exit(0)
             elif command == "stop": stop_all_servers(); sys.exit(0)
             else: logger.error(f"Command '{command}' requires a server name."); sys.exit(1)

        # Find the specific server config
        config = load_config()
        if config is None: sys.exit(1)
        target_server = next((s for s in config.get("servers", []) if s.get("name") == server_name), None)

        if not target_server:
            logger.error(f"Server '{server_name}' not found in configuration.")
            sys.exit(1)

        # Execute command for the specific server
        if command == "start":
            if not target_server.get("enabled", False):
                 logger.warning(f"Cannot start server '{server_name}' because it is disabled in the configuration.")
            else:
                 start_server(target_server)
        elif command == "stop":
            stop_server(target_server) # Allow stopping even if disabled in config
        elif command == "restart":
             if not target_server.get("enabled", False):
                 logger.warning(f"Cannot restart server '{server_name}' because it is disabled. Stopping only (if running).")
                 stop_server(target_server) # Stop it if it was running
             else:
                 restart_server(target_server)
    else:
        logger.error(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    # Setup signal handling for graceful shutdown in daemon mode
    def signal_handler(sig, frame):
        logger.info(f"Received signal {signal.Signals(sig).name}, initiating shutdown...")
        # Let the finally block in run_daemon handle cleanup
        # For non-daemon, this allows Ctrl+C to interrupt potentially long operations
        sys.exit(0) # Exit gracefully

    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    except (ValueError, AttributeError, OSError):
         logger.warning("Could not set signal handlers (e.g., running on Windows or unsupported env).")

    main()
