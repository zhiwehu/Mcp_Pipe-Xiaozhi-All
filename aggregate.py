from mcp.server.fastmcp import FastMCP

from tools.conversation_dingtalk import register_conversation_tools
from tools.email_qq import register_email_tools
from tools.system import register_system_tools
from tools.news_api import register_news_tools
from tools.web_brave import register_web_tools
from tools.file_manager import register_file_manager_tools
from tools.image_downloader import register_image_tools
from tools.video_downloader import register_video_tools
from tools.knowledge_downloader import register_knowledge_tools

# 创建MCP服务器
mcp = FastMCP("AggregateMCP")

# 注册所有工具
register_conversation_tools(mcp)
register_email_tools(mcp)
register_system_tools(mcp)
# register_news_tools(mcp)
# register_web_tools(mcp)
register_file_manager_tools(mcp)
register_image_tools(mcp)
register_video_tools(mcp)
# register_knowledge_tools(mcp)
if __name__ == "__main__":
    mcp.run(transport="stdio")

