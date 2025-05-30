import logging
import os
import requests
from datetime import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger('video_tools')

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

def register_video_tools(mcp: FastMCP):
    @mcp.tool()
    def search_videos(
        query: str,
        count: int = 5,
        orientation: str = "landscape",
        size: str = "large"
    ) -> dict:
        """
        搜索视频。
        参数:
        - query: 搜索关键词
        - count: 返回视频数量，默认5个
        - orientation: 视频方向（landscape, portrait, square）
        - size: 视频大小（large, medium, small）
        返回:
        - 视频信息列表
        """
        logger.info(f"搜索视频: {query}")

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
                "https://api.pexels.com/videos/search",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            # 处理视频数据
            videos = []
            for video in data["videos"]:
                # 获取最高质量的视频文件
                video_files = video["video_files"]
                best_quality = max(video_files, key=lambda x: x["width"] * x["height"])
                
                videos.append({
                    "id": video["id"],
                    "url": best_quality["link"],
                    "width": best_quality["width"],
                    "height": best_quality["height"],
                    "duration": video["duration"],
                    "description": video.get("alt", "No description"),
                    "photographer": video["user"]["name"],
                    "photographer_url": video["user"]["url"],
                    "avg_color": video["avg_color"]
                })

            return {
                "success": True,
                "videos": videos
            }
        except Exception as e:
            logger.error(f"搜索视频失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    def download_video(
        video_url: str,
        filename: str = None,
        download_dir: str = DEFAULT_DOWNLOAD_DIR
    ) -> dict:
        """
        下载视频。
        """
        logger.info(f"下载视频: {video_url}")

        try:
            logger.info(f"准备创建下载目录: {download_dir}")
            download_path = Path(download_dir)
            download_path.mkdir(parents=True, exist_ok=True)

            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"video_{timestamp}.mp4"
            logger.info(f"下载文件名: {filename}")

            if not filename.lower().endswith(('.mp4', '.mov', '.avi')):
                filename += '.mp4'
            file_path = download_path / filename
            logger.info(f"完整文件路径: {file_path}")

            logger.info(f"开始下载视频流: {video_url}")
            response = requests.get(video_url, stream=True, timeout=30)
            response.raise_for_status()
            logger.info(f"视频流响应成功，开始写入文件")

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            logger.info(f"文件写入完成: {file_path}")

            try:
                file_size = os.path.getsize(file_path)
                logger.info(f"文件大小: {file_size}")
            except Exception as e:
                logger.warning(f"获取文件大小失败: {e}")
                file_size = None

            return {
                "success": True,
                "file_path": str(file_path),
                "file_size": file_size
            }
        except Exception as e:
            logger.error(f"下载视频失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"下载失败: {str(e)}"
            }

    @mcp.tool()
    def download_videos_by_keyword(
        keyword: str,
        count: int = 5,
        orientation: str = "landscape",
        size: str = "large",
        download_dir: str = DEFAULT_DOWNLOAD_DIR
    ) -> dict:
        """
        根据关键词搜索并下载视频。
        """
        logger.info(f"搜索并下载视频: {keyword}")

        try:
            if any('\u4e00' <= ch <= '\u9fff' for ch in keyword):
                keyword_en = llm_translate(keyword, src='zh', dest='en')
                logger.info(f"LLM翻译关键词: {keyword} -> {keyword_en}")
            else:
                keyword_en = keyword

            logger.info(f"开始搜索视频: {keyword_en}")
            search_result = search_videos(keyword_en, count, orientation, size)
            logger.info(f"搜索结果: {search_result}")
            if not search_result["success"]:
                logger.error(f"视频搜索失败: {search_result.get('error')}")
                return search_result

            downloaded_files = []
            for video in search_result["videos"]:
                filename = f"{keyword_en}_{video['id']}.mp4"
                logger.info(f"准备下载视频: {video['url']} -> {filename}")
                download_result = download_video(
                    video["url"],
                    filename,
                    download_dir
                )
                logger.info(f"下载结果: {download_result}")
                if download_result["success"]:
                    downloaded_files.append({
                        "file_path": download_result["file_path"],
                        "description": video["description"],
                        "photographer": video["photographer"],
                        "duration": video["duration"],
                        "resolution": f"{video['width']}x{video['height']}"
                    })
                else:
                    logger.error(f"单个视频下载失败: {download_result.get('error')}")

            logger.info(f"全部下载完成，成功数量: {len(downloaded_files)}")
            return {
                "success": True,
                "downloaded_files": downloaded_files
            }
        except Exception as e:
            logger.error(f"下载视频失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    def get_popular_videos(
        count: int = 5,
        orientation: str = "landscape",
        size: str = "large"
    ) -> dict:
        """
        获取热门视频。
        参数:
        - count: 返回视频数量，默认5个
        - orientation: 视频方向（landscape, portrait, square）
        - size: 视频大小（large, medium, small）
        返回:
        - 视频信息列表
        """
        logger.info("获取热门视频")

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
                "https://api.pexels.com/videos/popular",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            # 处理视频数据
            videos = []
            for video in data["videos"]:
                # 获取最高质量的视频文件
                video_files = video["video_files"]
                best_quality = max(video_files, key=lambda x: x["width"] * x["height"])
                
                videos.append({
                    "id": video["id"],
                    "url": best_quality["link"],
                    "width": best_quality["width"],
                    "height": best_quality["height"],
                    "duration": video["duration"],
                    "description": video.get("alt", "No description"),
                    "photographer": video["user"]["name"],
                    "photographer_url": video["user"]["url"],
                    "avg_color": video["avg_color"]
                })

            return {
                "success": True,
                "videos": videos
            }
        except Exception as e:
            logger.error(f"获取热门视频失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 