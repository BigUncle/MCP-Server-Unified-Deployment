# Production Docker Setup for MCP Server

**English Navigation** | **英文导航**

- [Introduction](#production-docker-setup-for-mcp-server)
- [Files](#files)
- [Features](#features)
- [Usage](#usage)
- [Configuration](#configuration)
- [Volumes](#volumes)
- [Environment Variables](#environment-variables)
- [Security Considerations](#security-considerations)
- [Health Checks](#health-checks)

**Chinese Navigation** | **中文导航**

- [介绍](#mcp服务器生产环境docker设置)
- [文件](#文件)
- [特性](#特性)
- [使用方法](#使用方法)
- [配置](#配置)
- [卷挂载](#卷挂载)
- [环境变量](#环境变量)
- [安全考虑](#安全考虑)
- [健康检查](#健康检查)

**Chinese Navigation** | **中文导航**

- [镜像部署](#镜像部署)
- [环境准备](#1-环境准备)
- [拉取镜像](#2-拉取镜像)]
- [运行容器](#3-运行容器)
- [配置参数](#4-配置参数)
- [常见问题排查](#5-常见问题排查)
- [参考资料](#6-参考资料)


This directory contains Docker configuration files optimized for production deployment of the MCP Server Unified Deployment application.

## Files

- `Dockerfile`: Multi-stage build optimized for production with minimal image size
- `docker-compose.yml`: Production-ready compose configuration with appropriate volumes and security settings

## Features

- **Optimized Image Size**: Uses multi-stage builds to minimize the final image size
- **Security Enhancements**: Runs as non-root user with minimal permissions
- **Production-Ready**: Includes only essential runtime dependencies
- **Performance Optimized**: Configured for stable production operation

## Usage

### Building the Image

```bash
cd /path/to/MCP-Server-Unified-Deployment
docker-compose -f docker/docker-compose.yml build
```

### Starting the Container

```bash
docker-compose -f docker/docker-compose.yml up -d
```

### Viewing Logs

```bash
docker-compose -f docker/docker-compose.yml logs -f
```

### Stopping the Container

```bash
docker-compose -f docker/docker-compose.yml down
```

## Configuration

The production setup uses the configuration files from the `config` directory. Make sure to create your configuration file before starting the container:

```bash
cp config/mcp_servers.example.json config/mcp_servers.json
# Edit config/mcp_servers.json with your settings
```

## Volumes

The following volumes are mounted:

- `../config:/app/config:ro`: Configuration files (read-only)
- `../logs:/app/logs`: Log files
- `../pids:/app/pids`: Process ID files


## Environment Variables

You can customize the container by setting environment variables in the `docker-compose.yml` file:

| Variable        | Example Value   | Description                                                                                |
| --------------- | --------------- | ------------------------------------------------------------------------------------------ |
| `TZ`            | Asia/Shanghai   | Timezone for the container.                                                                |
| `LANG`          | zh_CN.UTF-8      | Primary locale setting.                                                                    |
| `LANGUAGE`      | zh_CN:zh         | Locale preference for messages and text.                                                  |
| `LC_ALL`        | zh_CN.UTF-8      | Overrides all locale categories.                                                           |
| `REAL_HOST_IP`  | 192.168.1.8   | Host IP address accessible by external clients. Important for client access.                |
| `EXTERNAL_HOST` | host.docker.internal    |  Alias for REAL_HOST_IP, to access host from container.                             |
| ...             | ...             | Other environment variables (Refer to `docker-compose.yml` for full list) |

>   **Note**: Timezone and locale settings are commented out in the Dockerfile to allow users to customize them according to their specific requirements. You can uncomment and modify these settings in the Dockerfile or set them through environment variables in the docker-compose.yml file.


## Security Considerations

- The application runs as a non-root user (`mcp`), reducing the risk of privilege escalation.
- Container has `no-new-privileges` security option enabled, preventing child processes from gaining additional privileges.
- Only essential packages are installed, minimizing the attack surface.
- Using minimal base images also reduces the attack surface and potential vulnerabilities.
- Consider regularly updating the base image and application dependencies to patch known security vulnerabilities.
- Use the principle of least privilege whenever possible.

## Health Checks

The container includes a health check that verifies the application is running correctly by testing connectivity to port 23001.

# MCP服务器生产环境Docker设置

本目录包含针对MCP服务器统一部署应用程序的生产环境部署优化的Docker配置文件。

## 文件

- `Dockerfile`: 针对生产环境优化的多阶段构建，最小化镜像大小
- `docker-compose.yml`: 具有适当卷挂载和安全设置的生产就绪compose配置

## 特性

- **优化的镜像大小**: 使用多阶段构建最小化最终镜像大小
- **安全增强**: 以非root用户运行，权限最小化
- **生产就绪**: 仅包含必要的运行时依赖
- **性能优化**: 配置为稳定的生产操作

## 使用方法

### 构建镜像

```bash
cd /path/to/MCP-Server-Unified-Deployment
docker-compose -f docker/docker-compose.yml build
```

### 启动容器

```bash
docker-compose -f docker/docker-compose.yml up -d
```

### 查看日志

```bash
docker-compose -f docker/docker-compose.yml logs -f
```

### 停止容器

```bash
docker-compose -f docker/docker-compose.yml down
```

## 配置

生产设置使用`config`目录中的配置文件。确保在启动容器前创建您的配置文件：

```bash
cp config/mcp_servers.example.json config/mcp_servers.json
# 使用您的设置编辑config/mcp_servers.json
```

## 卷挂载

以下卷被挂载：

- `../config:/app/config:ro`: 配置文件（只读）
- `../logs:/app/logs`: 日志文件
- `../pids:/app/pids`: 进程ID文件

## 环境变量

您可以通过在`docker-compose.yml`文件中设置环境变量来自定义容器：

- `TZ`: 时区（默认：Asia/Shanghai）
- `LANG`, `LANGUAGE`, `LC_ALL`: 语言环境设置

> **注意**：Dockerfile中的时区和语言环境设置已被注释，以便用户根据自己的特定需求进行自定义。您可以在Dockerfile中取消注释并修改这些设置，或通过docker-compose.yml文件中的环境变量进行设置。

## 安全考虑

- 应用程序以非root用户（`mcp`）运行
- 容器启用了`no-new-privileges`安全选项
- 仅安装必要的软件包

## 健康检查

容器包含一个健康检查，通过测试与23001端口的连接来验证应用程序是否正常运行。

# 镜像部署

本指南适用于基于 `biguncle2018/mcp-server-unified:latest` 镜像的 MCP Server 统一部署，推荐先克隆 GitHub 项目到本地，再用镜像部署。即使无 Docker 经验也能顺利完成部署。

---

## 1. 环境准备

### 1.1 安装 Docker

- 推荐使用最新版 Docker。可参考官方文档：[Docker 安装指南](https://docs.docker.com/engine/install/)
- 安装完成后，建议配置国内镜像加速（如阿里云、DaoCloud 等）。

### 1.2 克隆项目代码

建议先将官方项目仓库克隆到本地，便于获取最新配置、脚本和文档：

```bash
git clone https://github.com/BigUncle/MCP-Server-Unified-Deployment.git
cd MCP-Server-Unified-Deployment
```

### 1.3 目录准备

在本地项目目录下，确保以下子目录存在（首次克隆后大部分已包含）：

```bash
mkdir -p config logs pids mcp-data mcp-servers client_configs
```

### 1.4 端口说明

- 默认开放端口范围：`23001-23020`
- 如有端口冲突，请在运行时调整映射

---

## 2. 拉取镜像

```bash
docker pull biguncle2018/mcp-server-unified:latest
```

---

## 3. 运行容器

### 3.1 推荐启动命令

在项目根目录下运行：

```bash
docker run -d \
  --name mcp-server \
  -p 23001-23020:23001-23020 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/pids:/app/pids \
  -v $(pwd)/mcp-data:/app/mcp-data \
  -v $(pwd)/mcp-servers:/app/mcp-servers \
  -v $(pwd)/client_configs:/app/client_configs \
  -e REAL_HOST_IP="你自己主机IP地址" \
  biguncle2018/mcp-server-unified:latest
```

> **说明：**
> - `-d`：后台运行
> - `--name`：容器名称，可自定义
> - `-p`：端口映射，确保宿主机端口未被占用
> - `-v`：目录挂载，保证数据和配置持久化
> - `$(pwd)` 表示当前项目目录，适合在项目根目录下执行

### 3.2 配置文件说明

- 默认配置文件为 `config/mcp_servers.example.json`，首次启动后可复制为 `mcp_servers.json` 并根据实际需求修改。
- 推荐直接在本地 `config/` 目录下维护 `mcp_servers.json`，容器会自动加载。

### 3.3 以非 root 用户运行（推荐）

镜像内已创建 `mcp` 用户，默认以该用户运行，安全性更高。无需额外参数。

---

## 4. 配置参数

- **环境变量**：如需自定义 Python、Node、时区等参数，可通过 `-e` 传递环境变量。
- **自定义启动命令**：如需覆盖默认启动命令，可在 `docker run` 后追加命令参数。

---

## 5. 常见问题排查

### 5.1 权限问题

- 挂载目录建议归属当前用户，避免 root 权限导致读写失败。
- 如遇权限报错，可尝试 `sudo chown -R $(id -u):$(id -g) .`（在项目根目录下执行）

### 5.2 端口冲突

- 若 `23001-23020` 端口被占用，可修改 `-p` 参数映射到其他端口。

### 5.3 配置未生效

- 确认 `mcp_servers.json` 已正确挂载到 `/app/config/`，并格式无误。

### 5.4 日志查看

- 容器日志：`docker logs mcp-server`
- 应用日志：本地 `logs/` 目录下

### 5.5 镜像更新

- 更新镜像：`docker pull biguncle2018/mcp-server-unified:latest`
- 重启容器：`docker stop mcp-server && docker rm mcp-server && [重新运行上方命令]`

### 5.6 容器内缺少 ip 命令导致 IP 检测失败

**现象：**
- 日志出现如下报错：
  ```
  Error getting Docker gateway IP: [Errno 2] No such file or directory: 'ip'
  Could not determine a suitable host IP. Falling back to 'localhost'. External access will likely fail.
  ```
- 这会导致客户端无法通过宿主机 IP 访问服务。

**解决方法：**
1. **推荐修正 Dockerfile**  
   在 Dockerfile 的 apt 安装部分添加：
   ```dockerfile
   apt-get install -y iproute2
   ```
   重新构建并推送镜像后再部署。

2. **临时解决办法**  
   启动容器时手动指定宿主机 IP，例如：
   ```bash
   docker run -d \
     ...（其余参数同上） \
     -e REAL_HOST_IP=你的宿主机IP \
     biguncle2018/mcp-server-unified:latest
   ```
   这样脚本会优先使用该 IP，避免 fallback 到 localhost。

---

## 6. 参考资料

- [Docker 官方文档](https://docs.docker.com/)
- [MCP Server 项目仓库](https://github.com/BigUncle/MCP-Server-Unified-Deployment)
- [MCP Server 项目文档/README](./README.md)

---

如有其他问题，请先查阅日志和配置文件，或在 GitHub 项目仓库提交 issue 获取支持。