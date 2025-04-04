# MCP Server Unified Deployment

[English](#mcp-server-unified-deployment) | [中文](#mcp服务器统一部署工具)

A unified deployment and management tool for MCP (Model Context Protocol) servers. This project converts MCP servers deployed in various forms (uvx, npx, etc.) into a standardized SSE (Server-Sent Events) deployment, facilitating unified invocation by different tools.

## Features

- **Unified Management**: Manage multiple MCP servers from a single interface
- **SSE Standardization**: Convert various MCP server implementations to SSE protocol
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Flexible Configuration**: Easy configuration for different server types and environments
- **Process Management**: Start, stop, restart, and check status of MCP servers

## Prerequisites

- Python 12+
- Git (for source code type servers)
- Node.js and npm (for Node.js based servers)
- uv (for dependency management)
- pipx (for installing mcp-proxy)
- uvx (for uvx based servers)

## Installation

1. Clone this repository:

```bash
git clone https://github.com/BigUncle/MCP-Server-Unified-Deployment.git
cd MCP-Server-Unified-Deployment
```

2. Set up a virtual environment and install dependencies using uv:

```bash
# Install uv if you don't have it
pip install uv


# Create a virtual environment
uv venv --python=3.12

# install from requirements.txt
uv pip install -r requirements.txt
# OR install dependencies with uv
# uv pip install -e .


# Activate the virtual environment (Windows)
.venv\Scripts\activate
# OR Activate the virtual environment (Linux/MacOS)
# source .venv/bin/activate
```

Alternatively, you can use our setup script:

```bash
python scripts/setup_env.py
```

3. Install mcp-proxy using pipx (recommended):

```bash
# Install pipx if you don't have it
pip install pipx
pipx ensurepath

# Install mcp-proxy
pipx install mcp-proxy
```

4. Create your configuration file:

```bash
cp config/mcp_servers.example.json config/mcp_servers.json
```

5. Edit the configuration file to match your requirements.

## Configuration

The configuration file (`config/mcp_servers.json`) contains settings for all MCP servers you want to manage. Each server entry includes:

```json
{
  "name": "server-name",         // Unique name for the server
  "enabled": true,              // Whether the server is enabled
  "type": "uvx",                // Server type (uvx, node, source_code, etc.)
  "sse_host": "localhost",      // Host for SSE endpoint
  "sse_port": 23001,            // Port for SSE endpoint
  "allow_origin": "*",          // CORS setting for SSE endpoint
  "install_commands": [          // Commands to install the server
    "uvx -v mcp-server-fetch"
  ],
  "sse_start_command": "mcp-proxy {start_command} --sse-host={sse_host} --sse-port={sse_port} --allow-origin='{allow_origin}' ",  // Command template for SSE mode
  "start_command": "uvx mcp-server-fetch",  // Original start command
  "env": {}                     // Environment variables for the server
}
```

### Server Types

- **uvx**: Servers deployed using uvx
- **node**: Node.js based servers
- **source_code**: Servers that need to be built from source code

## Usage

### Basic Commands

```bash
# Start all enabled servers
python scripts/manage_mcp.py start

# Start a specific server
python scripts/manage_mcp.py start <server-name>

# Stop all servers
python scripts/manage_mcp.py stop

# Stop a specific server
python scripts/manage_mcp.py stop <server-name>

# Restart a specific server
python scripts/manage_mcp.py restart <server-name>

# Check status of all servers
python scripts/manage_mcp.py status
```

### Example

To start the fetch server:

```bash
python scripts/manage_mcp.py start fetch
```

## Directory Structure

```
.
├── config/                  # Configuration files
│   └── mcp_servers.json     # Server configuration
├── logs/                    # Server logs
├── pids/                    # Process ID files
├── scripts/                 # Management scripts
│   ├── manage_mcp.py        # Main management script
│   └── mcp_manager/         # Management modules
└── mcp-servers/             # Source code servers (if any)
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

# MCP服务器统一部署工具

[English](#mcp-server-unified-deployment) | [中文](#mcp服务器统一部署工具)

这是一个用于统一部署和管理MCP（Model Context Protocol）服务器的工具。该项目将以不同形式（uvx、npx等）部署的MCP服务器统一转换为标准化的SSE（Server-Sent Events）部署方式，方便不同工具的统一调用。

## 特性

- **统一管理**：通过单一界面管理多个MCP服务器
- **SSE标准化**：将各种MCP服务器实现转换为SSE协议
- **跨平台**：支持Windows、macOS和Linux
- **灵活配置**：轻松配置不同类型和环境的服务器
- **进程管理**：启动、停止、重启和检查MCP服务器状态

## 前提条件

- Python 3.12+
- Git（用于源代码类型服务器）
- Node.js和npm（用于基于Node.js的服务器）
- uv（用于依赖管理）
- pipx（用于安装mcp-proxy）
- uvx（用于基于uvx的服务器）

## 安装

1. 克隆此仓库：

```bash
git clone https://github.com/BigUncle/MCP-Server-Unified-Deployment.git
cd MCP-Server-Unified-Deployment
```

2. 使用uv设置虚拟环境并安装所需的Python依赖：

```bash
# 如果没有安装uv，先安装uv
pip install uv

# 创建虚拟环境
uv venv

# 使用uv安装依赖
uv pip install -r requirements.txt

# 激活虚拟环境（Windows）
.venv\Scripts\activate
# 或激活虚拟环境（Linux/MacOS）
# source .venv/bin/activate
```

或者，您可以使用我们的设置脚本：

```bash
python scripts/setup_env.py
```

3. 使用pipx安装mcp-proxy（推荐）：

```bash
# 如果没有安装pipx，先安装pipx
pip install pipx
pipx ensurepath

# 安装mcp-proxy
pipx install mcp-proxy
```

4. 创建配置文件：

```bash
cp config/mcp_servers.example.json config/mcp_servers.json
```

5. 编辑配置文件以满足您的需求。

## 配置

配置文件（`config/mcp_servers.json`）包含您想要管理的所有MCP服务器的设置。每个服务器条目包括：

```json
{
  "name": "server-name",         // 服务器的唯一名称
  "enabled": true,              // 服务器是否启用
  "type": "uvx",                // 服务器类型（uvx、node、source_code等）
  "sse_host": "localhost",      // SSE端点的主机
  "sse_port": 23001,            // SSE端点的端口
  "allow_origin": "*",          // SSE端点的CORS设置
  "install_commands": [          // 安装服务器的命令
    "uvx -v mcp-server-fetch"
  ],
  "sse_start_command": "mcp-proxy {start_command} --sse-host={sse_host} --sse-port={sse_port} --allow-origin='{allow_origin}' ",  // SSE模式的命令模板
  "start_command": "uvx mcp-server-fetch",  // 原始启动命令
  "env": {}                     // 服务器的环境变量
}
```

### 服务器类型

- **uvx**：使用uvx部署的服务器
- **node**：基于Node.js的服务器
- **source_code**：需要从源代码构建的服务器

## 使用方法

### 基本命令

```bash
# 启动所有已启用的服务器
python scripts/manage_mcp.py start

# 启动特定服务器
python scripts/manage_mcp.py start <server-name>

# 停止所有服务器
python scripts/manage_mcp.py stop

# 停止特定服务器
python scripts/manage_mcp.py stop <server-name>

# 重启特定服务器
python scripts/manage_mcp.py restart <server-name>

# 检查所有服务器的状态
python scripts/manage_mcp.py status
```

### 示例

启动fetch服务器：

```bash
python scripts/manage_mcp.py start fetch
```

## 目录结构

```
.
├── config/                  # 配置文件
│   └── mcp_servers.json     # 服务器配置
├── logs/                    # 服务器日志
├── pids/                    # 进程ID文件
├── scripts/                 # 管理脚本
│   ├── manage_mcp.py        # 主管理脚本
│   └── mcp_manager/         # 管理模块
└── mcp-servers/             # 源代码服务器（如果有）
```

## 贡献

欢迎贡献！详情请参阅[CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

本项目采用MIT许可证 - 详情请参阅[LICENSE](LICENSE)文件。