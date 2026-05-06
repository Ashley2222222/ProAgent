# -*- coding: utf-8 -*-
"""
广东省科学技术厅爬虫
"""
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import time
from .base import BaseResearchCrawler


class GDSTCrawler(BaseResearchCrawler):
    """广东省科技厅爬虫"""

    def get_site_name(self) -> str:
        return "广东省科学技术厅"

    def fetch_notice_list(self, list_url: str, max_pages: int = 3) -> List[Dict[str, str]]:
        """抓取广东省科技厅通知列表（支持分页）"""
        all_notices = []
        current_page = 1
        
        try:
            while current_page <= max_pages:
                # 构建分页URL
                page_url = list_url if current_page == 1 else f"{list_url}index_{current_page}.html"
                
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
                
                # 检查是否还有下一页
                pagination = soup.find("div", class_="pagination") or soup.find("div", class_="page")
                if pagination:
                    next_link = pagination.find("a", text=lambda t: t and ("下一页" in t or "下页" in t))
                    if not next_link or "disabled" in str(next_link.get("class", [])):
                        break
                
                current_page += 1
                time.sleep(0.5)  # 避免请求过快
            
            return all_notices[:10]  # 限制总数
        except Exception as e:
            print(f"[警告] 抓取 {self.get_site_name()} 列表失败: {str(e)}")
            return all_notices if all_notices else []

    def fetch_notice_detail(self, detail_url: str) -> Dict[str, str]:
        """抓取广东省科技厅通知正文和发布日期"""
        try:
            res = self.get(detail_url, timeout=20)
            res.encoding = res.apparent_encoding or "utf-8"
            soup = BeautifulSoup(res.text, "html.parser")

            # 移除无效标签
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            # 提取发布日期 - 从 zw-info 或 w-title 附近查找
            pub_date = None
            
            # 方式1：从 zw-info 中提取日期
            info_div = soup.find("div", class_="zw-info")
            if info_div:
                info_text = info_div.get_text(strip=True)
                pub_date = self.extract_date_from_text(info_text)
            
            # 方式2：从页面底部的发布日期段落提取
            if not pub_date:
                for p in soup.find_all("p"):
                    text = p.get_text(strip=True)
                    if "发布日期" in text or text.startswith("20") and "年" in text and "月" in text:
                        pub_date = self.extract_date_from_text(text)
                        if pub_date:
                            break

            # 尝试多种方式定位正文
            text = ""
            
            # 方式1：查找 class="w" 的 div（广东省科技厅标准格式 - 从截图中看到）
            content_div = soup.find("div", class_="w")
            if content_div:
                # 查找所有段落，包括 class="indenttext" 的
                paragraphs = content_div.find_all(["p", "div", "span"])
                text = "\n".join(
                    [
                        p.get_text(strip=True)
                        for p in paragraphs
                        if len(p.get_text(strip=True)) > 3
                    ]
                )
            
            # 方式2：查找 class="zw" 的 div（兼容旧格式）
            if not text:
                content_div = soup.find("div", class_="zw")
                if content_div:
                    paragraphs = content_div.find_all(["p", "div"])
                    text = "\n".join(
                        [
                            p.get_text(strip=True)
                            for p in paragraphs
                            if len(p.get_text(strip=True)) > 5
                        ]
                    )
            
            # 方式3：查找 view-content 类
            if not text:
                content_div = soup.find("div", class_="view-content")
                if content_div:
                    text = content_div.get_text(separator="\n", strip=True)
            
            # 方式4：查找所有包含通知正文的div
            if not text:
                for div in soup.find_all("div"):
                    if div.get("class") and any(
                        c in str(div.get("class"))
                        for c in ["content", "detail", "text"]
                    ):
                        text = div.get_text(separator="\n", strip=True)
                        if len(text) > 200:
                            break
            
            # 方式5：兜底 - 提取所有正文段落
            if not text or len(text) < 200:
                paragraphs = soup.find_all("p")
                text = "\n".join(
                    [
                        p.get_text(strip=True)
                        for p in paragraphs
                        if len(p.get_text(strip=True)) > 10
                    ]
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
