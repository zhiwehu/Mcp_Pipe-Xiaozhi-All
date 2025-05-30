import logging
import os
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger('system_tools')

DINGTALK_WEBHOOK = os.environ.get("DINGTALK_WEBHOOK")

def register_system_tools(mcp: FastMCP):
    @mcp.tool()
    def get_server_status() -> dict:
        """
        获取服务器状态监控信息。
        返回:
        - 包含CPU、内存、磁盘等使用情况的字典
        """
        try:
            import psutil

            # CPU信息
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # 内存信息
            memory = psutil.virtual_memory()
            memory_total = memory.total / (1024 * 1024 * 1024)  # GB
            memory_used = memory.used / (1024 * 1024 * 1024)    # GB
            memory_percent = memory.percent

            # 磁盘信息
            disk = psutil.disk_usage('/')
            disk_total = disk.total / (1024 * 1024 * 1024)      # GB
            disk_used = disk.used / (1024 * 1024 * 1024)        # GB
            disk_percent = disk.percent

            # 系统启动时间
            boot_time = psutil.boot_time()

            return {
                "success": True,
                "result": {
                    "cpu": {
                        "usage_percent": cpu_percent,
                        "core_count": cpu_count
                    },
                    "memory": {
                        "total_gb": round(memory_total, 2),
                        "used_gb": round(memory_used, 2),
                        "usage_percent": memory_percent
                    },
                    "disk": {
                        "total_gb": round(disk_total, 2),
                        "used_gb": round(disk_used, 2),
                        "usage_percent": disk_percent
                    },
                    "system": {
                        "boot_time": boot_time
                    }
                }
            }
        except Exception as e:
            logger.error(f"获取服务器状态失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

