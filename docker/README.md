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

- `TZ`: Timezone (default: Asia/Shanghai)
- `LANG`, `LANGUAGE`, `LC_ALL`: Locale settings

> **Note**: Timezone and locale settings are commented out in the Dockerfile to allow users to customize them according to their specific requirements. You can uncomment and modify these settings in the Dockerfile or set them through environment variables in the docker-compose.yml file.

## Security Considerations

- The application runs as a non-root user (`mcp`)
- Container has `no-new-privileges` security option enabled
- Only essential packages are installed

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
