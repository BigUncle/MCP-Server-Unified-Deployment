## MCP Server Unified Deployment

[English](#mcp-server-unified-deployment) | [中文](#mcp服务器统一部署工具)

A unified deployment and management tool for MCP (Model Context Protocol) servers. This project converts MCP servers deployed in various forms (uvx, npx, etc.) into a standardized SSE (Server-Sent Events) deployment, facilitating unified invocation by different tools.

**Table of Contents**

-   [Features](#features)
-   [Prerequisites](#prerequisites)
-   [Installation](#installation)
-   [Configuration](#configuration)
    -   [Server Types](#server-types)
    -   [Environment Variables](#environment-variables-1)
-   [Usage](#usage)
    -   [Basic Commands](#basic-commands)
    -   [Example](#example)
    -   [Integrate Configuration Generator Script](#integrate-configuration-generator-script)
    -   [Monitoring](#monitoring)
-   [Client Configuration](#client-configuration)
-   [Directory Structure](#directory-structure)
-   [Docker Support](#docker-support)
    -   [Docker Deployment Options](#docker-deployment-options)
    -   [Using Docker for Development](#using-docker-for-development)
    -   [Production Deployment with Pre-Built Images](#production-deployment-with-pre-built-images)
    -   [Production Deployment with Docker Compose](#production-deployment-with-docker-compose)
-   [Contributing](#contributing)
-   [License](#license)

**中文导航**

-   [MCP服务器统一部署工具](#mcp服务器统一部署工具)
    - [特性](#特性)
    - [前提条件](#前提条件)
    - [安装](#安装)
    - [配置](#配置)
        - [服务器类型](#服务器类型)
        - [环境变量](#环境变量-1)
    - [使用方法](#使用方法)
        - [基本命令](#基本命令)
        - [示例](#示例)
    - [客户端配置](#客户端配置)
    - [目录结构](#目录结构)
    - [Docker支持](#docker支持)
    - [贡献](#贡献)
    - [许可证](#许可证)

### Features

- **Unified Management**: Manage multiple MCP servers from a single interface
- **SSE Standardization**: Convert various MCP server implementations to SSE protocol
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Flexible Configuration**: Easy configuration for different server types and environments


# MCP Server Unified Deployment

## Features

- **Unified Management**: Manage multiple MCP servers from a single interface
- **SSE Standardization**: Convert various MCP server implementations to SSE protocol
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Flexible Configuration**: Easy configuration for different server types and environments
- **Process Management**: Start, stop, restart, and check status of MCP servers
- **Docker Support**: Comprehensive Docker deployment and management options
- **GitHub Workflow Integration**: CI/CD pipeline for automated testing and deployment

## Prerequisites

- Python 3.12+
- Git (for source code type servers)
- Node.js and npm (for Node.js based servers)
- uv (for dependency management)
- pipx (for installing `mcp-proxy`, it is recommended that `mcp-proxy` be installed through `pipx`).
- uvx (for uvx based servers)

- Docker and Docker Compose (optional, for containerized deployment)

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
  "env": {},                    // Environment variables for the server
  "working_directory": "",      // Optional working directory for running commands
  "repo_url": "",               // For source_code type, git repository URL
  "branch": "main"              // For source_code type, git branch to use
}
```

### Server Types

- **uvx**: Servers deployed using uvx
- **node**: Node.js based servers
- **source_code**: Servers that need to be built from source code
- **docker**: Servers that run in Docker containers

### Environment Variables

You can specify environment variables for each server in the `env` section:

```json
"env": {
  "NODE_ENV": "production",
  "DEBUG": "true"
}
```

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

## Integrate Configuration Generator Script

The `integrate_config_generator.py` script is used to generate client-specific configuration files based on the `mcp_servers.json` file. It reads the `mcp_servers.json` file and generates client-specific configuration files in the `config/client_configs/` directory.

### Usage

```bash
python scripts/integrate_config_generator.py
```

This script will create configuration files for each client found in the `mcp_servers.json` file and place them in the `config/client_configs/` directory. The generated configuration files are named `mcp_<client>_*.json`, where `<client>` is the name of the client. You can then use these configuration files to configure your client.


## Directory Structure

```
.
├── config
│   ├── host_info.json            # Host info cache (auto-generated, used for network/config assist)
│   ├── mcp_servers.example.json  # Example MCP server configuration
│   ├── mcp_servers.json          # Main MCP server configuration
│   └── client_configs/           # Client configuration files generated by integrate_config_generator.py
|          └── mcp_<client>_*.json # Client configuration files
├── docker
│   ├── docker-compose.yml        # Production Docker Compose configuration
│   ├── Dockerfile                # Production Docker image build file
│   ├── entrypoint.sh             # Container entrypoint script
│   └── README.md                 # Docker-related documentation
├── docker-dev
│   ├── docker-compose.yml        # Development Docker Compose configuration
│   ├── Dockerfile                # Development Docker image build file
│   └── .devcontainer             # Devcontainer directory
│       └─ devcontainer.json      # VS Code devcontainer configuration
├── docs/                         # Project documentation
├── logs/                         # Server runtime logs
├── mcp-data/                     # Runtime data storage (if needed)
├── mcp-servers/                  # MCP server source code (if any)
├── node-modules/                 # Node.js dependencies (if needed)
├── npm-global                    # Global npm dependencies and cache
│   ├── bin
│   ├── _cacache
│   ├── lib
│   ├── _logs
│   ├── _npx
├── pids/                         # Process ID files
├── scripts
│   ├── mcp_manager               # Management modules (commands, config, process utils, etc.)
│   │   ├── commands.py           # Command modules
│   │   ├── config.py             # Configuration modules
│   │   └── process_utils.py      # Process utilities
│   ├── container_startup.py      # Container startup helper script
│   ├── detect_host_ip.py         # Host IP detection script
│   ├── integrate_config_generator.py # Client config generator script
│   ├── manage_mcp.py             # Main MCP management script
│   └── setup_env.py              # Environment setup script
├── uv-cache/                     # Python dependency cache (auto-generated by uv)
├── README.md                     # Project documentation
└── requirements.txt              # Python dependency list
```

**Notes:**
- `config/client_configs/`: Stores client-specific configuration files generated by `integrate_config_generator.py`.
- `config/host_info.json`: Auto-generated host info cache, used for network configuration and automation.
- `docker/` and `docker-dev/`: Production and development Docker configurations for easy environment switching.
- `mcp-servers/`: Place your custom or extended MCP server source code here if needed.
- `scripts/`: All management, automation, and configuration scripts. The main entry point is `manage_mcp.py`.
- Other directories like `logs/`, `pids/`, `mcp-data/`, `uv-cache/` are for runtime or cache data and do not require manual maintenance.


## Docker Support

This project provides comprehensive Docker support for both development and deployment environments.

### Docker Deployment Options

1. **Development Environment**:
   - A development container with all necessary tools pre-installed
   - Visual Studio Code integration via devcontainer configuration

2. **Production Deployment**:
   - Multi-container setup with Docker Compose
   - Individual server containers with proper isolation
   - Persistent volume management for data and configurations

### Using Docker for Development

To start the development environment:

```bash
# Start the development container
docker compose -f docker-dev/docker-compose.yml up -d

# Connect to the container
docker exec -it mcp-dev zsh
```
### Production Deployment with pre-built images

To deploy in a production environment, you can use pre-built images from Docker Hub.
```bash
docker pull biguncle2018/mcp-server-unified:latest

# Start the production container
docker run -d --name mcp-server-unified biguncle2018/mcp-server-unified:latest

# View logs
docker logs -f mcp-server-unified

# Connect to the container
docker exec -it mcp-server-unified zsh
```

### Production Deployment with Docker Compose

To deploy in a production environment:
#### Configuration
Copy the example configuration file:

```bash
cp config/mcp_servers.example.json config/mcp_servers.json
```
Or edit the configuration file as needed.

#### Modify Dockerfile
If necessary, modify the Dockerfile or `docker-compose.yml` in the `docker/` directory to suit your needs.
For example, you may need to adjust the `ENTRYPOINT` or `REAL_HOST_IP` variables or `TIME ZONE` variables.

#### Build and Start Containers

```bash
# Build and start all containers
docker compose -f docker/docker-compose.yml up -d

# View logs
docker compose -f docker/docker-compose.yml logs -f

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
- **Docker支持**：全面的Docker部署和管理选项
- **GitHub工作流集成**：自动化测试和部署的CI/CD管道

## 前提条件

- Python 3.12+
- Git（用于源代码类型服务器）
- Node.js和npm（用于基于Node.js的服务器）
- uv（用于依赖管理）
- pipx（用于安装mcp-proxy）
- uvx（用于基于uvx的服务器）
- Docker和Docker Compose（可选，用于容器化部署）

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
uv venv --python=3.12

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
  "env": {},                    // 服务器的环境变量
  "working_directory": "",      // 运行命令的可选工作目录
  "repo_url": "",               // 对于source_code类型，git仓库URL
  "branch": "main"              // 对于source_code类型，使用的git分支
}
```

### 服务器类型

- **uvx**：使用uvx部署的服务器
- **node**：基于Node.js的服务器
- **source_code**：需要从源代码构建的服务器
- **docker**：在Docker容器中运行的服务器

### 环境变量

您可以在`env`部分为每个服务器指定环境变量：

```json
"env": {
  "NODE_ENV": "production",
  "DEBUG": "true"
}
```

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
├── config/                       # 配置文件
│   ├── host_info.json            # 主机信息缓存文件（自动生成/用于辅助配置）
│   ├── mcp_servers.example.json  # MCP服务器配置示例
│   ├── mcp_servers.json          # MCP服务器主配置文件
|   └── client_configs/      # 由integrate_config_generator.py生成的客户端配置
|        └── mcp_<client>_*.json # 客户端配置文件
├── docker
│   ├── docker-compose.yml        # 生产环境 Docker Compose 配置
│   ├── Dockerfile                # 生产环境 Docker 镜像构建文件
│   ├── entrypoint.sh             # 容器入口脚本
│   └── README.md                 # Docker 相关说明文档
├── docker-dev
│   ├── docker-compose.yml        # 开发环境 Docker Compose 配置
│   ├── Dockerfile                # 开发环境 Docker 镜像构建文件
│   └── .devcontainer             # 容器目录
│       └─ devcontainer.json      # devcontainer.json
├── docs/                         # 项目文档目录
├── logs/                         # 服务器运行日志目录
├── mcp-data/                     # 运行时数据存储目录（如有需要）
├── mcp-servers/                  # MCP服务器源代码目录（如有需要）
├── node-modules/                 # Node.js 依赖目录（如有需要）
├── npm-global                    # 全局 npm 依赖及缓存目录
│   ├── bin
│   ├── _cacache
│   ├── lib
│   ├── _logs
│   ├── _npx
├── pids/                         # 进程ID文件目录
├── scripts
│   ├── mcp_manager/              # 管理模块（如命令、配置、进程工具等）
│   │   ├── commands.py           # 
│   │   ├── config.py             # 配置管理
│   │   └── process_utils.py      # 进程工具
│   ├── container_startup.py      # 容器启动辅助脚本
│   ├── detect_host_ip.py         # 主机IP检测脚本
│   ├── integrate_config_generator.py # 客户端配置生成脚本
│   ├── manage_mcp.py             # MCP统一管理主脚本
│   └── setup_env.py              # 环境初始化脚本
├── uv-cache/                     # Python依赖缓存目录（uv工具自动生成）
├── README.md                     # 项目说明文档
└── requirements.txt              # Python依赖清单
```

## Docker支持

本项目为开发和部署环境提供全面的Docker支持。

### Docker部署选项

1. **开发环境**：
   - 预装所有必要工具的开发容器
   - 通过devcontainer配置集成Visual Studio Code

2. **生产部署**：
   - 使用Docker Compose的多容器设置
   - 具有适当隔离的单独服务器容器
   - 用于数据和配置的持久卷管理

### 使用Docker进行开发

启动开发环境：

```bash
# 启动开发容器
docker compose -f docker-dev/docker-compose.yml up -d

# 连接到容器
docker exec -it mcp-dev zsh
```
### 拉取项目镜像生产部署

见 [镜像部署推荐流程](docs/镜像部署推荐流程.md)

### 使用Docker compose 进行生产部署

在生产环境中部署：

#### 配置

```bash
cp config/mcp_servers.example.json config/mcp_servers.json
```
或者根据需求编辑配置文件。

#### 修改Dockerfile
有需要时，修改`docker/`目录中的`Dockerfile`或`docker-compose.yml`以适应您的需求。
比如，您可能需要调整`ENTRYPOINT`或`REAL_HOST_IP`变量或`TIME ZONE`变量。

#### 构建和启动容器
```bash
# 构建并启动所有容器
docker compose -f docker/docker-compose.yml up -d

# 查看日志
docker compose -f docker/docker-compose.yml logs -f
```

## 贡献

欢迎贡献！详情请参阅[CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

本项目采用MIT许可证 - 详情请参阅[LICENSE](LICENSE)文件。
