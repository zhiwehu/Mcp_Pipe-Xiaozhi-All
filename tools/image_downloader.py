import logging
import os
import requests
from datetime import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger('image_tools')

# 从环境变量获取 Pexels API 密钥
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
# 设置默认下载目录为 Downloads
DEFAULT_DOWNLOAD_DIR = os.path.expanduser("~/Downloads")

ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY")

def llm_translate(text, src="zh", dest="en"):
    """
    用智谱清言API翻译文本
    """
    if not ZHIPU_API_KEY:
        raise RuntimeError("未设置ZHIPU_API_KEY环境变量")
    prompt = f"请将下列内容翻译成英文，保留专有名词：\n{text}"
    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "glm-4-flash",  # 你也可以用 glm-3-turbo
        "messages": [
            {"role": "system", "content": "You are a translation assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 60,
        "temperature": 0.2
    }
    resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", headers=headers, json=data, timeout=20)
    resp.raise_for_status()
    result = resp.json()
    return result["choices"][0]["message"]["content"].strip()

def register_image_tools(mcp: FastMCP):
    @mcp.tool()
    def search_images(
        query: str,
        count: int = 5,
        orientation: str = "landscape",
        size: str = "large"
    ) -> dict:
        """
        搜索图片。
        参数:
        - query: 搜索关键词
        - count: 返回图片数量，默认5张
        - orientation: 图片方向（landscape, portrait, square）
        - size: 图片大小（large, medium, small）
        返回:
        - 图片信息列表
        """
        logger.info(f"搜索图片: {query}")

        try:
            if not PEXELS_API_KEY:
                return {
                    "success": False,
                    "error": "未设置 Pexels API KEY"
                }

            # 如果关键词为中文，自动用LLM翻译为英文
            if any('\u4e00' <= ch <= '\u9fff' for ch in query):
                query_en = llm_translate(query, src='zh', dest='en')
                logger.info(f"LLM翻译关键词: {query} -> {query_en}")
            else:
                query_en = query

            # 构建请求参数
            params = {
                "query": query_en,
                "per_page": count,
                "orientation": orientation,
                "size": size
            }

            # 设置请求头
            headers = {
                "Authorization": PEXELS_API_KEY
            }

            # 发送请求
            response = requests.get(
                "https://api.pexels.com/v1/search",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            # 处理图片数据
            images = []
            for photo in data["photos"]:
                images.append({
                    "id": photo["id"],
                    "url": photo["src"]["large"],  # 使用大尺寸图片
                    "original_url": photo["src"]["original"],
                    "width": photo["width"],
                    "height": photo["height"],
                    "description": photo.get("alt", "No description"),
                    "photographer": photo["photographer"],
                    "photographer_url": photo["photographer_url"],
                    "avg_color": photo["avg_color"]
                })

            return {
                "success": True,
                "images": images
            }
        except Exception as e:
            logger.error(f"搜索图片失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    def download_image(
        image_url: str,
        filename: str = None,
        download_dir: str = DEFAULT_DOWNLOAD_DIR
    ) -> dict:
        """
        下载图片。
        参数:
        - image_url: 图片URL
        - filename: 保存的文件名（可选）
        - download_dir: 下载目录（可选，默认Downloads）
        返回:
        - 下载状态和文件路径
        """
        logger.info(f"下载图片: {image_url}")

        try:
            # 确保下载目录存在
            download_path = Path(download_dir)
            download_path.mkdir(parents=True, exist_ok=True)

            # 如果没有提供文件名，使用时间戳生成
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"image_{timestamp}.jpg"

            # 确保文件名有正确的扩展名
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                filename += '.jpg'

            # 构建完整的文件路径
            file_path = download_path / filename

            # 下载图片
            response = requests.get(image_url, stream=True)
            response.raise_for_status()

            # 保存图片
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return {
                "success": True,
                "file_path": str(file_path),
                "file_size": os.path.getsize(file_path)
            }
        except Exception as e:
            logger.error(f"下载图片失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    def download_images_by_keyword(
        keyword: str,
        count: int = 5,
        orientation: str = "landscape",
        size: str = "large",
        download_dir: str = DEFAULT_DOWNLOAD_DIR
    ) -> dict:
        """
        根据关键词搜索并下载图片。
        参数:
        - keyword: 搜索关键词
        - count: 下载图片数量，默认5张
        - orientation: 图片方向（landscape, portrait, square）
        - size: 图片大小（large, medium, small）
        - download_dir: 下载目录（可选，默认Downloads）
        返回:
        - 下载状态和文件路径列表
        """
        logger.info(f"搜索并下载图片: {keyword}")

        try:
            # 如果关键词为中文，自动用LLM翻译为英文
            if any('\u4e00' <= ch <= '\u9fff' for ch in keyword):
                keyword_en = llm_translate(keyword, src='zh', dest='en')
                logger.info(f"LLM翻译关键词: {keyword} -> {keyword_en}")
            else:
                keyword_en = keyword

            # 搜索图片
            search_result = search_images(keyword_en, count, orientation, size)
            if not search_result["success"]:
                return search_result

            # 下载图片
            downloaded_files = []
            for image in search_result["images"]:
                # 使用图片ID和关键词作为文件名
                filename = f"{keyword_en}_{image['id']}.jpg"
                # 使用 original_url 而不是 url，确保下载原始图片
                download_result = download_image(
                    image["original_url"],
                    filename,
                    download_dir
                )
                if download_result["success"]:
                    downloaded_files.append({
                        "file_path": download_result["file_path"],
                        "description": image["description"],
                        "photographer": image["photographer"],
                        "avg_color": image["avg_color"]
                    })

            return {
                "success": True,
                "downloaded_files": downloaded_files
            }
        except Exception as e:
            logger.error(f"下载图片失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    def get_curated_photos(
        count: int = 5,
        orientation: str = "landscape",
        size: str = "large"
    ) -> dict:
        """
        获取精选图片。
        参数:
        - count: 返回图片数量，默认5张
        - orientation: 图片方向（landscape, portrait, square）
        - size: 图片大小（large, medium, small）
        返回:
        - 图片信息列表
        """
        logger.info("获取精选图片")

        try:
            if not PEXELS_API_KEY:
                return {
                    "success": False,
                    "error": "未设置 Pexels API KEY"
                }

            # 构建请求参数
            params = {
                "per_page": count,
                "orientation": orientation,
                "size": size
            }

            # 设置请求头
            headers = {
                "Authorization": PEXELS_API_KEY
            }

            # 发送请求
            response = requests.get(
                "https://api.pexels.com/v1/curated",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            # 处理图片数据
            images = []
            for photo in data["photos"]:
                images.append({
                    "id": photo["id"],
                    "url": photo["src"]["large"],
                    "original_url": photo["src"]["original"],
                    "width": photo["width"],
                    "height": photo["height"],
                    "description": photo.get("alt", "No description"),
                    "photographer": photo["photographer"],
                    "photographer_url": photo["photographer_url"],
                    "avg_color": photo["avg_color"]
                })

            return {
                "success": True,
                "images": images
            }
        except Exception as e:
            logger.error(f"获取精选图片失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 