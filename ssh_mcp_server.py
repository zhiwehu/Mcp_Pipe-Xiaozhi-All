import paramiko
from mcp.server.fastmcp import FastMCP
import os

# --- Globals ---
ssh_client = None
mcp_server = FastMCP(name="Python SSH MCP Server", description="An MCP server to interact with SSH connections.")

# --- Helper Functions ---
def get_ssh_client():
    """获取或创建 SSH 客户端实例。"""
    global ssh_client
    if ssh_client is None:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # 自动添加主机密钥
    return ssh_client

def is_connected(client):
    """检查 SSH 客户端是否已连接。"""
    if client and client.get_transport() and client.get_transport().is_active():
        return True
    return False

# --- MCP Tools ---

@mcp_server.tool()
def ssh_connect(host: str, username: str, password: str = None, port: int = 22, key_filename: str = None) -> dict:
    """连接到 SSH 服务器。支持密码或私钥认证。"""
    client = get_ssh_client()
    if is_connected(client):
        return {"status": "error", "message": f"Already connected. Disconnect first or use a new session."}

    try:
        abs_key_filename = None
        if key_filename:
            abs_key_filename = os.path.expanduser(key_filename) # 支持 ~/
            if not os.path.isabs(abs_key_filename):
                # 假设相对于当前工作目录 (如果不是绝对路径)
                # 在实际的MCP服务器中，这可能需要更复杂的路径处理
                abs_key_filename = os.path.join(os.getcwd(), key_filename)
            if not os.path.exists(abs_key_filename):
                return {"status": "error", "message": f"Key file {abs_key_filename} not found."}

        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            key_filename=abs_key_filename,
            timeout=10 # 10秒连接超时
        )
        return {"status": "success", "message": f"Successfully connected to {username}@{host}:{port}"}
    except paramiko.AuthenticationException:
        return {"status": "error", "message": "Authentication failed. Please check credentials or key."}
    except paramiko.SSHException as e:
        return {"status": "error", "message": f"SSH connection error: {str(e)}"}
    except FileNotFoundError:
        # This might be redundant if key_filename check is robust
        return {"status": "error", "message": f"Key file {key_filename} not found."}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred during connection: {str(e)}"}

@mcp_server.tool()
def ssh_disconnect() -> dict:
    """断开与 SSH 服务器的连接。"""
    client = get_ssh_client()
    if not is_connected(client):
        return {"status": "info", "message": "Not connected."}
    try:
        client.close()
        return {"status": "success", "message": "Successfully disconnected."}
    except Exception as e:
        return {"status": "error", "message": f"Error during disconnect: {str(e)}"}

@mcp_server.tool()
def ssh_exec(command: str) -> dict:
    """在连接的 SSH 服务器上执行命令。"""
    client = get_ssh_client()
    if not is_connected(client):
        return {"status": "error", "message": "Not connected. Call ssh_connect first."}

    try:
        stdin, stdout, stderr = client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        stdout_output = stdout.read().decode('utf-8', errors='replace').strip()
        stderr_output = stderr.read().decode('utf-8', errors='replace').strip()
        return {
            "status": "success" if exit_code == 0 else "error",
            "stdout": stdout_output,
            "stderr": stderr_output,
            "exit_code": exit_code
        }
    except paramiko.SSHException as e:
        return {"status": "error", "message": f"Error executing command: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred during command execution: {str(e)}"}

@mcp_server.tool()
def ssh_put_file(local_path: str, remote_path: str) -> dict:
    """将本地文件上传到 SSH 服务器 (使用 SFTP)。"""
    client = get_ssh_client()
    if not is_connected(client):
        return {"status": "error", "message": "Not connected. Call ssh_connect first."}

    abs_local_path = os.path.expanduser(local_path)
    if not os.path.isabs(abs_local_path):
        abs_local_path = os.path.join(os.getcwd(), local_path)
    
    if not os.path.exists(abs_local_path):
        return {"status": "error", "message": f"Local file {abs_local_path} not found."}
    if not os.path.isfile(abs_local_path):
        return {"status": "error", "message": f"Local path {abs_local_path} is not a file."}

    try:
        sftp = client.open_sftp()
        sftp.put(abs_local_path, remote_path)
        sftp.close()
        return {"status": "success", "message": f"File {abs_local_path} successfully uploaded to {remote_path}"}
    except Exception as e:
        return {"status": "error", "message": f"SFTP error during upload: {str(e)}"}

@mcp_server.tool()
def ssh_get_file(remote_path: str, local_path: str) -> dict:
    """从 SSH 服务器下载文件到本地 (使用 SFTP)。"""
    client = get_ssh_client()
    if not is_connected(client):
        return {"status": "error", "message": "Not connected. Call ssh_connect first."}

    abs_local_path = os.path.expanduser(local_path)
    if not os.path.isabs(abs_local_path):
        # 如果是相对路径，则放在当前工作目录下
        abs_local_path = os.path.join(os.getcwd(), local_path)
    
    # 确保目标本地目录存在
    local_dir = os.path.dirname(abs_local_path)
    if local_dir and not os.path.exists(local_dir):
        try:
            os.makedirs(local_dir)
        except Exception as e:
            return {"status": "error", "message": f"Could not create local directory {local_dir}: {str(e)}"}

    try:
        sftp = client.open_sftp()
        sftp.get(remote_path, abs_local_path)
        sftp.close()
        return {"status": "success", "message": f"File {remote_path} successfully downloaded to {abs_local_path}"}
    except FileNotFoundError:
         return {"status": "error", "message": f"Remote file {remote_path} not found on server."}
    except Exception as e:
        return {"status": "error", "message": f"SFTP error during download: {str(e)}"}


if __name__ == "__main__":
    print("Starting Python SSH MCP Server (stdio mode)...")
    # 对于通过 mcp.json 启动并由 Cursor 管理的服务器，通常期望使用 stdio
    mcp_server.run() 