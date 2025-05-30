import logging
import requests
import os
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger('news_tools')

# 从环境变量获取 NewsAPI 密钥
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
NEWS_API_BASE_URL = "https://newsapi.org/v2"

def register_news_tools(mcp: FastMCP):
    @mcp.tool()
    def get_top_headlines(
        country: str = "cn",
        category: str = None,
        query: str = None,
        page_size: int = 10
    ) -> dict:
        """
        获取热门新闻头条。
        参数:
        - country: 国家代码，默认中国(cn)
        - category: 新闻类别（可选：business, entertainment, general, health, science, sports, technology）
        - query: 搜索关键词（可选）
        - page_size: 返回结果数量，默认10条
        返回:
        - 新闻列表
        """
        logger.info(f"获取{country}的热门新闻")

        try:
            if not NEWS_API_KEY:
                return {
                    "success": False,
                    "error": "未设置 NewsAPI KEY"
                }

            # 构建请求参数
            params = {
                "apiKey": NEWS_API_KEY,
                "country": country,
                "pageSize": page_size
            }

            if category:
                params["category"] = category
            if query:
                params["q"] = query

            # 发送请求
            response = requests.get(f"{NEWS_API_BASE_URL}/top-headlines", params=params)
            response.raise_for_status()
            data = response.json()

            if data["status"] != "ok":
                return {
                    "success": False,
                    "error": data.get("message", "获取新闻失败")
                }

            # 处理新闻数据
            articles = []
            for article in data["articles"]:
                articles.append({
                    "title": article["title"],
                    "description": article["description"],
                    "url": article["url"],
                    "image_url": article["urlToImage"],
                    "source": article["source"]["name"],
                    "published_at": article["publishedAt"],
                    "author": article["author"]
                })

            return {
                "success": True,
                "total_results": data["totalResults"],
                "articles": articles
            }
        except Exception as e:
            logger.error(f"获取新闻失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    def search_news(
        query: str,
        from_date: str = None,
        to_date: str = None,
        language: str = "zh",
        sort_by: str = "publishedAt",
        page_size: int = 10
    ) -> dict:
        """
        搜索新闻文章。
        参数:
        - query: 搜索关键词
        - from_date: 开始日期（格式：YYYY-MM-DD）
        - to_date: 结束日期（格式：YYYY-MM-DD）
        - language: 语言代码，默认中文(zh)
        - sort_by: 排序方式（publishedAt, relevancy, popularity）
        - page_size: 返回结果数量，默认10条
        返回:
        - 新闻列表
        """
        logger.info(f"搜索新闻: {query}")

        try:
            if not NEWS_API_KEY:
                return {
                    "success": False,
                    "error": "未设置 NewsAPI KEY"
                }

            # 构建请求参数
            params = {
                "apiKey": NEWS_API_KEY,
                "q": query,
                "language": language,
                "sortBy": sort_by,
                "pageSize": page_size
            }

            if from_date:
                params["from"] = from_date
            if to_date:
                params["to"] = to_date

            # 发送请求
            response = requests.get(f"{NEWS_API_BASE_URL}/everything", params=params)
            response.raise_for_status()
            data = response.json()

            if data["status"] != "ok":
                return {
                    "success": False,
                    "error": data.get("message", "搜索新闻失败")
                }

            # 处理新闻数据
            articles = []
            for article in data["articles"]:
                articles.append({
                    "title": article["title"],
                    "description": article["description"],
                    "url": article["url"],
                    "image_url": article["urlToImage"],
                    "source": article["source"]["name"],
                    "published_at": article["publishedAt"],
                    "author": article["author"]
                })

            return {
                "success": True,
                "total_results": data["totalResults"],
                "articles": articles
            }
        except Exception as e:
            logger.error(f"搜索新闻失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    def get_news_sources(
        category: str = None,
        language: str = "zh",
        country: str = "cn"
    ) -> dict:
        """
        获取新闻源列表。
        参数:
        - category: 新闻类别（可选）
        - language: 语言代码，默认中文(zh)
        - country: 国家代码，默认中国(cn)
        返回:
        - 新闻源列表
        """
        logger.info("获取新闻源列表")

        try:
            if not NEWS_API_KEY:
                return {
                    "success": False,
                    "error": "未设置 NewsAPI KEY"
                }

            # 构建请求参数
            params = {
                "apiKey": NEWS_API_KEY,
                "language": language,
                "country": country
            }

            if category:
                params["category"] = category

            # 发送请求
            response = requests.get(f"{NEWS_API_BASE_URL}/sources", params=params)
            response.raise_for_status()
            data = response.json()

            if data["status"] != "ok":
                return {
                    "success": False,
                    "error": data.get("message", "获取新闻源失败")
                }

            # 处理新闻源数据
            sources = []
            for source in data["sources"]:
                sources.append({
                    "id": source["id"],
                    "name": source["name"],
                    "description": source["description"],
                    "url": source["url"],
                    "category": source["category"],
                    "language": source["language"],
                    "country": source["country"]
                })

            return {
                "success": True,
                "sources": sources
            }
        except Exception as e:
            logger.error(f"获取新闻源失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 