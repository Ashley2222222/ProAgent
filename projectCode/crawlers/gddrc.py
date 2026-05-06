# -*- coding: utf-8 -*-
"""
广东省发展和改革委员会爬虫
使用Playwright处理SPA架构
"""
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import time
from .base import BaseResearchCrawler


class GDDRCrawler(BaseResearchCrawler):
    """广东省发展和改革委员会爬虫 - 支持SPA"""

    def get_site_name(self) -> str:
        return "广东省发展和改革委员会"

    def fetch_notice_list(self, list_url: str, max_pages: int = 3) -> List[Dict[str, str]]:
        """抓取广东省发改委通知列表（使用Playwright处理SPA）"""
        all_notices = []
        
        try:
            print(f"  [INFO] 使用Playwright渲染页面...")
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                print(f"    加载页面: {list_url}")
                page.goto(list_url, wait_until='commit', timeout=20000)
                
                # 简短等待让JS执行
                page.wait_for_timeout(1500)
                
                html = page.content()
                browser.close()
                
            soup = BeautifulSoup(html, "html.parser")
            
            # 解析列表结构 (ul > li)
            page_notices = []
            all_items = []
            
            # 查找所有ul，收集所有包含申报类长文本链接的ul
            all_uls = soup.find_all("ul")
            for ul in all_uls:
                lis = ul.find_all("li")
                # 检查是否包含长文本链接（内容列表而非导航）
                content_count = 0
                for li in lis[:5]:
                    a = li.find("a")
                    if a and len(a.get_text(strip=True)) > 20:
                        content_count += 1
                # 如果包含内容链接且不是分页导航，收集此ul
                if content_count >= 2:
                    all_items.extend(lis)
            
            items = all_items
            print(f"    找到内容列表: {len(items)} 个li")
            
            for item in items:
                a_tag = item.find("a", href=True)
                if not a_tag:
                    continue

                title = a_tag.get_text(strip=True)
                href = a_tag["href"]

                if len(title) < 5:
                    continue

                if self.should_include_notice(title):
                    # 处理链接
                    if href.startswith("//"):
                        href = "https:" + href
                    elif not href.startswith("http"):
                        href = self.build_full_url(href)
                    
                    # 从item中提取日期
                    pub_date = None
                    item_text = item.get_text(strip=True)
                    pub_date = self.extract_date_from_text(item_text)
                    
                    page_notices.append({
                        "标题": title, 
                        "链接": href,
                        "发布日期": pub_date
                    })
            
            all_notices.extend(page_notices)
            print(f"    [OK] 成功提取 {len(page_notices)} 条相关通知")
            
        except ImportError:
            print(f"  [WARN] 未安装Playwright，无法渲染SPA页面")
            print(f"  [TIP] 请运行: pip install playwright && playwright install chromium")
        except Exception as e:
            print(f"  [WARN] Playwright渲染失败: {str(e)}")
        
        return all_notices[:10]

    def fetch_notice_detail(self, detail_url: str) -> Dict[str, Any]:
        """抓取广东省发改委通知正文和发布日期"""
        try:
            res = self.get(detail_url, timeout=20)
            res.encoding = res.apparent_encoding or "utf-8"
            soup = BeautifulSoup(res.text, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = ""
            pub_date = None
            
            # 方式1：从正文内容中提取日期
            content_div = soup.find("div", class_="content")
            if content_div:
                content_text = content_div.get_text(strip=True)
                pub_date = self.extract_date_from_text(content_text)
            
            # 方式2：查找其他可能的日期元素
            if not pub_date:
                for class_name in ["pages-date", "date", "time"]:
                    elem = soup.find(["div", "span", "p"], class_=class_name)
                    if elem:
                        pub_date = self.extract_date_from_text(elem.get_text(strip=True))
                        if pub_date:
                            break
            
            # 提取正文
            if content_div:
                paragraphs = content_div.find_all(["p", "div"])
                text = "\n".join(
                    [
                        p.get_text(strip=True)
                        for p in paragraphs
                        if len(p.get_text(strip=True)) > 3
                    ]
                )
            
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
