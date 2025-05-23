"""
This script is used to connect to the MCP server and pipe the input and output to the websocket endpoint.
Version: 0.2.0
--PonYoung

Usage:

export MCP_ENDPOINT=<mcp_endpoint>
python mcp_pipe.py <mcp_script>

Or use a config file:
python mcp_pipe.py config.yaml

Optional arguments:
  --debug    Enable debug logging
"""

import asyncio
import websockets
import subprocess
import logging
import os
import signal
import sys
import random
import yaml
import aiohttp
import json
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging - will be adjusted based on debug flag
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MCP_PIPE')

# Reconnection settings
INITIAL_BACKOFF = 1  # Initial wait time in seconds
MAX_BACKOFF = 600  # Maximum wait time in seconds
reconnect_attempt = 1
backoff = INITIAL_BACKOFF

# 响应队列类
class ResponseQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.tool_requests = {}  # 用于存储待处理的工具请求
        
    async def add(self, message):
        await self.queue.put(message)
        
    async def get(self):
        return await self.queue.get()
        
    def register_tool_request(self, request_id, name):
        self.tool_requests[request_id] = name
        
    def get_tool_request(self, response_id):
        return self.tool_requests.pop(response_id, None)

# 创建全局响应队列
response_queue = ResponseQueue()

# 设置调试级别
def set_debug_level(debug=False):
    if debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    else:
        logger.setLevel(logging.INFO)

async def connect_with_retry(uri, target, mode='stdio'):
    """Connect to WebSocket server with retry mechanism"""
    global reconnect_attempt, backoff
    while True:  # Infinite reconnection
        try:
            if reconnect_attempt > 0:
                wait_time = backoff * (1 + random.random() * 0.1)  # Add some random jitter
                logger.info(f"Waiting {wait_time:.2f} seconds before reconnection attempt {reconnect_attempt}...")
                await asyncio.sleep(wait_time)
                
            # Attempt to connect
            await connect_to_server(uri, target, mode)
        
        except Exception as e:
            reconnect_attempt += 1
            logger.warning(f"Connection closed (attempt: {reconnect_attempt}): {e}")            
            # Calculate wait time for next reconnection (exponential backoff)
            backoff = min(backoff * 2, MAX_BACKOFF)

async def connect_to_server(uri, target, mode='stdio'):
    """Connect to WebSocket server and establish bidirectional communication with target"""
    global reconnect_attempt, backoff, response_queue
    
    # 重新初始化响应队列，确保每次连接都使用新的队列
    # 如果 response_queue 在模块级别定义，并且你希望每次连接都重置，
    # 你可能需要一个 reset_response_queue() 函数或在这里重新实例化。
    # 假设 response_queue 是在 connect_with_retry 或全局正确处理的。
    
    # 清除之前的endpoint信息，确保每次重连都获取新的会话ID
    if hasattr(pipe_websocket_to_sse, 'endpoint'):
        pipe_websocket_to_sse.endpoint = None
        
    try:
        logger.info(f"Connecting to WebSocket server...")
        async with websockets.connect(uri) as websocket:
            logger.info(f"Successfully connected to WebSocket server")
            
            # Reset reconnection counter if connection closes normally
            reconnect_attempt = 0
            backoff = INITIAL_BACKOFF
            
            # 启动响应处理任务，两种模式都需要
            response_processor = asyncio.create_task(process_response_queue(websocket))
            
            if mode == 'stdio':
                # Start mcp_script process
                process = subprocess.Popen(
                    ['python', target],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,  # Use text mode
                    encoding='utf-8',  # Specify UTF-8 encoding for stdout/stderr
                    errors='replace'   # Replace undecodable characters
                )
                logger.info(f"Started {target} process")
                
                # Create tasks for stdio mode
                await asyncio.gather(
                    pipe_websocket_to_process(websocket, process),
                    pipe_process_to_queue(process),  # 发送到队列而不是直接发送
                    pipe_process_stderr_to_terminal(process),
                    response_processor
                )
            elif mode == 'sse':
                # Handle SSE mode
                logger.info(f"Starting SSE mode with endpoint: {target}")
                
                # Create aiohttp session
                async with aiohttp.ClientSession() as session:
                    # Subscribe to SSE endpoint
                    try:
                        async with session.get(target) as sse_response:
                            if sse_response.status != 200:
                                logger.error(f"Failed to connect to SSE endpoint: {sse_response.status}")
                                return
                                
                            logger.info("Connected to SSE endpoint successfully")
                            
                            # Get the base URL for posting messages
                            base_url = target.split('/sse')[0]
                            
                            # Create tasks for SSE mode
                            await asyncio.gather(
                                pipe_websocket_to_sse(websocket, session, base_url),
                                pipe_sse_to_websocket(sse_response, websocket),
                                response_processor
                            )
                    except Exception as e:
                        logger.error(f"SSE connection error: {e}")
                        raise
            else:
                logger.error(f"Unsupported mode: {mode}")
                response_processor.cancel()
                return
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"WebSocket connection closed: {e}")
        raise  # Re-throw exception to trigger reconnection
    except Exception as e:
        logger.error(f"Connection error: {e}")
        raise  # Re-throw exception
    finally:
        # Ensure the child process is properly terminated if in stdio mode
        if mode == 'stdio' and 'process' in locals():
            logger.info(f"Terminating {target} process")
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            logger.info(f"{target} process terminated")

async def pipe_websocket_to_process(websocket, process):
    """Read data from WebSocket and write to process stdin"""
    try:
        while True:
            # Read message from WebSocket
            message = await websocket.recv()
            
            # Write to process stdin (in text mode)
            if isinstance(message, bytes):
                message = message.decode('utf-8')
            process.stdin.write(message + '\n')
            process.stdin.flush()
    except Exception as e:
        logger.error(f"Error in WebSocket to process pipe: {e}")
        raise  # Re-throw exception to trigger reconnection
    finally:
        # Close process stdin
        if not process.stdin.closed:
            process.stdin.close()

async def pipe_process_to_queue(process):
    """Read data from process stdout and send to queue"""
    try:
        while True:
            # Read data from process stdout
            data = await asyncio.get_event_loop().run_in_executor(
                None, process.stdout.readline
            )
            
            if not data:  # If no data, the process may have ended
                logger.info("Process has ended output")
                break
                
            # Send data to queue
            await response_queue.add(data)
    except Exception as e:
        logger.error(f"Error in process to queue pipe: {e}")
        raise  # Re-throw exception to trigger reconnection

async def pipe_process_stderr_to_terminal(process):
    """Read data from process stderr and print to terminal"""
    try:
        while True:
            # Read data from process stderr
            data = await asyncio.get_event_loop().run_in_executor(
                None, process.stderr.readline
            )
            
            if not data:  # If no data, the process may have ended
                logger.info("Process has ended stderr output")
                break
                
            # Print stderr data to terminal (in text mode, data is already a string)
            sys.stderr.write(data)
            sys.stderr.flush()
    except Exception as e:
        logger.error(f"Error in process stderr pipe: {e}")
        raise  # Re-throw exception to trigger reconnection

async def pipe_websocket_to_sse(websocket, session, base_url):
    """Read data from WebSocket and send to SSE server via POST"""
    message_endpoint = None
    
    # Wait for endpoint to be set by the SSE stream
    while message_endpoint is None:
        if hasattr(pipe_websocket_to_sse, 'endpoint') and pipe_websocket_to_sse.endpoint:
            message_endpoint = pipe_websocket_to_sse.endpoint
            break
        await asyncio.sleep(0.1)
    
    logger.info(f"Using message endpoint: {message_endpoint}")
    
    # 正确构造完整URL - 提取消息路径的核心部分
    # message_endpoint通常是类似/159951/mcp/xiaozhi/message?sessionId=xxx
    # 而base_url已经包含了http://localhost:16100/159951/mcp/xiaozhi
    # 所以我们需要避免这部分的重复
    
    # 从endpoint中提取实际需要的部分
    session_part = ""
    if '?' in message_endpoint:
        path_part, session_part = message_endpoint.split('?', 1)
        # 只保留消息部分而不是完整路径
        if '/message' in path_part:
            path_part = '/message'
    else:
        path_part = message_endpoint
        
    # 构造正确的URL
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    
    # 确保正确连接路径部分
    if not path_part.startswith('/'):
        path_part = '/' + path_part
        
    # 组合完整URL
    if session_part:
        full_endpoint = f"{base_url}{path_part}?{session_part}"
    else:
        full_endpoint = f"{base_url}{path_part}"
            
    logger.info(f"Constructed full endpoint: {full_endpoint}")
    
    # 启动心跳任务
    heartbeat_task = asyncio.create_task(send_heartbeat(session, full_endpoint))
    
    # 在建立连接后请求工具列表
    await initialize_session(session, full_endpoint)
    
    try:
        while True:
            # Read message from WebSocket
            message = await websocket.recv()
            
            # 检查是否是工具调用
            try:
                msg_data = json.loads(message)
                if ('method' in msg_data and msg_data['method'] == 'tools/call' and 
                    'params' in msg_data and 'name' in msg_data['params']):
                    tool_name = msg_data['params']['name']
                    request_id = msg_data.get('id')
                    
                    # 注册工具请求用于后续响应匹配
                    response_queue.register_tool_request(request_id, tool_name)
                    logger.info(f"Routing tool '{tool_name}' to SSE handler")
            except Exception as e:
                pass
            
            # Convert to string if needed
            if isinstance(message, bytes):
                message = message.decode('utf-8')
                
            # Send message to SSE server
            try:
                # 使用预先构造好的完整URL，不再重新构造
                logger.info(f"Sending message to: {full_endpoint}")
                
                # 发送消息 - 使用JSON格式
                headers = {"Content-Type": "application/json"}
                
                # 检查消息是否已经是JSON对象
                if not message.startswith('{'):
                    # 如果不是JSON对象，则包装成JSON
                    message = json.dumps({"message": message})
                
                async with session.post(full_endpoint, data=message, headers=headers) as response:
                    if response.status not in [200, 202]:
                        logger.warning(f"Failed to send message to SSE server: Status {response.status}")
                        response_text = await response.text()
                        logger.warning(f"Error response: {response_text[:200]}")  # 只显示前200个字符
                    else:
                        logger.info(f"Successfully sent message to SSE server: Status {response.status}")
            except Exception as e:
                logger.error(f"Error sending message to SSE server: {e}")
    except Exception as e:
        logger.error(f"Error in WebSocket to SSE pipe: {e}")
        raise  # Re-throw exception to trigger reconnection
    finally:
        # 取消心跳任务
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

async def pipe_sse_to_websocket(sse_response, websocket):
    """Read data from SSE response and send to WebSocket"""
    try:
        logger.info("Starting to read SSE events...")
        # Process SSE events line by line
        event_type = None
        data_buffer = []
        
        async for line in sse_response.content:
            line = line.decode('utf-8').strip()
            logger.debug(f"SSE raw line: '{line}'")
            
            # Skip empty lines, but in SSE an empty line marks the end of an event
            if not line:
                # Process the complete event if we have data
                if data_buffer and event_type:
                    full_data = ''.join(data_buffer)
                    logger.info(f"SSE {event_type} event received, length: {len(full_data)}")
                    
                    # Special handling for endpoint event
                    if event_type == 'endpoint':
                        logger.info(f"Received endpoint: {full_data}")
                        pipe_websocket_to_sse.endpoint = full_data
                    elif event_type == 'message':
                        # 解析消息内容 - 可能需要提取内部的实际消息
                        try:
                            # 尝试解析JSON
                            data_obj = json.loads(full_data)
                            logger.debug(f"Parsed message data: {data_obj}")
                            
                            # 如果消息有嵌套结构，提取实际消息内容
                            actual_message = full_data
                            if isinstance(data_obj, dict) and 'message' in data_obj:
                                actual_message = data_obj['message']
                                if isinstance(actual_message, dict):
                                    actual_message = json.dumps(actual_message)
                                logger.info("Extracted message from wrapper")
                            
                            # 检查是否是工具列表响应
                            if isinstance(data_obj, dict) and 'result' in data_obj and \
                               isinstance(data_obj['result'], dict) and 'tools' in data_obj['result']:
                                logger.info(f"Received tools list with {len(data_obj['result']['tools'])} tools")
                            
                            # 检查是否是工具调用响应
                            if isinstance(data_obj, dict) and 'id' in data_obj:
                                response_id = data_obj['id']
                                tool_name = response_queue.get_tool_request(response_id)
                                if tool_name:
                                    logger.info(f"Received response for tool '{tool_name}'")
                            
                            # 添加到响应队列
                            await response_queue.add(actual_message)
                        except json.JSONDecodeError:
                            # 如果不是JSON，直接添加原始数据
                            logger.warning(f"Received non-JSON message from SSE: {full_data[:50]}...")
                            await response_queue.add(full_data)
                        except Exception as e:
                            logger.warning(f"Error processing SSE message: {e}")
                            # 尝试继续处理消息，而不是失败
                            await response_queue.add(full_data)
                
                # Reset event type and data buffer
                event_type = None
                data_buffer = []
                continue
                
            # Process event type
            if line.startswith('event:'):
                event_type = line[6:].strip()
                continue
                
            # Process data line
            if line.startswith('data:'):
                data = line[5:].strip()
                data_buffer.append(data)
                continue
    except Exception as e:
        logger.error(f"Error in SSE to WebSocket pipe: {e}")
        raise  # Re-throw exception to trigger reconnection

async def process_response_queue(websocket):
    """处理响应队列，将响应发送到WebSocket"""
    try:
        logger.info("Started response queue processor")
        while True:
            # 从队列获取下一个响应
            response = await response_queue.get()
            
            # 检查响应类型
            response_type = "Unknown"
            try:
                # 尝试解析为JSON以确定类型
                if isinstance(response, str) and response.startswith('{'):
                    data = json.loads(response)
                    if 'method' in data:
                        response_type = f"Method: {data['method']}"
                    elif 'result' in data and isinstance(data['result'], dict) and 'tools' in data['result']:
                        response_type = f"Tools list ({len(data['result']['tools'])} tools)"
                    elif 'result' in data:
                        response_type = "Tool result"
                    elif 'error' in data:
                        response_type = f"Error: {data.get('error', {}).get('message', 'Unknown error')}"
                    else:
                        response_type = "JSON data"
            except:
                # 如果解析失败，只是记录
                pass
                
            # 记录消息类型
            logger.info(f"Sending to WebSocket: {response_type} ({len(response) if isinstance(response, str) else 'non-string'} bytes)")
            logger.debug(f"Response content: {response[:100]}..." if isinstance(response, str) and len(response) > 100 else response)
            
            # 发送到WebSocket
            await websocket.send(response)
    except asyncio.CancelledError:
        logger.info("Response queue processor cancelled")
        raise
    except Exception as e:
        logger.error(f"Error processing response queue: {e}")
        raise

async def send_heartbeat(session, endpoint):
    """发送定期心跳以保持连接活跃"""
    try:
        logger.info(f"Started heartbeat task to {endpoint}")
        while True:
            await asyncio.sleep(30)  # 每30秒发送一次心跳
            try:
                # 构造心跳消息
                ping_message = json.dumps({
                    "jsonrpc": "2.0",
                    "method": "ping",
                    "params": {}
                })
                
                logger.debug(f"Sending heartbeat to {endpoint}")
                # 发送心跳
                headers = {"Content-Type": "application/json"}
                async with session.post(endpoint, data=ping_message, headers=headers) as response:
                    if response.status in [200, 202]:
                        logger.debug(f"Heartbeat successful: {response.status}")
                    else:
                        response_text = await response.text()
                        logger.warning(f"Heartbeat failed: {response.status} - {response_text[:50]}")
            except Exception as e:
                logger.warning(f"Error sending heartbeat: {e}")
    except asyncio.CancelledError:
        logger.info("Heartbeat task cancelled")
        pass  # 任务取消，静默退出
    except Exception as e:
        logger.error(f"Unexpected error in heartbeat task: {e}")
        raise

def load_config(config_file):
    """Load configuration from a YAML file"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config file: {e}")
        return None

def signal_handler(sig, frame):
    """Handle interrupt signals"""
    logger.info("Received interrupt signal, shutting down...")
    sys.exit(0)

async def initialize_session(session, endpoint):
    """发送初始化请求，获取工具列表"""
    try:
        # 构造工具列表请求
        tools_request = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        })
        
        logger.info("Sending tools/list request to initialize session")
        # 发送请求
        headers = {"Content-Type": "application/json"}
        async with session.post(endpoint, data=tools_request, headers=headers) as response:
            if response.status not in [200, 202]:
                logger.warning(f"Failed to initialize session: Status {response.status}")
            else:
                logger.info("Session initialization request sent successfully")
    except Exception as e:
        logger.warning(f"Error initializing session: {e}")

if __name__ == "__main__":
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='MCP pipe for WebSocket and SSE communication')
    parser.add_argument('target', help='MCP script or config file')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Set debug level
    set_debug_level(args.debug)
    
    target_arg = args.target
    
    # Determine if the argument is a YAML config file
    if target_arg.endswith('.yaml') or target_arg.endswith('.yml'):
        # Load configuration from YAML file
        config = load_config(target_arg)
        if not config:
            logger.error("Failed to load configuration file")
            sys.exit(1)
        
        # Get MCP endpoint and mode from config
        endpoint_url = config.get('mcp_endpoint')
        # Default mode to 'stdio' if not specified, for clarity.
        mode = config.get('mode', 'stdio') 
        
        if not endpoint_url:
            logger.error("MCP_ENDPOINT must be defined in the config file (mcp_endpoint)")
            sys.exit(1)

        if mode == 'sse':
            sse_url = config.get('sse_url')
            if not sse_url:
                logger.error("sse_url is required in config file for SSE mode")
                sys.exit(1)
            target = sse_url
        elif mode == 'stdio':
            # 读取 script_path 来指定 stdio 模式下要运行的脚本
            script_path = config.get('script_path')
            if not script_path:
                logger.error("script_path is required in config file for stdio mode")
                sys.exit(1)
            target = script_path
        else:
            # 如果模式不是 'sse' 或 'stdio'，则报错
            logger.error(f"Unsupported mode '{mode}' in config file. Supported modes are 'stdio' and 'sse'.")
            sys.exit(1)
    else:
        # Use stdio mode with the provided script from command line
        endpoint_url = os.environ.get('MCP_ENDPOINT')
        if not endpoint_url:
            logger.error("Please set the `MCP_ENDPOINT` environment variable or use a config file")
            sys.exit(1)
        target = target_arg
        mode = 'stdio' # Explicitly stdio mode if script is passed via CLI
    
    # Log the configuration
    logger.info(f"Using mode: {mode}")
    logger.info(f"MCP endpoint: {endpoint_url}")
    logger.info(f"Target: {target}")
    
    # Start main loop
    try:
        asyncio.run(connect_with_retry(endpoint_url, target, mode))
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Program execution error: {e}")
