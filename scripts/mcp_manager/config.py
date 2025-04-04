"""MCP服务器配置管理模块

该模块提供了MCP服务器配置的加载和保存功能。
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
    """加载服务器配置并自动修正路径"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"错误: 配置文件未找到于 {CONFIG_FILE}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"错误: 配置文件 {CONFIG_FILE} 不是有效的 JSON。")
        sys.exit(1)

    updated = False
    for server in config.get("servers", []):
        # 仅处理 source_code 类型的服务器路径
        if server.get("type") == "source_code":
            if server.get("repo") and server.get("subdir") is not None:
                repo_name = server["repo"].split("/")[-1].replace(".git", "")
                repo_base_path = os.path.join(SOURCE_CODE_SERVERS_DIR, repo_name)

                if server["subdir"] == ".":
                    expected_path = repo_base_path
                else:
                    expected_path = os.path.join(repo_base_path, server["subdir"])

                # 规范化路径以进行比较
                expected_path_norm = os.path.normpath(expected_path).replace("\\", "/")
                current_path_norm = (
                    os.path.normpath(server.get("path", "")).replace("\\", "/")
                    if server.get("path")
                    else ""
                )

                # 如果配置中的path不正确或为空，则更新为预期路径
                if current_path_norm != expected_path_norm:
                    print(
                        f"更新服务器 '{server['name']}' 的路径为: {expected_path_norm}"
                    )
                    server["path"] = expected_path_norm
                    updated = True
            elif not server.get("path"):
                print(
                    f"警告: source_code 服务器 '{server['name']}' 缺少 'repo'/'subdir' 或 'path' 配置。"
                )

    # 如果有更新，则保存配置
    if updated:
        save_config(config)

    return config


def save_config(config):
    """保存服务器配置"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"配置已更新并保存至 {CONFIG_FILE}")
    except IOError:
        print(f"错误: 无法写入配置文件 {CONFIG_FILE}")
