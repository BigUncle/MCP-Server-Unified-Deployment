# scripts/mcp_manager/commands.py
import json
import os
import signal
import sys
import time

# Use relative imports
from .config import SERVERS_DIR, load_config
from .process_utils import (RUNNING_PROCESSES, clone_repo, is_port_in_use,
                            run_command, stop_process, stream_output)

# --- Command Functions ---


def setup_server(server_config: dict):
    """Install dependencies for the specified server"""
    name = server_config.get("name", "Unknown Server")
    print(f"\n--- Setting up server: {name} ---")
    if not server_config.get("enabled", True):
        print(f"Server '{name}' is disabled. Skipping setup.")
        return

    server_type = server_config.get("type")
    server_path = server_config.get("path")  # load_config 应该已经修正了这个路径

    # 1. Clone/update repository (only for source_code type)
    if server_type == "source_code":
        repo_url = server_config.get("repo")
        if repo_url:
            # Path should be determined by load_config, here we assume it's in the parent directory of server_config['path']
            # Or a more robust way is to infer from the repo url
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            clone_target_dir = os.path.join(SERVERS_DIR, repo_name)
            if not clone_repo(repo_url, clone_target_dir, server_name=name):
                print(f"[{name}] Repository operation failed. Stopping setup.")
                return  # Stop if clone/update fails
        else:
            print(
                f"[{name}] Warning: source_code type server missing 'repo' configuration, cannot automatically clone/update."
            )

        # Check if the final path exists (after clone/update or when manually specified)
        if not server_path or not os.path.isdir(server_path):
            print(
                f"Error: Server path '{server_path}' not found or invalid for '{name}'. Please check configuration or repository cloning step."
            )
            return

    # 2. Run installation commands
    install_commands = server_config.get("install_commands", [])
    if not install_commands:
        print(f"[{name}] No installation commands specified. Skipping installation step.")
    else:
        print(f"[{name}] Executing installation commands...")
        # Determine the working directory for executing commands
        # For source_code, use its path; for other types, may not need specific cwd
        cwd = server_path if server_type == "source_code" else None

        for command in install_commands:
            process = run_command(command, cwd=cwd, server_name=f"{name}-install")
            if process:
                # Synchronously wait for installation command to complete and print output
                stdout_lines = []
                stderr_lines = []
                import subprocess

                try:
                    # Use communicate() to get all output and wait for the process to end
                    stdout, stderr = process.communicate(timeout=300)  # 5 minutes timeout
                    stdout_lines = stdout.strip().splitlines()
                    stderr_lines = stderr.strip().splitlines()

                    if stdout_lines:
                        print(f"[{name}-install-out] {' '.join(stdout_lines)}")
                    if process.returncode != 0:
                        print(
                            f"Error: Error executing installation command for '{name}'. Command failed: {command}"
                        )
                        if stderr_lines:
                            print(f"[{name}-install-err] {' '.join(stderr_lines)}")
                        return  # Stop if installation fails
                    else:
                        print(f"[{name}] Command '{command}' completed successfully.")

                except subprocess.TimeoutExpired:
                    print(f"Error: Timeout executing installation command '{command}' for '{name}'.")
                    stop_process(f"{name}-install", process)  # Try to stop the timed-out process
                    return
                except Exception as e:
                    print(f"Error: Unexpected error occurred while waiting for installation command '{command}' to complete: {e}")
                    # Try to read remaining output (if possible)
                    try:
                        stdout, stderr = process.communicate()
                    except:
                        pass
                    if process.poll() is None:  # If still running, try to stop
                        stop_process(f"{name}-install", process)
                    return
            else:
                print(f"Error: Unable to start installation command '{command}' for '{name}'.")
                return  # Stop if unable to execute command

    print(f"--- Server setup completed: {name} ---")


def start_server(server_config: dict, watch: bool = False):
    """Start the specified server"""
    name = server_config.get("name", "Unknown Server")
    if not server_config.get("enabled", True):
        print(f"Server '{name}' is disabled. Skipping startup.")
        return

    # Check if already running in this script instance
    if name in RUNNING_PROCESSES and RUNNING_PROCESSES[name].poll() is None:
        print(
            f"Server '{name}' appears to have been started by this script already (PID: {RUNNING_PROCESSES[name].pid})."
        )
        # Can optionally check if the port is actually listening as a secondary confirmation
        port = server_config.get("sse_port") or server_config.get("port")
        if port and is_port_in_use(int(port)):
            print(f"Port {port} is listening. No need to start again.")
            return
        else:
            print(
                f"Warning: Process record exists, but port {port} is not listening. Process may have crashed or not fully started. Attempting to restart..."
            )
            # Clean up old record, allowing restart
            del RUNNING_PROCESSES[name]

    print(f"\n--- Starting server: {name} ---")
    server_type = server_config.get("type")
    server_path = server_config.get("path")  # load_config should have already corrected this path

    # Check path (only for source_code type)
    if server_type == "source_code":
        if not server_path or not os.path.isdir(server_path):
            print(
                f"Error: Server path '{server_path}' not found for '{name}'. Please run 'setup' first."
            )
            return

    # Prepare start command
    start_command = server_config.get("start_command")
    if not start_command:
        print(f"Error: Server '{name}' does not define 'start_command'.")
        return

    # Process SSE wrapper command (if exists)
    sse_start_command_template = server_config.get("sse_start_command")
    final_start_command = start_command  # Default to original command
    if sse_start_command_template:
        sse_host = server_config.get("sse_host", "localhost")
        sse_port = server_config.get("sse_port")
        allow_origin = server_config.get("allow_origin", "*")
        if not sse_port:
            print(
                f"Error: Server '{name}' defines 'sse_start_command' but is missing 'sse_port'."
            )
            return

        # Replace placeholders
        try:
            final_start_command = sse_start_command_template.format(
                sse_host=sse_host,
                sse_port=sse_port,
                allow_origin=allow_origin,
                start_command=start_command,  # Original command passed as parameter
            )
            print(f"[{name}] Using SSE wrapper command: {final_start_command}")
        except KeyError as e:
            print(
                f"Error: Error replacing placeholder {{{e}}} in 'sse_start_command'. Please check the template."
            )
            return
    else:
        print(f"[{name}] Using start command: {final_start_command}")

    # Get environment variables
    env = server_config.get("env", {})

    # Determine working directory
    cwd = server_path if server_type == "source_code" else None

    # Start process
    process = run_command(final_start_command, cwd=cwd, env=env, server_name=name)

    if process:
        RUNNING_PROCESSES[name] = process
        port_to_check = server_config.get("sse_port") or server_config.get("port")
        print(
            f"Server '{name}' start command executed (PID: {process.pid})."
            f"{f' Expected listening port: {port_to_check}' if port_to_check else ''}"
        )

        # Start output stream threads
        stdout_thread, stderr_thread = stream_output(process, name)

        if watch:
            print(f"[{name}] Entering watch mode. Press Ctrl+C to stop.")
            try:
                # Wait for process to end
                process.wait()
            except KeyboardInterrupt:
                print(f"\n[{name}] Ctrl+C detected. Stopping server...")
                stop_process(name, process)  # Directly call stop_process
            except Exception as e:
                print(f"\n[{name}] Error occurred while waiting for process: {e}. Attempting to stop...")
                stop_process(name, process)
            finally:
                # Ensure threads end (although they are daemon threads, joining them is safer)
                if stdout_thread.is_alive():
                    stdout_thread.join(timeout=1)
                if stderr_thread.is_alive():
                    stderr_thread.join(timeout=1)
                if name in RUNNING_PROCESSES:
                    del RUNNING_PROCESSES[name]  # Remove from running list
                print(f"--- Server '{name}' has stopped (watch mode ended). ---")
        else:
            # Non-watch mode, run in background
            # Brief wait and check if process fails quickly
            time.sleep(3)  # Wait 3 seconds to give the service a chance to start or fail
            if process.poll() is not None:  # Process has exited
                print(
                    f"Error: Server '{name}' (PID: {process.pid}) seems to have exited shortly after starting (exit code: {process.poll()})."
                )
                # Try to read the last error output (may have been read by stream_output thread)
                # Consider having stream_output collect the last few lines of error information
                if name in RUNNING_PROCESSES:
                    del RUNNING_PROCESSES[name]  # Remove from running list
            else:
                print(f"Server '{name}' (PID: {process.pid}) is running in the background.")
                # Check if port is listening as expected (optional but recommended)
                if port_to_check:
                    time.sleep(2)  # Wait a bit longer to ensure service is listening
                    if is_port_in_use(int(port_to_check)):
                        print(f"[{name}] Port {port_to_check} confirmed to be listening.")
                    else:
                        print(
                            f"Warning: Server '{name}' is running, but port {port_to_check} is not listening as expected."
                        )

    else:
        print(f"Error: Unable to start server '{name}'.")


def stop_server(server_config: dict):
    """Stop the specified server (if started by the current script)"""
    name = server_config.get("name", "Unknown Server")
    print(f"\n--- Stopping server: {name} ---")
    if name in RUNNING_PROCESSES:
        process = RUNNING_PROCESSES[name]
        stop_process(name, process)  # Use the refactored stop function
        # Remove from monitoring list regardless of whether stopping was successful
        del RUNNING_PROCESSES[name]
    else:
        print(f"Server '{name}' is not running under the management of the current script (or has already been stopped).")
        # Note: This function cannot stop processes not started by the current script instance
        # If you need to stop any process listening on a specific port, more complex logic is needed (e.g., finding PID)


def status_servers():
    """Display the status of all configured servers"""
    print("\n--- MCP Server Status ---")
    config = load_config()
    servers = config.get("servers", [])

    if not servers:
        print("No servers defined in the configuration file.")
        return

    print(
        f"{'Name':<20} {'Enabled':<7} {'Type':<12} {'Port':<6} {'Status':<25} {'PID (This Instance)':<15} {'Path'}"
    )
    print("-" * 100)  # Adjust separator line length

    # Clean up processes in RUNNING_PROCESSES that have already ended
    for name, process in list(RUNNING_PROCESSES.items()):
        if process.poll() is not None:
            print(f"[Status Check] Cleaning up ended process record: {name} (PID: {process.pid})")
            del RUNNING_PROCESSES[name]

    for server in servers:
        name = server.get("name", "N/A")
        enabled = str(server.get("enabled", True))
        stype = server.get("type", "N/A")
        # Prioritize sse_port, then port
        port = server.get("sse_port") or server.get("port")
        path = server.get("path", "N/A")
        status = "Unknown"
        pid_str = "N/A"

        if enabled == "True":
            if port:
                port_int = int(port)
                if is_port_in_use(port_int):
                    status = f"Running (port {port} listening)"
                    # Check if started by this instance
                    if name in RUNNING_PROCESSES:
                        pid_str = str(RUNNING_PROCESSES[name].pid)
                    else:
                        pid_str = "(External start?)"
                else:
                    status = "Stopped"
                    # If there's a record in this instance but the port is not listening, it may have failed to start or crashed
                    if name in RUNNING_PROCESSES:
                        exit_code = RUNNING_PROCESSES[name].poll()
                        status = f"Error/Exited (code: {exit_code})"
                        pid_str = str(RUNNING_PROCESSES[name].pid)
                        # Consider cleaning up RUNNING_PROCESSES[name] here
            else:
                status = "No port configured"  # For services without ports, status is unknown
                if name in RUNNING_PROCESSES:  # But if this instance started it...
                    if RUNNING_PROCESSES[name].poll() is None:
                        status = "Running (no port check)"
                        pid_str = str(RUNNING_PROCESSES[name].pid)
                    else:
                        exit_code = RUNNING_PROCESSES[name].poll()
                        status = f"Exited (code: {exit_code})"
                        pid_str = str(RUNNING_PROCESSES[name].pid)

        else:  # enabled == "False"
            status = "Disabled"

        print(
            f"{name:<20} {enabled:<7} {stype:<12} {str(port):<6} {status:<25} {pid_str:<15} {path}"
        )


def stop_all_servers():
    """Stop all servers started by the current script instance"""
    print("\n--- Stopping all managed servers ---")
    if not RUNNING_PROCESSES:
        print("The current script is not managing any running servers.")
        return

    # Create a copy for iteration, because stop_process will modify the dictionary
    processes_to_stop = list(RUNNING_PROCESSES.items())

    for name, process in processes_to_stop:
        print(f"Requesting stop: {name} (PID: {process.pid})")
        stop_process(name, process)

    # Confirm cleanup (theoretically stop_process has already handled it internally, but just in case)
    remaining = list(RUNNING_PROCESSES.keys())
    if remaining:
        print(f"Warning: The following servers may not have been completely stopped or cleaned up: {', '.join(remaining)}")
    else:
        print("All managed servers have been processed with stop requests.")

    RUNNING_PROCESSES.clear()  # Ensure it's empty


def list_servers():
    """List all configured servers (print configuration)"""
    print("\n--- Configured MCP Servers ---")
    config = load_config()
    print(json.dumps(config, indent=2, ensure_ascii=False))


# --- Signal Handling for Graceful Exit ---


def setup_signal_handlers():
    """Set up signal handlers to try to gracefully stop all servers"""

    def signal_handler(sig, frame):
        print(f"\nSignal {signal.Signals(sig).name} detected. Attempting to stop all managed servers...")
        stop_all_servers()
        print("Exiting script.")
        sys.exit(0)

    # Handle SIGINT (Ctrl+C) and SIGTERM (signal sent by kill command by default)
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        # On Windows, SIGBREAK may also be relevant, but CTRL_BREAK_EVENT is used for child processes
        if os.name == "nt":
            # signal.signal(signal.SIGBREAK, signal_handler) # Usually no need to handle SIGBREAK for the main script
            pass
    except ValueError:
        print("Warning: Running in a non-main thread, cannot set signal handlers.")
    except AttributeError:
        print("Warning: The current environment does not support signal handling (e.g., some Windows environments or restricted environments).")
