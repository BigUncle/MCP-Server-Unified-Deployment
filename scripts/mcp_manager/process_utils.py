"""MCP 服务器管理工具 - 进程实用工具模块

包含用于进程管理的实用函数，包括命令执行、端口检查、进程终止等功能。
"""

# scripts/mcp_manager/process_utils.py
import os
import signal
import socket
import subprocess
import sys
import threading
import time

# 用于存储由本脚本启动的进程信息 {name: Popen_object}
# 注意：这只跟踪当前运行实例启动的进程
RUNNING_PROCESSES = {}

# --- Port Checking ---


def is_port_in_use(port: int) -> bool:
    """检查本地端口是否被监听"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(0.2)  # 短暂超时
            # 尝试连接，如果成功说明端口在使用中
            s.connect(("127.0.0.1", port))
            return True
        except (socket.timeout, ConnectionRefusedError):
            return False
        except Exception as e:
            # 其他错误也认为端口不可用或检查失败
            # print(f"检查端口 {port} 时发生错误: {e}") # 可选的调试信息
            return False


# --- Command Execution ---


def run_command(
    command: str, cwd: str | None = None, env: dict | None = None, server_name: str = ""
) -> subprocess.Popen | None:
    """在指定目录运行命令并返回 Popen 对象"""
    print(f"[{server_name}] 准备执行命令: '{command}' 于目录 '{cwd or os.getcwd()}'")

    current_env = os.environ.copy()
    if env:
        current_env.update(env)
        # print(f"[{server_name}] 使用了自定义环境变量: {env}") # 调试信息

    # 确保 PATH 存在
    if "PATH" not in current_env or not current_env["PATH"]:
        current_env["PATH"] = os.environ.get("PATH", "")  # 从 os.environ 获取以防万一

    shell = False
    args = command  # 默认将整个命令传递

    # Windows 特定的命令处理
    if os.name == "nt":
        # 对于需要 cmd /c 的命令 (例如包含管道、重定向或内置命令)
        if command.lower().startswith("cmd /c") or any(
            op in command for op in ["|", ">", "<", "&", "&&", "||"]
        ):
            args = command  # 保持原样
            shell = True  # cmd /c 需要 shell=True
            print(f"[DEBUG][{server_name}] 使用 cmd /c (shell=True) 执行: {args}")
        # 对于 npm/npx，最好直接调用 .cmd 文件，避免多一层 cmd /c
        elif command.lower().startswith("npm ") or command.lower().startswith("npx "):
            parts = command.split(" ", 1)
            cmd_name = parts[0]
            cmd_args = parts[1] if len(parts) > 1 else ""
            # 尝试找到 npm.cmd 或 npx.cmd 的完整路径 (可能在 PATH 或 node_modules/.bin)
            # 这里简化处理，直接使用 cmd /c 保证兼容性，虽然效率稍低
            args = f"cmd /c {cmd_name} {cmd_args}"
            shell = True
            print(
                f"[DEBUG][{server_name}] 使用 cmd /c (shell=True) 执行 {cmd_name}: {args}"
            )
        else:
            # 对于其他简单命令，尝试直接执行，可能不需要 shell=True
            try:
                # 尝试分割命令，如果失败（例如路径含空格且未加引号），则回退到 shell=True
                args_list = subprocess.list2cmdline(
                    [command.split()[0]]
                )  # 检查第一个参数是否像可执行文件
                args = command.split()
                shell = False  # 尝试非 shell 模式
                print(f"[DEBUG][{server_name}] 尝试直接执行 (shell=False): {args}")
            except Exception:
                args = command  # 回退到将整个命令作为字符串传递
                shell = True
                print(f"[DEBUG][{server_name}] 无法分割命令，回退到 shell=True: {args}")

    # Linux/macOS 处理
    else:
        # 通常可以直接分割，但 shell=True 更能处理复杂命令
        args = command
        shell = True  # 在非 Windows 上使用 shell=True 通常更安全地处理复杂命令
        print(f"[DEBUG][{server_name}] 在非 Windows 上使用 shell=True 执行: {args}")

    try:
        creationflags = 0
        if os.name == "nt":
            # CREATE_NEW_PROCESS_GROUP 允许我们之后可靠地终止子进程
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
        print(f"[{server_name}] 命令已启动 (PID: {process.pid})")
        return process
    except FileNotFoundError:
        cmd_to_report = args[0] if isinstance(args, list) else args.split()[0]
        print(f"错误: 命令 '{cmd_to_report}' 未找到。请确保它已安装并在系统 PATH 中。")
        return None
    except Exception as e:
        print(f"错误: 执行命令 '{command}' 时出错: {e}")
        return None


# --- Process Streaming ---


def stream_output(process: subprocess.Popen, server_name: str):
    """实时打印进程的stdout和stderr"""

    def reader(pipe, prefix):
        try:
            if pipe:
                for line in iter(pipe.readline, ""):
                    print(f"[{server_name}-{prefix}] {line.strip()}")
        except ValueError:
            # 可能在进程结束时管道关闭导致此错误
            print(f"[{server_name}-{prefix}] 读取管道时出错 (可能已关闭).")
        finally:
            if pipe:
                try:
                    pipe.close()
                except Exception:
                    pass  # 忽略关闭错误

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
    """尝试停止指定的进程"""
    if process.poll() is None:  # 进程仍在运行
        print(f"[{name}] 正在尝试停止进程 (PID: {process.pid})...")
        try:
            # 在 Windows 上，发送 CTRL_BREAK_EVENT 通常是停止控制台应用的推荐方式
            # 但 terminate() / kill() 更通用
            if os.name == "nt":
                print(f"[{name}] (Windows) 发送 CTRL_BREAK_EVENT 到进程组...")
                # 注意：这会发送到整个进程组，可能影响子进程
                os.kill(process.pid, signal.CTRL_BREAK_EVENT)
            else:
                print(f"[{name}] (非 Windows) 发送 SIGTERM 信号...")
                process.terminate()  # 发送 SIGTERM

            # 等待一段时间让进程响应
            try:
                process.wait(timeout=10)
                print(f"[{name}] 进程 (PID: {process.pid}) 已成功停止。")
            except subprocess.TimeoutExpired:
                print(
                    f"[{name}] 进程 (PID: {process.pid}) 在 10 秒内未响应 SIGTERM/CTRL_BREAK。尝试强制终止 (SIGKILL)..."
                )
                process.kill()  # 发送 SIGKILL
                process.wait(timeout=5)  # 等待 SIGKILL 生效
                print(f"[{name}] 进程 (PID: {process.pid}) 已被强制终止。")
            except Exception as e:  # 处理 wait 可能出现的其他错误
                print(
                    f"[{name}] 等待进程 {process.pid} 停止时发生错误: {e}. 尝试强制终止..."
                )
                process.kill()
                print(f"[{name}] 进程 (PID: {process.pid}) 已被强制终止。")

        except ProcessLookupError:
            print(
                f"[{name}] 进程 (PID: {process.pid}) 在尝试停止时未找到 (可能已自行退出)。"
            )
        except OSError as e:
            print(f"[{name}] 停止进程 {process.pid} 时发生 OS 错误: {e}。")
        except Exception as e:
            print(f"[{name}] 停止进程 {process.pid} 时发生意外错误: {e}")
    else:
        print(f"[{name}] 进程 (PID: {process.pid}) 已经停止。")

    # 清理标准输出/错误流
    try:
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()
    except Exception:
        pass  # 忽略关闭错误


# --- Git Operations ---


def clone_repo(repo_url: str, target_dir: str, server_name: str = "") -> bool:
    """克隆或更新Git仓库"""
    target_dir_abs = os.path.abspath(target_dir)
    git_command_base = ["git"]

    if not os.path.exists(target_dir_abs):
        print(
            f"[{server_name}] 仓库目录不存在，正在克隆 {repo_url} 到 {target_dir_abs}..."
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
            print(f"[{server_name}] 克隆成功。")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[{server_name}] 错误: 克隆仓库失败。返回码: {e.returncode}")
            print(f"[{server_name}] Git Stderr:\n{e.stderr}")
            print(f"[{server_name}] Git Stdout:\n{e.stdout}")
            return False
        except FileNotFoundError:
            print(
                f"[{server_name}] 错误: 'git' 命令未找到。请确保 Git 已安装并添加到系统 PATH。"
            )
            return False
        except Exception as e:
            print(f"[{server_name}] 克隆仓库时发生未知错误: {e}")
            return False
    else:
        print(f"[{server_name}] 目录 {target_dir_abs} 已存在。尝试更新 (git pull)...")
        command = git_command_base + ["pull"]
        try:
            # 在目标目录执行 git pull
            result = subprocess.run(
                command,
                cwd=target_dir_abs,
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                errors="replace",
            )
            print(f"[{server_name}] 更新成功。")
            # 打印 git pull 的输出（可选）
            # if result.stdout.strip():
            #     print(f"[{server_name}] Git Pull Output:\n{result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[{server_name}] 警告: 更新仓库失败。返回码: {e.returncode}")
            print(f"[{server_name}] Git Stderr:\n{e.stderr}")
            print(f"[{server_name}] Git Stdout:\n{e.stdout}")
            # 不认为是致命错误，返回 True，但打印警告
            return True  # 或者根据需要返回 False
        except FileNotFoundError:
            print(
                f"[{server_name}] 错误: 'git' 命令未找到。请确保 Git 已安装并添加到系统 PATH。"
            )
            return False  # 更新失败是问题
        except Exception as e:
            print(f"[{server_name}] 更新仓库时发生未知错误: {e}")
            return False  # 更新失败是问题
