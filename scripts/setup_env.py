#!/usr/bin/env python3
"""
设置MCP服务器统一部署工具的虚拟环境

此脚本使用uv创建虚拟环境并安装所需的依赖。
uv是一个快速的Python包管理器和虚拟环境工具。
"""

import os
import subprocess
import sys

def run_command(command):
    """运行命令并打印输出"""
    print(f"执行: {command}")
    result = subprocess.run(command, shell=True, check=False)
    if result.returncode != 0:
        print(f"命令执行失败，退出代码: {result.returncode}")
        sys.exit(result.returncode)
    return result

def main():
    # 获取脚本所在目录的上一级目录（项目根目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    # 切换到项目根目录
    os.chdir(project_dir)
    print(f"切换到项目目录: {project_dir}")

    # 检查uv是否已安装
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        print("uv已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("uv未安装，正在安装...")
        run_command("pip install uv")

    # 创建虚拟环境
    print("\n创建虚拟环境...")
    run_command("uv venv --python=3.12")

    # 显示激活虚拟环境的命令
    venv_activate_cmd = ".venv\\Scripts\\activate" if sys.platform == "win32" else "source .venv/bin/activate"
    print(f"\n请使用以下命令激活虚拟环境:\n{venv_activate_cmd}")

    # 安装依赖
    print("\n安装依赖...")
    run_command("uv pip install -e .")
    print("\n或者使用requirements.txt安装依赖:")
    print("uv pip install -r requirements.txt")

    # 提示安装mcp-proxy
    print("\n建议使用pipx安装mcp-proxy:")
    print("pip install pipx")
    print("pipx ensurepath")
    print("pipx install mcp-proxy")

    print("\n环境设置完成！请按照以下步骤继续：")
    print(f"1. 激活虚拟环境: {venv_activate_cmd}")
    print("2. 配置MCP服务器: 编辑config/mcp_servers.json文件")
    print("3. 启动MCP服务器: python scripts/manage_mcp.py start")
    print("\n更多信息请参考README.md文件")

    print("\n环境设置完成！")
    print("使用以下命令激活虚拟环境:")
    if os.name == 'nt':  # Windows
        print(".venv\\Scripts\\activate")
    else:  # Unix/Linux/MacOS
        print("source .venv/bin/activate")

if __name__ == "__main__":
    main()