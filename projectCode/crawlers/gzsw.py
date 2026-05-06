# -*- coding: utf-8 -*-
"""
广州市商务局爬虫
"""
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from .base import BaseResearchCrawler


class GZSWcrawler(BaseResearchCrawler):
    """广州市商务局爬虫"""

    def get_site_name(self) -> str:
        return "广州市商务局"

    def fetch_notice_list(self, list_url: str, max_pages: int = 3) -> List[Dict[str, str]]:
        """抓取广州市商务局通知列表"""
        all_notices = []
        
        try:
            page_num = 1
            while page_num <= max_pages:
                print(f"  [INFO] 正在抓取第 {page_num} 页...")
                
                if page_num > 1:
                    if "?" in list_url:
                        url = f"{list_url}&page={page_num}"
                    else:
                        url = f"{list_url}?page={page_num}"
                else:
                    url = list_url
                
                res = self.get(url, timeout=20)
                res.encoding = res.apparent_encoding or "utf-8"
                soup = BeautifulSoup(res.text, "html.parser")
                
                page_notices = []
                
                items = []
                
                for ul in soup.find_all("ul"):
                    lis = ul.find_all("li")
                    content_count = 0
                    for li in lis[:5]:
                        a = li.find("a")
                        if a and len(a.get_text(strip=True)) > 10:
                            content_count += 1
                    if content_count >= 2:
                        items.extend(lis)
                
                for item in items:
                    a_tag = item.find("a", href=True)
                    if not a_tag:
                        continue
                    
                    title = a_tag.get_text(strip=True)
                    href = a_tag["href"]
                    
                    if len(title) < 5:
                        continue
                    
                    if self.should_include_notice(title):
                        if href.startswith("//"):
                            href = "https:" + href
                        elif not href.startswith("http"):
                            href = self.build_full_url(href)
                        
                        pub_date = None
                        item_text = item.get_text(strip=True)
                        pub_date = self.extract_date_from_text(item_text)
                        
                        page_notices.append({
                            "标题": title,
                            "链接": href,
                            "发布日期": pub_date
                        })
                
                if not page_notices:
                    print(f"    本页无数据，停止抓取")
                    break
                
                all_notices.extend(page_notices)
                print(f"    本页提取 {len(page_notices)} 条")
                page_num += 1
                
        except Exception as e:
            print(f"  [WARN] 抓取失败: {str(e)}")
        
        return all_notices

    def fetch_notice_detail(self, detail_url: str) -> Dict[str, Any]:
        """抓取广州市商务局通知正文和发布日期"""
        try:
            res = self.get(detail_url, timeout=20)
            res.encoding = res.apparent_encoding or "utf-8"
            soup = BeautifulSoup(res.text, "html.parser")
            
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            
            text = ""
            pub_date = None
            
            content_div = None
            for class_name in ["content", "article-content", "main-content", "text", "detail-content"]:
                content_div = soup.find("div", class_=class_name)
                if content_div:
                    break
            
            if content_div:
                content_text = content_div.get_text(strip=True)
                pub_date = self.extract_date_from_text(content_text)
            
            if not pub_date:
                for class_name in ["date", "time", "pub-date", "publish-time"]:
                    elem = soup.find(["div", "span", "p"], class_=class_name)
                    if elem:
                        pub_date = self.extract_date_from_text(elem.get_text(strip=True))
                        if pub_date:
                            break
            
            if content_div:
                paragraphs = content_div.find_all(["p", "div"])
                text = "\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 3])
            
            if not text or len(text) < 200:
                paragraphs = soup.find_all("p")
                text = "\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 10])
            
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
