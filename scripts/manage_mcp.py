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

# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent / "config" / "mcp_servers.json"
PID_DIR = Path(__file__).parent.parent / "pids"
LOG_DIR = Path(__file__).parent.parent / "logs"

# 确保目录存在
PID_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


# 加载配置
def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# 保存 PID 到文件
def save_pid(name, pid):
    with open(PID_DIR / f"{name}.pid", "w") as f:
        f.write(str(pid))


# 从文件读取 PID
def load_pid(name):
    pid_file = PID_DIR / f"{name}.pid"
    if pid_file.exists():
        with open(pid_file, "r") as f:
            return int(f.read().strip())
    return None


# 删除 PID 文件
def remove_pid_file(name):
    pid_file = PID_DIR / f"{name}.pid"
    if pid_file.exists():
        pid_file.unlink()


# 检查进程是否运行
def is_running(pid):
    try:
        return psutil.pid_exists(pid)
    except psutil.NoSuchProcess:  # Be specific about expected errors
        # PID does not exist, which means it's not running
        return False
    except Exception as e:  # Catch other potential errors during check
        print(f"Error checking PID {pid}: {e}")
        return False  # Assume not running if error occurs


# 检查端口是否被占用
def is_port_in_use(port):
    for conn in psutil.net_connections():
        if conn.laddr.port == port:
            return conn.pid
    return None


# 启动服务器
def start_server(server):
    name = server["name"]

    # 检查是否已在运行
    pid = load_pid(name)
    if pid and is_running(pid):
        print(f"服务器 '{name}' 已经在运行(PID: {pid})")
        return

    # 检查端口是否已被占用
    port = server.get("sse_port", server.get("port"))
    if port:
        existing_pid = is_port_in_use(port)
        if existing_pid:
            print(f"警告: 端口 {port} 已被进程 {existing_pid} 占用")

    # 准备环境变量
    env = os.environ.copy()
    for key, value in server.get("env", {}).items():
        env[key] = value

    # 准备启动命令
    if "sse_host" in server and "sse_port" in server:
        print(f"启动服务器 '{name}' (SSE 模式)")
        # SSE 模式
        cmd = server["sse_start_command"]
        # 替换命令中的占位符
        for key, value in server.items():
            # 总是尝试替换，并将 value 转换为字符串以确保兼容性
            cmd = cmd.replace("{" + key + "}", str(value))
        # 替换环境变量占位符
        for key, value in server.get("env", {}).items():
            # cmd = cmd.replace("{" + key + "}", value)
            cmd += f" -e {key} {value}"
        # 替换启动命令
        start_cmd = server["start_command"]
        cmd = cmd.replace("{start_command}", start_cmd)
    else:
        # 非 SSE 模式
        cmd = server["start_command"]
        if "port" in server:
            cmd = cmd.replace("{port}", str(server["port"]))

    # 创建日志文件
    log_file = open(LOG_DIR / f"{name}.log", "a")

    # 打印启动信息，帮助调试
    print(f"正在启动服务器 '{name}' 执行命令: {cmd}")

    # 启动服务器
    try:
        # Bandit B602: shell=True is a security risk if cmd contains untrusted input.
        print(f"启动命令: {cmd}")

        process = subprocess.Popen(
            cmd, shell=True, env=env, stdout=log_file, stderr=log_file
        )
        save_pid(name, process.pid)
        print(f"已启动服务器 '{name}' (PID: {process.pid})")
    except Exception as e:
        print(f"启动服务器 '{name}' 失败: {e}")


# 停止服务器
def stop_server(server):
    name = server["name"]
    pid = load_pid(name)

    # 检查是否由我们的脚本启动
    if pid and is_running(pid):
        try:
            # 在Windows上使用taskkill杀死进程树
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=False)
            else:
                os.kill(pid, signal.SIGTERM)
                # 给进程一点时间正常退出
                time.sleep(1)
                if is_running(pid):
                    os.kill(pid, signal.SIGKILL)
            print(f"已停止服务器 '{name}' (PID: {pid})")
        except Exception as e:
            print(f"停止服务器 '{name}' 失败: {e}")
        finally:
            remove_pid_file(name)
    else:
        # 检查端口是否被占用，尝试杀死占用进程
        port = server.get("sse_port", server.get("port"))
        if port:
            port_pid = is_port_in_use(port)
            if port_pid:
                try:
                    # 在Windows上使用taskkill杀死进程树
                    if platform.system() == "Windows":
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(port_pid)], check=False
                        )
                    else:
                        os.kill(port_pid, signal.SIGTERM)
                        # 给进程一点时间正常退出
                        time.sleep(1)
                        if is_running(port_pid):
                            os.kill(port_pid, signal.SIGKILL)
                    print(
                        f"已停止在端口 {port} 上运行的服务器 '{name}' (PID: {port_pid})"
                    )
                except Exception as e:
                    print(f"停止端口 {port} 上的进程失败: {e}")
            else:
                print(f"服务器 '{name}' 没有在运行。")
        else:
            print(f"服务器 '{name}' 未在此脚本实例的管理下运行。")


# 重启服务器
def restart_server(server):
    stop_server(server)
    time.sleep(1)  # 等待一秒确保完全停止
    start_server(server)


# 检查服务器状态
def server_status(server):
    name = server["name"]
    enabled = server.get("enabled", True)
    server_type = server.get("type", "unknown")
    host = server.get("host", "localhost")
    port = server.get("sse_port", server.get("port", "N/A"))
    # path = server.get("path", "未知")
    url = f"http://{host}:{port}/sse"

    # 检查 PID 文件
    pid = load_pid(name)
    pid_running = pid and is_running(pid)

    # 检查端口
    port_pid = None
    if port != "N/A":
        port_pid = is_port_in_use(port)

    # 确定状态
    if not enabled:
        status = "已禁用"
        pid_str = "N/A"
    elif port_pid:
        if pid_running and port_pid == pid:
            status = f"运行中 (端口 {port} 监听)"
            pid_str = str(pid)
        else:
            status = f"运行中 (端口 {port} 监听)"
            pid_str = "(外部启动)"
    elif pid_running:
        status = "运行中"
        pid_str = str(pid)
    else:
        status = "已停止"
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


# 获取所有服务器状态
def get_all_status():
    config = load_config()
    status_list = []
    for server in config["servers"]:
        status_list.append(server_status(server))
    return status_list


# 显示状态表格
def print_status_table():
    status_list = get_all_status()

    # 打印表头
    print("\n--- MCP 服务器状态 ---")
    headers = ["名称", "启用", "类型", "端口", "状态", "PID (本实例)", "路径"]
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

    # 打印每个服务器的状态
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


# 启动所有已启用的服务器
def start_all_servers():
    config = load_config()
    for server in config["servers"]:
        if server.get("enabled", True):
            start_server(server)


# 停止所有服务器
def stop_all_servers():
    config = load_config()
    for server in config["servers"]:
        stop_server(server)


# 主函数
def main():
    if len(sys.argv) < 2:
        print("用法: python manage_mcp.py <命令> [服务器名称]")
        print("命令: start, stop, restart, status")
        return

    command = sys.argv[1]
    server_name = sys.argv[2] if len(sys.argv) > 2 else None

    config = load_config()

    if command == "status":
        print_status_table()
        return

    if command == "start" and not server_name:
        # 启动所有已启用的服务器
        start_all_servers()
        return

    if command == "stop" and not server_name:
        # 停止所有服务器
        stop_all_servers()
        return

    if not server_name:
        print("请指定服务器名称")
        return

    # 查找服务器配置
    server = None
    for s in config["servers"]:
        if s["name"] == server_name:
            server = s
            break

    if not server:
        print(f"未找到服务器 '{server_name}'")
        return

    # 检查服务器是否启用
    if not server.get("enabled", True):
        print(f"服务器 '{server_name}' 已禁用。要启用，请修改配置文件。")
        return

    # 执行命令
    if command == "start":
        start_server(server)
    elif command == "stop":
        stop_server(server)
    elif command == "restart":
        restart_server(server)
    else:
        print(f"未知命令: {command}")


if __name__ == "__main__":
    main()
