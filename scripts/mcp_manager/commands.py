# scripts/mcp_manager/commands.py
import json
import os
import signal
import sys
import time

# 使用相对导入
from .config import SERVERS_DIR, load_config
from .process_utils import (RUNNING_PROCESSES, clone_repo, is_port_in_use,
                            run_command, stop_process, stream_output)

# --- Command Functions ---


def setup_server(server_config: dict):
    """安装指定服务器的依赖"""
    name = server_config.get("name", "未知服务器")
    print(f"\n--- 正在设置服务器: {name} ---")
    if not server_config.get("enabled", True):
        print(f"服务器 '{name}' 已禁用。跳过设置。")
        return

    server_type = server_config.get("type")
    server_path = server_config.get("path")  # load_config 应该已经修正了这个路径

    # 1. 克隆/更新仓库 (仅 source_code 类型)
    if server_type == "source_code":
        repo_url = server_config.get("repo")
        if repo_url:
            # 路径应该由 load_config 确定，这里假设它在 server_config['path'] 的父目录
            # 或者更健壮的方式是从 repo url 推断
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            clone_target_dir = os.path.join(SERVERS_DIR, repo_name)
            if not clone_repo(repo_url, clone_target_dir, server_name=name):
                print(f"[{name}] 仓库操作失败。停止设置。")
                return  # 克隆/更新失败则停止
        else:
            print(
                f"[{name}] 警告: source_code 类型服务器缺少 'repo' 配置，无法自动克隆/更新。"
            )

        # 检查最终路径是否存在 (克隆/更新后或手动指定时)
        if not server_path or not os.path.isdir(server_path):
            print(
                f"错误: 服务器路径 '{server_path}' 未找到或无效 '{name}'。请检查配置或仓库克隆步骤。"
            )
            return

    # 2. 运行安装命令
    install_commands = server_config.get("install_commands", [])
    if not install_commands:
        print(f"[{name}] 未指定安装命令。跳过安装步骤。")
    else:
        print(f"[{name}] 执行安装命令...")
        # 确定执行命令的工作目录
        # 对于 source_code，使用其 path；对于其他类型，可能不需要特定 cwd
        cwd = server_path if server_type == "source_code" else None

        for command in install_commands:
            process = run_command(command, cwd=cwd, server_name=f"{name}-安装")
            if process:
                # 同步等待安装命令完成，并打印输出
                stdout_lines = []
                stderr_lines = []
                import subprocess

                try:
                    # 使用 communicate() 获取所有输出并等待进程结束
                    stdout, stderr = process.communicate(timeout=300)  # 5分钟超时
                    stdout_lines = stdout.strip().splitlines()
                    stderr_lines = stderr.strip().splitlines()

                    if stdout_lines:
                        print(f"[{name}-安装-out] {' '.join(stdout_lines)}")
                    if process.returncode != 0:
                        print(
                            f"错误: 为 '{name}' 执行安装命令时出错。命令失败: {command}"
                        )
                        if stderr_lines:
                            print(f"[{name}-安装-err] {' '.join(stderr_lines)}")
                        return  # 安装失败则停止
                    else:
                        print(f"[{name}] 命令 '{command}' 成功完成。")

                except subprocess.TimeoutExpired:
                    print(f"错误: 为 '{name}' 执行安装命令 '{command}' 超时。")
                    stop_process(f"{name}-安装", process)  # 尝试停止超时的进程
                    return
                except Exception as e:
                    print(f"错误: 等待安装命令 '{command}' 完成时发生意外错误: {e}")
                    # 尝试读取剩余输出（如果可能）
                    try:
                        stdout, stderr = process.communicate()
                    except:
                        pass
                    if process.poll() is None:  # 如果还在运行，尝试停止
                        stop_process(f"{name}-安装", process)
                    return
            else:
                print(f"错误: 无法为 '{name}' 启动安装命令 '{command}'。")
                return  # 无法执行命令则停止

    print(f"--- 服务器设置完成: {name} ---")


def start_server(server_config: dict, watch: bool = False):
    """启动指定服务器"""
    name = server_config.get("name", "未知服务器")
    if not server_config.get("enabled", True):
        print(f"服务器 '{name}' 已禁用。跳过启动。")
        return

    # 检查是否已在本脚本实例中运行
    if name in RUNNING_PROCESSES and RUNNING_PROCESSES[name].poll() is None:
        print(
            f"服务器 '{name}' 似乎已由此脚本启动 (PID: {RUNNING_PROCESSES[name].pid})。"
        )
        # 可以选择检查端口是否真的在监听作为二次确认
        port = server_config.get("sse_port") or server_config.get("port")
        if port and is_port_in_use(int(port)):
            print(f"端口 {port} 正在监听。无需重复启动。")
            return
        else:
            print(
                f"警告: 进程记录存在，但端口 {port} 未监听。可能进程已崩溃或未完全启动。尝试重新启动..."
            )
            # 清理旧记录，允许重新启动
            del RUNNING_PROCESSES[name]

    print(f"\n--- 正在启动服务器: {name} ---")
    server_type = server_config.get("type")
    server_path = server_config.get("path")  # load_config 应该已经修正了这个路径

    # 检查路径 (仅 source_code 类型)
    if server_type == "source_code":
        if not server_path or not os.path.isdir(server_path):
            print(
                f"错误: 服务器路径 '{server_path}' 未找到 '{name}'。请先运行 'setup'。"
            )
            return

    # 准备启动命令
    start_command = server_config.get("start_command")
    if not start_command:
        print(f"错误: 服务器 '{name}' 未定义 'start_command'。")
        return

    # 处理 SSE 包装命令 (如果存在)
    sse_start_command_template = server_config.get("sse_start_command")
    final_start_command = start_command  # 默认为原始命令
    if sse_start_command_template:
        sse_host = server_config.get("sse_host", "localhost")
        sse_port = server_config.get("sse_port")
        allow_origin = server_config.get("allow_origin", "*")
        if not sse_port:
            print(
                f"错误: 服务器 '{name}' 定义了 'sse_start_command' 但缺少 'sse_port'。"
            )
            return

        # 替换占位符
        try:
            final_start_command = sse_start_command_template.format(
                sse_host=sse_host,
                sse_port=sse_port,
                allow_origin=allow_origin,
                start_command=start_command,  # 原始命令作为参数传入
            )
            print(f"[{name}] 使用 SSE 包装命令: {final_start_command}")
        except KeyError as e:
            print(
                f"错误: 替换 'sse_start_command' 中的占位符 {{{e}}} 时出错。请检查模板。"
            )
            return
    else:
        print(f"[{name}] 使用启动命令: {final_start_command}")

    # 获取环境变量
    env = server_config.get("env", {})

    # 确定工作目录
    cwd = server_path if server_type == "source_code" else None

    # 启动进程
    process = run_command(final_start_command, cwd=cwd, env=env, server_name=name)

    if process:
        RUNNING_PROCESSES[name] = process
        port_to_check = server_config.get("sse_port") or server_config.get("port")
        print(
            f"服务器 '{name}' 启动命令已执行 (PID: {process.pid})。"
            f"{f' 预期监听端口: {port_to_check}' if port_to_check else ''}"
        )

        # 启动输出流线程
        stdout_thread, stderr_thread = stream_output(process, name)

        if watch:
            print(f"[{name}] 进入监视模式。按 Ctrl+C 停止。")
            try:
                # 等待进程结束
                process.wait()
            except KeyboardInterrupt:
                print(f"\n[{name}] 检测到 Ctrl+C。正在停止服务器...")
                stop_process(name, process)  # 直接调用 stop_process
            except Exception as e:
                print(f"\n[{name}] 等待进程时发生错误: {e}。尝试停止...")
                stop_process(name, process)
            finally:
                # 确保线程结束 (虽然是 daemon，join 一下更保险)
                if stdout_thread.is_alive():
                    stdout_thread.join(timeout=1)
                if stderr_thread.is_alive():
                    stderr_thread.join(timeout=1)
                if name in RUNNING_PROCESSES:
                    del RUNNING_PROCESSES[name]  # 从运行列表中移除
                print(f"--- 服务器 '{name}' 已停止 (监视模式结束)。 ---")
        else:
            # 非 watch 模式，后台运行
            # 短暂等待并检查进程是否快速失败
            time.sleep(3)  # 等待 3 秒让服务有机会启动或失败
            if process.poll() is not None:  # 进程已退出
                print(
                    f"错误: 服务器 '{name}' (PID: {process.pid}) 似乎在启动后不久就退出了 (退出码: {process.poll()})。"
                )
                # 尝试读取最后的错误输出 (可能已被 stream_output 线程读取)
                # 这里可以考虑让 stream_output 收集最后几行错误信息
                if name in RUNNING_PROCESSES:
                    del RUNNING_PROCESSES[name]  # 从运行列表中移除
            else:
                print(f"服务器 '{name}' (PID: {process.pid}) 正在后台运行。")
                # 检查端口是否按预期监听 (可选但推荐)
                if port_to_check:
                    time.sleep(2)  # 再等一会确保服务监听
                    if is_port_in_use(int(port_to_check)):
                        print(f"[{name}] 端口 {port_to_check} 确认正在监听。")
                    else:
                        print(
                            f"警告: 服务器 '{name}' 正在运行，但端口 {port_to_check} 未按预期监听。"
                        )

    else:
        print(f"错误: 无法启动服务器 '{name}'。")


def stop_server(server_config: dict):
    """停止指定服务器 (如果由当前脚本启动)"""
    name = server_config.get("name", "未知服务器")
    print(f"\n--- 正在停止服务器: {name} ---")
    if name in RUNNING_PROCESSES:
        process = RUNNING_PROCESSES[name]
        stop_process(name, process)  # 使用重构后的停止函数
        # 无论停止是否成功，都从监控列表移除
        del RUNNING_PROCESSES[name]
    else:
        print(f"服务器 '{name}' 未在当前脚本的管理下运行 (或已被停止)。")
        # 注意：此函数无法停止不由当前脚本实例启动的进程
        # 如果需要停止任何监听特定端口的进程，需要更复杂的逻辑 (例如查找PID)


def status_servers():
    """显示所有已配置服务器的状态"""
    print("\n--- MCP 服务器状态 ---")
    config = load_config()
    servers = config.get("servers", [])

    if not servers:
        print("配置文件中未定义任何服务器。")
        return

    print(
        f"{'名称':<20} {'启用':<7} {'类型':<12} {'端口':<6} {'状态':<25} {'PID (本实例)':<15} {'路径'}"
    )
    print("-" * 100)  # 调整分隔线长度

    # 清理 RUNNING_PROCESSES 中已经结束的进程
    for name, process in list(RUNNING_PROCESSES.items()):
        if process.poll() is not None:
            print(f"[状态检查] 清理已结束的进程记录: {name} (PID: {process.pid})")
            del RUNNING_PROCESSES[name]

    for server in servers:
        name = server.get("name", "N/A")
        enabled = str(server.get("enabled", True))
        stype = server.get("type", "N/A")
        # 优先使用 sse_port，其次是 port
        port = server.get("sse_port") or server.get("port")
        path = server.get("path", "N/A")
        status = "未知"
        pid_str = "N/A"

        if enabled == "True":
            if port:
                port_int = int(port)
                if is_port_in_use(port_int):
                    status = f"运行中 (端口 {port} 监听)"
                    # 检查是否由本实例启动
                    if name in RUNNING_PROCESSES:
                        pid_str = str(RUNNING_PROCESSES[name].pid)
                    else:
                        pid_str = "(外部启动?)"
                else:
                    status = "已停止"
                    # 如果在本实例中有记录但端口未监听，说明可能启动失败或崩溃
                    if name in RUNNING_PROCESSES:
                        exit_code = RUNNING_PROCESSES[name].poll()
                        status = f"错误/已退出 (代码: {exit_code})"
                        pid_str = str(RUNNING_PROCESSES[name].pid)
                        # 可以考虑在这里清理 RUNNING_PROCESSES[name]
            else:
                status = "无端口配置"  # 对于没有端口的服务，状态未知
                if name in RUNNING_PROCESSES:  # 但如果本实例启动了它...
                    if RUNNING_PROCESSES[name].poll() is None:
                        status = "运行中 (无端口检查)"
                        pid_str = str(RUNNING_PROCESSES[name].pid)
                    else:
                        exit_code = RUNNING_PROCESSES[name].poll()
                        status = f"已退出 (代码: {exit_code})"
                        pid_str = str(RUNNING_PROCESSES[name].pid)

        else:  # enabled == "False"
            status = "已禁用"

        print(
            f"{name:<20} {enabled:<7} {stype:<12} {str(port):<6} {status:<25} {pid_str:<15} {path}"
        )


def stop_all_servers():
    """停止所有由当前脚本实例启动的服务器"""
    print("\n--- 正在停止所有受管服务器 ---")
    if not RUNNING_PROCESSES:
        print("当前脚本未管理任何正在运行的服务器。")
        return

    # 创建副本进行迭代，因为 stop_process 会修改字典
    processes_to_stop = list(RUNNING_PROCESSES.items())

    for name, process in processes_to_stop:
        print(f"请求停止: {name} (PID: {process.pid})")
        stop_process(name, process)

    # 确认清理 (理论上 stop_process 内部已处理，但以防万一)
    remaining = list(RUNNING_PROCESSES.keys())
    if remaining:
        print(f"警告: 以下服务器可能未能完全停止或清理: {', '.join(remaining)}")
    else:
        print("所有受管服务器已处理停止请求。")

    RUNNING_PROCESSES.clear()  # 确保清空


def list_servers():
    """列出所有已配置的服务器 (打印配置)"""
    print("\n--- 已配置的 MCP 服务器 ---")
    config = load_config()
    print(json.dumps(config, indent=2, ensure_ascii=False))


# --- Signal Handling for Graceful Exit ---


def setup_signal_handlers():
    """设置信号处理程序以尝试优雅地停止所有服务器"""

    def signal_handler(sig, frame):
        print(f"\n检测到信号 {signal.Signals(sig).name}。正在尝试停止所有受管服务器...")
        stop_all_servers()
        print("退出脚本。")
        sys.exit(0)

    # 处理 SIGINT (Ctrl+C) 和 SIGTERM (kill 命令默认发送的信号)
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        # 在 Windows 上，SIGBREAK 可能也相关，但 CTRL_BREAK_EVENT 用于子进程
        if os.name == "nt":
            # signal.signal(signal.SIGBREAK, signal_handler) # 通常不需要处理主脚本的 SIGBREAK
            pass
    except ValueError:
        print("警告: 在非主线程中运行，无法设置信号处理程序。")
    except AttributeError:
        print("警告: 当前环境不支持信号处理 (例如某些 Windows 环境或受限环境)。")
