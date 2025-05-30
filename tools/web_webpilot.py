import logging
import requests
import os
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger('web_tools')

WEB_WEBPILOT_APIKEY = os.environ.get("WEB_WEBPILOT_APIKEY")
API_URL = "https://gpts.webpilot.ai/api/read"

def register_web_tools(mcp: FastMCP):
    @mcp.tool()
    def web_search(query: str) -> dict:
        """
        搜索工具。
        参数:
        - query: 搜索内容
        返回:
        - 包含搜索结果的字典
        """
        logger.info(f"执行网络搜索: {query}")

        if not WEB_WEBPILOT_APIKEY:
            return {
                "success": False,
                "error": "未设置WebPilot APIKEY"
            }

        try:
            # 构造一个可能包含搜索关键词的URL (使用必应搜索)
            url = f"https://www.bing.com/search?q={query}"

            # 准备请求参数
            payload = {
                "link": url,
                "ur": query,
                "lp": True,
                "rt": False,
                "l": "zh-CN",
            }

            # 设置请求头
            headers = {
                'Content-Type': 'application/json',
                'WebPilot-Friend-UID': WEB_WEBPILOT_APIKEY
            }

            # 发送请求
            response = requests.post(API_URL, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()

            return {
                "success": True,
                "result": data
            }
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return {
                "success": False,
                "result": str(e)
            }

    @mcp.tool()
    def read_webpage(url: str, keyword: str = "", language: str = "zh-CN") -> dict:
        """
        读取并分析网页内容。
        参数:
        - url: 要读取的网页URL
        - keyword: 在网页中查找的关键词(可选)
        - language: 语言代码，默认为中文
        返回:
        - 包含网页内容的字典
        """
        logger.info(f"读取网页: {url}, 关键词: {keyword}")

        if not WEB_WEBPILOT_APIKEY:
            return {
                "success": False,
                "error": "未设置WebPilot APIKEY"
            }

        try:
            # 准备请求参数
            payload = {
                "link": url,
                "ur": keyword,
                "lp": True,
                "rt": False,
                "l": language
            }

            # 设置请求头
            headers = {
                'Content-Type': 'application/json',
                'WebPilot-Friend-UID': WEB_WEBPILOT_APIKEY
            }

            # 发送请求
            response = requests.post(API_URL, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()

            logger.info(f"成功读取网页，标题: {data.get('title', '无标题')}")

            return {
                "success": True,
                "title": data.get("title", ""),
                "content": data.get("content", ""),
                "url": url
            }
        except Exception as e:
            logger.error(f"读取网页失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }