# MCP Sample Project | MCP 示例项目

A powerful interface for extending AI capabilities through remote control, calculations, email operations, knowledge search, and more.

一个强大的接口，用于通过远程控制、计算、邮件操作、知识搜索等方式扩展AI能力。

## Overview | 概述

MCP (Model Context Protocol) is a protocol that allows servers to expose tools that can be invoked by language models. Tools enable models to interact with external systems, such as querying databases, calling APIs, or performing computations. Each tool is uniquely identified by a name and includes metadata describing its schema.

MCP（模型上下文协议）是一个允许服务器向语言模型暴露可调用工具的协议。这些工具使模型能够与外部系统交互，例如查询数据库、调用API或执行计算。每个工具都由一个唯一的名称标识，并包含描述其模式的元数据。

## Features | 特性

- 🔌 Bidirectional communication between AI and external tools | AI与外部工具之间的双向通信
- 🔄 Automatic reconnection with exponential backoff | 具有指数退避的自动重连机制
- 📊 Real-time data streaming | 实时数据流传输
- 🛠️ Easy-to-use tool creation interface | 简单易用的工具创建接口
- 🔒 Secure WebSocket communication | 安全的WebSocket通信
- 🌐 Multiple communication modes support (STDIO and SSE) | 支持多种通信模式（STDIO和SSE）

## Quick Start | 快速开始

1. Install dependencies | 安装依赖:
```bash
pip install -r requirements.txt
```

2. Run with STDIO mode (original mode) | 使用STDIO模式运行（原始模式）:

   - Set up environment variables | 设置环境变量:
   ```bash
   export MCP_ENDPOINT=<your_mcp_endpoint>
   ```

   - Run script | 运行脚本:
   ```bash
   python mcp_pipe.py calculator.py
   ```

3. Run with SSE mode using config file | 使用配置文件运行SSE模式:
   ```bash
   python mcp_pipe.py config.yaml
   ```

## Configuration | 配置

You can use a YAML configuration file to specify the mode and endpoints:

可以使用YAML配置文件指定模式和端点：

### Example config.yaml for SSE mode | SSE模式的示例配置文件：
```yaml
mode: sse
mcp_endpoint: wss://your-websocket-server.com/ws
sse_url: http://localhost:16100/your-path/mcp/sse
```

### Example config.yaml for WebSocket mode | WebSocket模式的示例配置文件：
```yaml
mode: websocket
mcp_endpoint: wss://your-websocket-server.com/ws
```

## Project Structure | 项目结构

- `mcp_pipe.py`: Main communication pipe that handles WebSocket connections and process management | 处理WebSocket连接和进程管理的主通信管道
- `calculator.py`: Example MCP tool implementation for mathematical calculations | 用于数学计算的MCP工具示例实现
- `requirements.txt`: Project dependencies | 项目依赖
- `config.yaml`: Configuration file for different modes | 不同模式的配置文件

## Creating Your Own MCP Tools | 创建自己的MCP工具

Here's a simple example of creating an MCP tool | 以下是一个创建MCP工具的简单示例:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("YourToolName")

@mcp.tool()
def your_tool(parameter: str) -> dict:
    """Tool description here"""
    # Your implementation
    return {"success": True, "result": result}

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

## Use Cases | 使用场景

- Mathematical calculations | 数学计算
- Email operations | 邮件操作
- Knowledge base search | 知识库搜索
- Remote device control | 远程设备控制
- Data processing | 数据处理
- Custom tool integration | 自定义工具集成

## Requirements | 环境要求

- Python 3.7+
- websockets>=11.0.3
- python-dotenv>=1.0.0
- mcp>=1.8.1
- pydantic>=2.11.4
- aiohttp>=4.13.2
- PyYAML>=6.0

## Contributing | 贡献指南

Contributions are welcome! Please feel free to submit a Pull Request.

欢迎贡献代码！请随时提交Pull Request。

## License | 许可证

This project is licensed under the MIT License - see the LICENSE file for details.

本项目采用MIT许可证 - 详情请查看LICENSE文件。

## Acknowledgments | 致谢

- Thanks to all contributors who have helped shape this project | 感谢所有帮助塑造这个项目的贡献者
- Inspired by the need for extensible AI capabilities | 灵感来源于对可扩展AI能力的需求

## 更新日志 | Changelog

### v0.2.0 主要优化

- 新增 **SSE（Server-Sent Events）模式**，支持与 SSE 服务端点直接通信，自动发现消息端点，支持工具调用与响应、会话初始化（`tools/list`）、心跳保活等功能。
- 支持通过 YAML 配置文件灵活管理端点、模式（`stdio`/`sse`）、目标脚本路径等参数，便于集中配置和多环境切换。
- 引入响应队列机制，提升异步消息处理能力和健壮性。
- 命令行支持 `--debug` 参数，日志与错误处理更完善。
- 代码结构优化，核心连接逻辑支持多种模式，易于扩展和维护。

## 推荐对接 | Recommended Integration

> **推荐使用 [HyperChat](https://github.com/BigSweetPotatoStudio/HyperChat/blob/doc/README.zh.md) 作为 SSE 服务端，获取更多小智能力和丰富的对话能力。**
>
> 通过 SSE 模式对接 HyperChat，可以让您的 MCP 工具与 HyperChat 平台的多种智能体和插件无缝协作，快速扩展 AI 能力。
