"""MCP Server Management Tool - Process Utility Module

Contains utility functions for process management, including command execution, port checking, process termination, and other functionalities.
"""

# scripts/mcp_manager/process_utils.py
import os
import signal
import socket
import subprocess
import sys
import threading
import time

# Used to store process information started by this script {name: Popen_object}
# Note: This only tracks processes started by the current running instance
RUNNING_PROCESSES = {}

# --- Port Checking ---


def is_port_in_use(port: int) -> bool:
    """Check if a local port is being listened on"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(0.2)  # Brief timeout
            # Try to connect, if successful it means the port is in use
            s.connect(("127.0.0.1", port))
            return True
        except (socket.timeout, ConnectionRefusedError):
            return False
        except Exception as e:
            # Other errors also indicate that the port is unavailable or the check failed
            # print(f"Error checking port {port}: {e}") # Optional debug information
            return False


# --- Command Execution ---


def run_command(
    command: str, cwd: str | None = None, env: dict | None = None, server_name: str = ""
) -> subprocess.Popen | None:
    """Run a command in the specified directory and return a Popen object"""
    print(f"[{server_name}] Preparing to execute command: '{command}' in directory '{cwd or os.getcwd()}'")

    current_env = os.environ.copy()
    if env:
        current_env.update(env)
        # print(f"[{server_name}] Using custom environment variables: {env}") # Debug information

    # Ensure PATH exists
    if "PATH" not in current_env or not current_env["PATH"]:
        current_env["PATH"] = os.environ.get("PATH", "")  # Get from os.environ just in case

    shell = False
    args = command  # 默认将整个命令传递

    # Windows-specific command handling
    if os.name == "nt":
        # For commands that need cmd /c (e.g., containing pipes, redirections, or built-in commands)
        if command.lower().startswith("cmd /c") or any(
            op in command for op in ["|", ">", "<", "&", "&&", "||"]
        ):
            args = command  # 保持原样
            shell = True  # cmd /c 需要 shell=True
            print(f"[DEBUG][{server_name}] Using cmd /c (shell=True) to execute: {args}")
        # For npm/npx, it's better to call the .cmd file directly, avoiding an extra layer of cmd /c
        elif command.lower().startswith("npm ") or command.lower().startswith("npx "):
            parts = command.split(" ", 1)
            cmd_name = parts[0]
            cmd_args = parts[1] if len(parts) > 1 else ""
            # Try to find the full path of npm.cmd or npx.cmd (may be in PATH or node_modules/.bin)
            # Simplified handling here, using cmd /c directly for compatibility, although slightly less efficient
            args = f"cmd /c {cmd_name} {cmd_args}"
            shell = True
            print(
                f"[DEBUG][{server_name}] Using cmd /c (shell=True) to execute {cmd_name}: {args}"
            )
        else:
            # For other simple commands, try to execute directly, may not need shell=True
            try:
                # Try to split the command, if it fails (e.g., path contains spaces and is not quoted), fall back to shell=True
                args_list = subprocess.list2cmdline(
                    [command.split()[0]]
                )  # 检查第一个参数是否像可执行文件
                args = command.split()
                shell = False  # 尝试非 shell 模式
                print(f"[DEBUG][{server_name}] Attempting to execute directly (shell=False): {args}")
            except Exception:
                args = command  # Fall back to passing the entire command as a string
                shell = True
                print(f"[DEBUG][{server_name}] Unable to split command, falling back to shell=True: {args}")

    # Linux/macOS handling
    else:
        # Usually can be split directly, but shell=True better handles complex commands
        args = command
        shell = True  # On non-Windows, using shell=True is usually safer for handling complex commands
        print(f"[DEBUG][{server_name}] On non-Windows using shell=True to execute: {args}")

    try:
        creationflags = 0
        if os.name == "nt":
            # CREATE_NEW_PROCESS_GROUP allows us to reliably terminate child processes later
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        process = subprocess.Popen(
            args,
            cwd=cwd,
            env=current_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=shell,
            creationflags=creationflags,
        )
        print(f"[{server_name}] Command started (PID: {process.pid})")
        return process
    except FileNotFoundError:
        cmd_to_report = args[0] if isinstance(args, list) else args.split()[0]
        print(f"Error: Command '{cmd_to_report}' not found. Please ensure it is installed and in the system PATH.")
        return None
    except Exception as e:
        print(f"Error: Error executing command '{command}': {e}")
        return None


# --- Process Streaming ---


def stream_output(process: subprocess.Popen, server_name: str):
    """Print process stdout and stderr in real-time"""

    def reader(pipe, prefix):
        try:
            if pipe:
                for line in iter(pipe.readline, ""):
                    print(f"[{server_name}-{prefix}] {line.strip()}")
        except ValueError:
            # This error may occur when the pipe is closed as the process ends
            print(f"[{server_name}-{prefix}] Error reading pipe (may be closed).")
        finally:
            if pipe:
                try:
                    pipe.close()
                except Exception:
                    pass  # Ignore closing errors

    stdout_thread = threading.Thread(
        target=reader, args=(process.stdout, "out"), daemon=True
    )
    stderr_thread = threading.Thread(
        target=reader, args=(process.stderr, "err"), daemon=True
    )
    stdout_thread.start()
    stderr_thread.start()
    return stdout_thread, stderr_thread


# --- Process Termination ---


def stop_process(name: str, process: subprocess.Popen):
    """Attempt to stop the specified process"""
    if process.poll() is None:  # Process is still running
        print(f"[{name}] Attempting to stop process (PID: {process.pid})...")
        try:
            # On Windows, sending CTRL_BREAK_EVENT is usually the recommended way to stop console applications
            # But terminate() / kill() is more universal
            if os.name == "nt":
                print(f"[{name}] (Windows) Sending CTRL_BREAK_EVENT to process group...")
                # Note: This will be sent to the entire process group, may affect child processes
                os.kill(process.pid, signal.CTRL_BREAK_EVENT)
            else:
                print(f"[{name}] (Non-Windows) Sending SIGTERM signal...")
                process.terminate()  # Send SIGTERM

            # Wait for a while to let the process respond
            try:
                process.wait(timeout=10)
                print(f"[{name}] Process (PID: {process.pid}) has been successfully stopped.")
            except subprocess.TimeoutExpired:
                print(
                    f"[{name}] Process (PID: {process.pid}) did not respond to SIGTERM/CTRL_BREAK within 10 seconds. Attempting to force terminate (SIGKILL)..."
                )
                process.kill()  # Send SIGKILL
                process.wait(timeout=5)  # Wait for SIGKILL to take effect
                print(f"[{name}] Process (PID: {process.pid}) has been forcibly terminated.")
            except Exception as e:  # Handle other errors that may occur with wait
                print(
                    f"[{name}] Error occurred while waiting for process {process.pid} to stop: {e}. Attempting to force terminate..."
                )
                process.kill()
                print(f"[{name}] Process (PID: {process.pid}) has been forcibly terminated.")

        except ProcessLookupError:
            print(
                f"[{name}] Process (PID: {process.pid}) not found when attempting to stop (may have exited on its own)."
            )
        except OSError as e:
            print(f"[{name}] OS error occurred when stopping process {process.pid}: {e}.")
        except Exception as e:
            print(f"[{name}] Unexpected error occurred when stopping process {process.pid}: {e}")
    else:
        print(f"[{name}] Process (PID: {process.pid}) is already stopped.")

    # Clean up standard output/error streams
    try:
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()
    except Exception:
        pass  # Ignore closing errors


# --- Git Operations ---


def clone_repo(repo_url: str, target_dir: str, server_name: str = "") -> bool:
    """Clone or update Git repository"""
    target_dir_abs = os.path.abspath(target_dir)
    git_command_base = ["git"]

    if not os.path.exists(target_dir_abs):
        print(
            f"[{server_name}] Repository directory does not exist, cloning {repo_url} to {target_dir_abs}..."
        )
        command = git_command_base + ["clone", repo_url, target_dir_abs]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                errors="replace",
            )
            print(f"[{server_name}] Clone successful.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[{server_name}] Error: Failed to clone repository. Return code: {e.returncode}")
            print(f"[{server_name}] Git Stderr:\n{e.stderr}")
            print(f"[{server_name}] Git Stdout:\n{e.stdout}")
            return False
        except FileNotFoundError:
            print(
                f"[{server_name}] Error: 'git' command not found. Please ensure Git is installed and added to the system PATH."
            )
            return False
        except Exception as e:
            print(f"[{server_name}] Unknown error occurred while cloning repository: {e}")
            return False
    else:
        print(f"[{server_name}] Directory {target_dir_abs} already exists. Attempting to update (git pull)...")
        command = git_command_base + ["pull"]
        try:
            # Execute git pull in the target directory
            result = subprocess.run(
                command,
                cwd=target_dir_abs,
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                errors="replace",
            )
            print(f"[{server_name}] Update successful.")
            # Print git pull output (optional)
            # if result.stdout.strip():
            #     print(f"[{server_name}] Git Pull Output:\n{result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[{server_name}] Warning: Failed to update repository. Return code: {e.returncode}")
            print(f"[{server_name}] Git Stderr:\n{e.stderr}")
            print(f"[{server_name}] Git Stdout:\n{e.stdout}")
            # Not considered a fatal error, return True but print a warning
            return True  # Or return False as needed
        except FileNotFoundError:
            print(
                f"[{server_name}] Error: 'git' command not found. Please ensure Git is installed and added to the system PATH."
            )
            return False  # Update failure is a problem
        except Exception as e:
            print(f"[{server_name}] Unknown error occurred while updating repository: {e}")
            return False  # Update failure is a problem
