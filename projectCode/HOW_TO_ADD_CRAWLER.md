# 如何添加新的网站爬虫？

系统采用工厂模式设计（Factory Pattern），所有爬虫均继承自基础类 `BaseResearchCrawler`。添加一个新的政府网站爬虫非常简单，只需按照以下 3 步操作：

## 第一步：创建新的爬虫类文件

在 `crawlers` 目录下创建一个新的 Python 文件（例如 `my_new_crawler.py`），并定义一个继承自 `BaseResearchCrawler` 的类。

### 基本模板代码：

```python
# -*- coding: utf-8 -*-
from typing import Dict, List, Any
import requests
from bs4 import BeautifulSoup
from .base import BaseResearchCrawler

class MyNewSiteCrawler(BaseResearchCrawler):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 根据需要设置特有的 Headers
        self.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

    def parse_list_page(self, html: str, url: str) -> List[Dict[str, Any]]:
        """
        解析列表页HTML，提取通知列表。
        必须返回一个字典列表，每个字典至少包含: "标题", "链接", "发布日期"(可选)
        """
        notices = []
        soup = BeautifulSoup(html, "html.parser")
        
        # TODO: 找到包含通知的列表DOM元素
        # 例如：<ul class="list-container"> <li><a href="...">标题</a><span>日期</span></li> </ul>
        list_items = soup.find_all("li", class_="list-item-class")
        
        for item in list_items:
            a_tag = item.find("a")
            if not a_tag:
                continue
                
            title = a_tag.get("title") or a_tag.text.strip()
            href = a_tag.get("href")
            
            # 组装完整URL
            full_url = self.get_full_url(url, href)
            
            # 提取日期
            date_span = item.find("span", class_="date-class")
            pub_date = date_span.text.strip() if date_span else ""
            pub_date = self.format_date(pub_date)
            
            notices.append({
                "标题": title,
                "链接": full_url,
                "发布日期": pub_date
            })
            
        return notices

    def parse_detail_page(self, html: str, url: str) -> Dict[str, Any]:
        """
        解析详情页HTML，提取正文内容。
        必须返回一个字典，包含 "content" 字段。可选包含 "pub_date"。
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # TODO: 找到正文所在的DOM元素
        # 例如：<div id="zoom">...</div>
        content_div = soup.find("div", id="zoom") or soup.find("div", class_="article-content")
        
        if content_div:
            # 获取纯文本，去掉多余空行
            text = content_div.get_text(separator="\n", strip=True)
            return {"content": text}
            
        return {"content": ""}
```

## 第二步：在 crawler_factory.py 中注册你的爬虫

打开 `crawler_factory.py`，完成两件事：

1. **导入你的新爬虫类**：
   ```python
   from crawlers.my_new_crawler import MyNewSiteCrawler
   ```

2. **在 `create_crawler` 方法中添加实例化逻辑**：
   ```python
   @classmethod
   def create_crawler(cls, site_key: str):
       config = cls.get_config(site_key)
       if not config:
           raise ValueError(f"未知网站: {site_key}")

       # ... 现有的其他爬虫 ...
       elif site_key == "my_new_site":
           return MyNewSiteCrawler(config)
       else:
           raise NotImplementedError(f"未实现该网站的爬虫: {site_key}")
   ```

## 第三步：在 config_sites.json 中添加网站配置

打开 `config_sites.json`，在最外层的 JSON 对象中加入你新网站的配置信息（注意 `site_key` 要与第二步保持一致）：

```json
{
  "my_new_site": {
    "base_url": "http://www.example.gov.cn",
    "description": "某某省科技厅",
    "max_pages": 3,
    "list_urls": [
      {
        "name": "科技计划通知",
        "url": "http://www.example.gov.cn/tzgg/index.html"
      }
    ]
  }
}
```

## 测试你的爬虫

你可以直接在 `main.py` 中测试，或者新建一个小脚本只调用你的爬虫：

```python
from crawler_factory import ResearchCrawlerFactory

# 创建爬虫
crawler = ResearchCrawlerFactory.create_crawler("my_new_site")

# 测试列表页抓取
notices = crawler.fetch_notice_list("http://www.example.gov.cn/tzgg/index.html", max_pages=1)
print(notices)

# 测试详情页抓取
if notices:
    detail = crawler.fetch_notice_detail(notices[0]['链接'])
    print(detail['content'])
```

这就完成了！你的新爬虫将会自动融入整个主流程、AI分析、材料提取及HTML日报生成体系。
