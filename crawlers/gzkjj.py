# -*- coding: utf-8 -*-
"""
广州市科学技术局爬虫
"""
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import time
from .base import BaseResearchCrawler


class GZKJJCrawler(BaseResearchCrawler):
    """广州市科学技术局爬虫"""

    def get_site_name(self) -> str:
        return "广州市科学技术局"

    def fetch_notice_list(self, list_url: str, max_pages: int = 3) -> List[Dict[str, str]]:
        """抓取广州市科技局通知列表（支持分页）"""
        all_notices = []
        current_page = 1
        
        try:
            while current_page <= max_pages:
                # 构建分页URL
                if current_page == 1:
                    page_url = list_url
                else:
                    if "?" in list_url:
                        page_url = f"{list_url}&page={current_page}"
                    else:
                        page_url = list_url.replace("index.html", f"index_{current_page}.html")
                
                print(f"  📄 正在抓取第 {current_page} 页...")
                res = self.get(page_url, timeout=15)
                res.encoding = res.apparent_encoding or "utf-8"
                soup = BeautifulSoup(res.text, "html.parser")
                
                page_notices = []
                # 查找通知列表
                for item in soup.find_all("li"):
                    a_tag = item.find("a", href=True)
                    if not a_tag:
                        continue

                    title = a_tag.get_text(strip=True)
                    href = a_tag["href"]

                    if len(title) < 5:
                        continue

                    if self.should_include_notice(title):
                        full_url = self.build_full_url(href)
                        
                        # 尝试从标题或列表项中提取日期
                        date_text = item.get_text(strip=True)
                        pub_date = self.extract_date_from_text(date_text)
                        
                        page_notices.append({
                            "标题": title, 
                            "链接": full_url,
                            "发布日期": pub_date
                        })
                
                # 如果本页没有数据，停止分页
                if not page_notices:
                    break
                
                all_notices.extend(page_notices)
                current_page += 1
                time.sleep(0.5)
            
            return all_notices[:10]
        except Exception as e:
            print(f"[警告] 抓取 {self.get_site_name()} 列表失败: {str(e)}")
            return all_notices if all_notices else []

    def fetch_notice_detail(self, detail_url: str) -> Dict[str, Any]:
        """抓取广州市科技局通知正文和发布日期"""
        try:
            res = self.get(detail_url, timeout=20)
            res.encoding = res.apparent_encoding or "utf-8"
            soup = BeautifulSoup(res.text, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = ""
            pub_date = None
            
            # 尝试从页面中提取发布日期
            for p in soup.find_all("p"):
                p_text = p.get_text(strip=True)
                if "发布日期" in p_text or "发布时间" in p_text:
                    pub_date = self.extract_date_from_text(p_text)
                    if pub_date:
                        break
            
            # 广州市政府网站常见正文容器
            for class_name in ["content", "article-content", "detail-content", "main-content"]:
                content_div = soup.find("div", class_=class_name)
                if content_div:
                    text = content_div.get_text(separator="\n", strip=True)
                    break

            # 兜底
            if not text or len(text) < 200:
                paragraphs = soup.find_all("p")
                text = "\n".join(
                    [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 10]
                )

            content = text[:5000] if len(text) > 50 else "正文内容过短或无法识别"
            return {
                "content": content,
                "pub_date": pub_date
            }
        except Exception as e:
            print(f"[警告] 抓取正文失败 {detail_url}: {str(e)}")
            return {
                "content": f"获取正文失败：{str(e)[:50]}",
                "pub_date": None
            }
