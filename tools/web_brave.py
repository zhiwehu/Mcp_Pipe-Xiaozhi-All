import logging
import requests
import os
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger('web_tools')

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY")
BRAVE_SEARCH_API_URL = "https://api.search.brave.com/res/v1/web/search"
BRAVE_SUMMARIZE_API_URL = "https://api.search.brave.com/res/v1/summarizer/search"

def register_web_tools(mcp: FastMCP):
    @mcp.tool()
    def brave_search(query: str, count: int = 10) -> dict:
        """
        使用 Brave Search 进行网络搜索。
        参数:
        - query: 搜索内容
        - count: 返回结果数量，默认10条
        返回:
        - 包含搜索结果的字典
        """
        logger.info(f"执行 Brave 搜索: {query}")

        if not BRAVE_API_KEY:
            return {
                "success": False,
                "error": "未设置 Brave API KEY"
            }

        try:
            # 准备请求参数
            params = {
                "q": query,
                "count": count
            }

            # 设置请求头
            headers = {
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip',
                'X-Subscription-Token': BRAVE_API_KEY
            }

            # 发送请求
            response = requests.get(BRAVE_SEARCH_API_URL, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()

            # 处理搜索结果
            results = []
            for web_result in data.get('web', {}).get('results', []):
                results.append({
                    'title': web_result.get('title', ''),
                    'description': web_result.get('description', ''),
                    'url': web_result.get('url', ''),
                    'published_date': web_result.get('published_date', '')
                })

            return {
                "success": True,
                "query": query,
                "results": results
            }
        except Exception as e:
            logger.error(f"Brave 搜索失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    # @mcp.tool()
    # def brave_summarize(url: str) -> dict:
    #     """
    #     使用 Brave Search 的摘要功能分析网页内容。
    #     参数:
    #     - url: 要分析的网页URL
    #     返回:
    #     - 包含网页摘要的字典
    #     """
    #     logger.info(f"分析网页: {url}")

    #     if not BRAVE_API_KEY:
    #         return {
    #             "success": False,
    #             "error": "未设置 Brave API KEY"
    #         }

    #     try:
    #         # 准备请求参数
    #         params = {
    #             "url": url,
    #         }

    #         # 设置请求头
    #         headers = {
    #             'Accept': 'application/json',
    #             'Accept-Encoding': 'gzip',
    #             'X-Subscription-Token': BRAVE_API_KEY
    #         }

    #         # 发送请求
    #         response = requests.get(BRAVE_SUMMARIZE_API_URL, params=params, headers=headers)
    #         response.raise_for_status()

    #         data = response.json()

    #         return {
    #             "success": True,
    #             "title": data.get('title', ''),
    #             "summary": data.get('summary', ''),
    #             "url": url
    #         }
    #     except Exception as e:
    #         logger.error(f"网页分析失败: {str(e)}")
    #         return {
    #             "success": False,
    #             "error": str(e)
    #         } 