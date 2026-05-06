# -*- coding: utf-8 -*-
"""
花都区科技工业商务和信息化局爬虫
使用Playwright处理SPA架构
"""
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import time
from .base import BaseResearchCrawler


class HuaduCrawler(BaseResearchCrawler):
    """花都区科技工业商务和信息化局爬虫 - 支持SPA"""

    def get_site_name(self) -> str:
        return "花都区科技工业商务和信息化局"

    def fetch_notice_list(self, list_url: str, max_pages: int = 3) -> List[Dict[str, str]]:
        """抓取花都区科工商信局通知列表（使用Playwright处理SPA）"""
        all_notices = []
        
        try:
            # 尝试使用Playwright获取SPA渲染后的内容
            print(f"  🌐 使用Playwright渲染页面...")
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                # 启动浏览器（无头模式）
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                # 访问列表页
                print(f"    加载页面: {list_url}")
                page.goto(list_url, wait_until='domcontentloaded', timeout=30000)
                
                # 等待表格内容加载（最多5秒）
                try:
                    page.wait_for_selector('table tr', timeout=5000)
                except:
                    pass  # 即使超时也继续
                
                # 额外等待一下确保JS执行
                page.wait_for_timeout(2000)
                
                # 获取渲染后的HTML
                html = page.content()
                
                browser.close()
                
            # 使用BeautifulSoup解析渲染后的HTML
            soup = BeautifulSoup(html, "html.parser")
            
            # 解析table结构（从调试结果看到的结构）
            page_notices = []
            
            # 查找所有包含链接的tr行
            table_rows = soup.find_all("tr")
            print(f"    找到 {len(table_rows)} 个表格行")
            
            for row in table_rows:
                # 在tr中查找a标签
                a_tag = row.find("a", href=True, class_="document-number")
                if not a_tag:
                    a_tag = row.find("a", href=True)
                
                if not a_tag:
                    continue

                title = a_tag.get_text(strip=True)
                href = a_tag["href"]

                if len(title) < 5:
                    continue

                if self.should_include_notice(title):
                    # 处理 // 开头的链接
                    if href.startswith("//"):
                        href = "https:" + href
                    elif href.startswith("http"):
                        full_url = href
                    else:
                        full_url = self.build_full_url(href)
                    
                    # 从行中提取日期（在td中）
                    pub_date = None
                    tds = row.find_all("td")
                    for td in tds:
                        date_text = td.get_text(strip=True)
                        if date_text and len(date_text) == 10 and date_text[4] == '-':
                            # 格式: 2026-02-12
                            pub_date = date_text
                            break
                        else:
                            pub_date = self.extract_date_from_text(date_text)
                            if pub_date:
                                break
                    
                    page_notices.append({
                        "标题": title, 
                        "链接": href if href.startswith("http") else full_url,
                        "发布日期": pub_date
                    })
            
            all_notices.extend(page_notices)
            print(f"    ✅ 成功提取 {len(page_notices)} 条相关通知")
            
        except ImportError:
            print(f"  ⚠️  未安装Playwright，无法渲染SPA页面")
            print(f"  💡 请运行: pip install playwright && playwright install chromium")
        except Exception as e:
            print(f"  ⚠️  Playwright渲染失败: {str(e)}")
        
        return all_notices[:10]

    def fetch_notice_detail(self, detail_url: str) -> Dict[str, Any]:
        """抓取花都区科工商信局通知正文和发布日期"""
        try:
            res = self.get(detail_url, timeout=20)
            res.encoding = res.apparent_encoding or "utf-8"
            soup = BeautifulSoup(res.text, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = ""
            pub_date = None
            
            # 方式1：从 pages-date 中提取发布日期（截图中的结构）
            pages_date = soup.find("div", class_="pages-date")
            if pages_date:
                date_text = pages_date.get_text(strip=True)
                pub_date = self.extract_date_from_text(date_text)
            
            # 方式2：从包含"发布日期"的段落中提取
            if not pub_date:
                for p in soup.find_all("p"):
                    p_text = p.get_text(strip=True)
                    if "发布日期" in p_text or "发布时间" in p_text:
                        pub_date = self.extract_date_from_text(p_text)
                        if pub_date:
                            break
            
            # 方式1：查找 class="article-content" 的正文容器（截图中的结构）
            content_div = soup.find("div", class_="article-content")
            if content_div:
                # 提取所有段落，包括 indenttext2 类的
                paragraphs = content_div.find_all(["p", "div", "span"])
                text = "\n".join(
                    [
                        p.get_text(strip=True)
                        for p in paragraphs
                        if len(p.get_text(strip=True)) > 3
                    ]
                )
            
            # 方式2：尝试其他正文容器
            if not text:
                for class_name in ["content", "article", "detail", "main", "view"]:
                    content_div = soup.find("div", class_=class_name)
                    if content_div:
                        text = content_div.get_text(separator="\n", strip=True)
                        if len(text) > 200:
                            break

            # 兜底：提取所有正文段落
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
