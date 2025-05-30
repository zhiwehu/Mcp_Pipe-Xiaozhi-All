# file_manager.py
from mcp.server.fastmcp import FastMCP
import sys
import logging
import os
import shutil
from send2trash import send2trash

logger = logging.getLogger('FileManager')
logger.setLevel(logging.INFO)
# Allow logs to propagate to root handlers
logger.propagate = True

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

# 设置默认工作目录，优先从环境变量读取，否则使用 Downloads 目录
DEFAULT_WORK_DIR = os.getenv("FILE_MANAGER_WORK_DIR", os.path.expanduser("~/Downloads"))

def register_file_manager_tools(mcp: FastMCP):
    @mcp.tool()
    def get_work_dir() -> dict:
        """获取当前工作目录"""
        return {
            "success": True,
            "work_dir": DEFAULT_WORK_DIR
        }

    @mcp.tool()
    def list_directory(path: str = DEFAULT_WORK_DIR) -> dict:
        """列出指定目录下的所有文件和文件夹，默认列出 Downloads 目录"""
        try:
            path = os.path.expanduser(path)  # 支持 ~ 展开为用户目录
            items = os.listdir(path)
            files = []
            dirs = []
            
            for item in items:
                full_path = os.path.join(path, item)
                if os.path.isfile(full_path):
                    files.append({
                        "name": item,
                        "size": os.path.getsize(full_path),
                        "type": "file"
                    })
                else:
                    dirs.append({
                        "name": item,
                        "type": "directory"
                    })
            
            return {
                "success": True,
                "path": path,
                "files": files,
                "directories": dirs
            }
        except Exception as e:
            logger.error(f"Error listing directory {path}: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def create_directory(path: str) -> dict:
        """在 Downloads 目录下创建新目录"""
        try:
            # 如果路径不是绝对路径，则相对于 Downloads 目录
            if not os.path.isabs(path):
                path = os.path.join(DEFAULT_WORK_DIR, path)
            path = os.path.expanduser(path)
            os.makedirs(path, exist_ok=True)
            return {"success": True, "message": f"Directory created: {path}"}
        except Exception as e:
            logger.error(f"Error creating directory {path}: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def delete_file(path: str) -> dict:
        """
        将文件或目录移动到回收站。
        参数:
        - path: 要删除的文件或目录路径
        返回:
        - 操作状态
        """
        try:
            # 如果路径不是绝对路径，则相对于 Downloads 目录
            if not os.path.isabs(path):
                path = os.path.join(DEFAULT_WORK_DIR, path)
            path = os.path.expanduser(path)
            
            if os.path.exists(path):
                # 使用 send2trash 将文件移动到回收站
                send2trash(path)
                return {
                    "success": True, 
                    "message": f"File moved to trash: {path}"
                }
            else:
                return {
                    "success": False, 
                    "error": "Path does not exist"
                }
        except Exception as e:
            logger.error(f"Error moving to trash {path}: {str(e)}")
            return {
                "success": False, 
                "error": str(e)
            }

    @mcp.tool()
    def move_file(source: str, destination: str) -> dict:
        """移动或重命名 Downloads 目录下的文件/目录"""
        try:
            # 如果路径不是绝对路径，则相对于 Downloads 目录
            if not os.path.isabs(source):
                source = os.path.join(DEFAULT_WORK_DIR, source)
            if not os.path.isabs(destination):
                destination = os.path.join(DEFAULT_WORK_DIR, destination)
                
            source = os.path.expanduser(source)
            destination = os.path.expanduser(destination)
            shutil.move(source, destination)
            return {"success": True, "message": f"Moved {source} to {destination}"}
        except Exception as e:
            logger.error(f"Error moving {source} to {destination}: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def read_file(path: str) -> dict:
        """读取 Downloads 目录下的文件内容"""
        try:
            # 如果路径不是绝对路径，则相对于 Downloads 目录
            if not os.path.isabs(path):
                path = os.path.join(DEFAULT_WORK_DIR, path)
            path = os.path.expanduser(path)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"success": True, "content": content}
        except Exception as e:
            logger.error(f"Error reading file {path}: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def write_file(path: str, content: str) -> dict:
        """写入文件内容到 Downloads 目录"""
        try:
            # 如果路径不是绝对路径，则相对于 Downloads 目录
            if not os.path.isabs(path):
                path = os.path.join(DEFAULT_WORK_DIR, path)
            path = os.path.expanduser(path)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {"success": True, "message": f"File written: {path}"}
        except Exception as e:
            logger.error(f"Error writing file {path}: {str(e)}")
            return {"success": False, "error": str(e)}