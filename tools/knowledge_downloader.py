import logging
import os
import requests
from mcp.server.fastmcp import FastMCP
from pathlib import Path

logger = logging.getLogger('knowledge_downloader')

# 你可以选择用 BRAVE_API_KEY 或 WEB_WEBPILOT_APIKEY
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY")
BRAVE_SEARCH_API_URL = "https://api.search.brave.com/res/v1/web/search"
DEFAULT_DOWNLOAD_DIR = os.path.expanduser("~/Downloads")

def register_knowledge_tools(mcp: FastMCP):
    @mcp.tool()
    def search_and_save_markdown(
        query: str,
        count: int = 3,
        download_dir: str = DEFAULT_DOWNLOAD_DIR
    ) -> dict:
        """
        搜索相关资料并保存为markdown文件。
        参数:
        - query: 搜索关键词
        - count: 下载前几个网页，默认3个
        - download_dir: 保存目录，默认~/Downloads
        返回:
        - 保存的markdown文件路径列表
        """
        logger.info(f"搜索并保存为markdown: {query}")

        if not BRAVE_API_KEY:
            return {"success": False, "error": "未设置 BRAVE_API_KEY"}

        try:
            # 1. Brave 搜索
            headers = {"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY}
            params = {"q": query, "count": count}
            resp = requests.get(BRAVE_SEARCH_API_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("web", {}).get("results", [])
            if not results:
                return {"success": False, "error": "未找到相关网页"}

            # 2. 读取网页内容（这里只做简单 requests.get，实际可用更强的爬虫或 WebPilot API）
            saved_files = []
            for idx, item in enumerate(results[:count]):
                url = item["url"]
                title = item.get("title", f"Result {idx+1}")
                try:
                    page = requests.get(url, timeout=10)
                    page.raise_for_status()
                    content = page.text
                except Exception as e:
                    logger.warning(f"无法读取网页 {url}: {e}")
                    continue

                # 3. 简单提取正文（可用更强的正文提取库，如 readability-lxml）
                # 这里只是简单保存全部HTML
                md_content = f"# {title}\n\n原始链接: {url}\n\n```\n{content[:2000]}\n...（内容截断）\n```"

                # 4. 保存为 markdown 文件
                filename = f"{query.replace(' ', '_')}_{idx+1}.md"
                save_path = Path(download_dir) / filename
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
                saved_files.append(str(save_path))

            if not saved_files:
                return {"success": False, "error": "未能成功保存任何网页内容"}

            return {"success": True, "files": saved_files}
        except Exception as e:
            logger.error(f"查找资料并保存markdown失败: {e}")
            return {"success": False, "error": str(e)}