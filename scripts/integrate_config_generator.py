#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCP 配置文件生成器
根据mcp_servers.json配置文件生成不同客户端格式的配置文件
支持的格式:
- Cline
- Roo Code
- Cherry Studio
"""

import json
import os
import random
import string
import time
from pathlib import Path

# 从上级目录导入config模块
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp_manager.config import load_config

# 配置文件输出目录
CONFIG_OUTPUT_DIR = Path(__file__).parent.parent / "config" / "client_configs"

# 确保输出目录存在
CONFIG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 不同客户端的默认配置
CLIENT_DEFAULTS = {
    "cline": {
        "timeout": 60,
        "transportType": "sse",
        "autoApprove": []
    },
    "roo_code": {
        "alwaysAllow": []
    },
    "cherry_studio": {
        "isActive": True,
        "description": ""
    }
}

# 不同服务器的默认函数授权列表
DEFAULT_ALLOWED_FUNCTIONS = {
    "filesystem": [
        "read_file", "read_multiple_files", "write_file", "edit_file",
        "create_directory", "list_directory", "directory_tree", "move_file",
        "search_files", "get_file_info", "list_allowed_directories"
    ],
    "github": [
        "create_or_update_file", "search_repositories", "create_repository",
        "get_file_contents", "push_files", "create_issue", "create_pull_request",
        "fork_repository", "create_branch", "list_commits", "list_issues", 
        "update_issue", "add_issue_comment", "search_code", "search_issues",
        "search_users", "get_issue", "get_pull_request", "list_pull_requests",
        "create_pull_request_review", "merge_pull_request", "get_pull_request_files",
        "get_pull_request_status", "update_pull_request_branch", "get_pull_request_comments",
        "get_pull_request_reviews"
    ],
    "firecrawl": [
        "firecrawl_scrape", "firecrawl_map", "firecrawl_crawl", "firecrawl_batch_scrape",
        "firecrawl_check_batch_status", "firecrawl_check_crawl_status", "firecrawl_search",
        "firecrawl_extract", "firecrawl_deep_research", "firecrawl_generate_llmstxt"
    ],
    "duckduckgo": [
        "search", "fetch_content"
    ],
    "amap": [
        "search", "fetch_content", "maps_regeocode", "maps_geo", "maps_ip_location",
        "maps_weather", "maps_search_detail", "maps_bicycling", "maps_direction_walking",
        "maps_direction_driving", "maps_direction_transit_integrated", "maps_distance",
        "maps_text_search", "maps_around_search"
    ]
}

def generate_random_id(length=20):
    """生成随机ID，用于Cherry Studio配置"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_server_ip_port(server_config):
    """从服务器配置中提取IP和端口"""
    host = server_config.get("sse_host", "127.0.0.1")
    # 如果sse_host是0.0.0.0，使用127.0.0.1作为客户端连接地址
    if host == "0.0.0.0":
        host = "127.0.0.1"
    port = server_config.get("sse_port", "3000")
    return host, port

def generate_cline_config(servers_config):
    """生成Cline格式的配置文件"""
    config = {"mcpServers": {}}
    
    for server in servers_config["servers"]:
        if not server.get("enabled", True):
            # 如果服务器被禁用，则设置disabled标志
            config["mcpServers"][server["name"]] = {
                "disabled": True
            }
            continue
        
        host, port = get_server_ip_port(server)
        url = f"http://{host}:{port}/sse"
        
        server_config = {
            "timeout": 60,
            "url": url,
            "transportType": "sse"
        }
        
        # 添加自动允许的函数列表
        if server["name"] in DEFAULT_ALLOWED_FUNCTIONS:
            server_config["autoApprove"] = DEFAULT_ALLOWED_FUNCTIONS[server["name"]]
        
        config["mcpServers"][server["name"]] = server_config
    
    return config

def generate_roo_code_config(servers_config):
    """生成Roo Code格式的配置文件"""
    config = {"mcpServers": {}}
    
    for server in servers_config["servers"]:
        if not server.get("enabled", True):
            # 如果服务器被禁用，则设置disabled标志
            config["mcpServers"][server["name"]] = {
                "url": "",
                "disabled": True,
                "alwaysAllow": []
            }
            continue
        
        host, port = get_server_ip_port(server)
        url = f"http://{host}:{port}/sse"
        
        server_config = {
            "url": url
        }
        
        # 添加自动允许的函数列表，在Roo Code中叫做alwaysAllow
        if server["name"] in DEFAULT_ALLOWED_FUNCTIONS:
            server_config["alwaysAllow"] = DEFAULT_ALLOWED_FUNCTIONS[server["name"]]
        
        config["mcpServers"][server["name"]] = server_config
    
    return config

def generate_cherry_studio_config(servers_config):
    """生成Cherry Studio格式的配置文件"""
    config = {"mcpServers": {}}
    
    # 增加一个mcp-auto-install条目
    config["mcpServers"]["cPqOEdSHLwBLnukhxTppp"] = {
        "isActive": True,
        "name": "mcp-auto-install",
        "description": "Automatically install MCP services (Beta version)",
        "baseUrl": "",
        "command": "npx",
        "args": ["-y", "@mcpmarket/mcp-auto-install", "connect", "--json"],
        "registryUrl": "https://registry.npmmirror.com",
        "env": {}
    }
    
    for server in servers_config["servers"]:
        server_id = generate_random_id()
        
        # 如果服务器被禁用，则设置isActive为false
        isActive = server.get("enabled", True)
        
        host, port = get_server_ip_port(server)
        url = f"http://{host}:{port}/sse"
        
        server_config = {
            "isActive": isActive,
            "name": server["name"],
            "description": server.get("description", server["name"]),
            "baseUrl": url
        }
        
        config["mcpServers"][server_id] = server_config
    
    return config

def save_config_to_file(config, filename):
    """保存配置到文件"""
    file_path = CONFIG_OUTPUT_DIR / filename
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return file_path

def generate_all_configs():
    """生成所有客户端配置文件"""
    # 加载服务器配置
    servers_config = load_config()
    
    # 生成各种格式的配置
    cline_config = generate_cline_config(servers_config)
    roo_code_config = generate_roo_code_config(servers_config)
    cherry_studio_config = generate_cherry_studio_config(servers_config)
    
    # 生成带时间戳的文件名
    timestamp = time.strftime("%Y%m%d%H%M%S")
    
    # 保存配置文件
    cline_path = save_config_to_file(cline_config, f"mcp_cline_{timestamp}.json")
    roo_code_path = save_config_to_file(roo_code_config, f"mcp_roo_code_{timestamp}.json")
    cherry_studio_path = save_config_to_file(cherry_studio_config, f"mcp_cherry_studio_{timestamp}.json")
    
    # 同时保存一份最新的配置（不带时间戳）
    latest_cline_path = save_config_to_file(cline_config, "mcp_cline_latest.json")
    latest_roo_code_path = save_config_to_file(roo_code_config, "mcp_roo_code_latest.json")
    latest_cherry_studio_path = save_config_to_file(cherry_studio_config, "mcp_cherry_studio_latest.json")
    
    return {
        "cline": str(cline_path),
        "roo_code": str(roo_code_path),
        "cherry_studio": str(cherry_studio_path),
        "latest": {
            "cline": str(latest_cline_path),
            "roo_code": str(latest_roo_code_path),
            "cherry_studio": str(latest_cherry_studio_path)
        }
    }

if __name__ == "__main__":
    """命令行执行时直接生成所有配置文件"""
    result = generate_all_configs()
    print("生成客户端配置文件完成:")
    for client_type, path in result.items():
        if client_type != "latest":
            print(f"- {client_type}: {path}")
