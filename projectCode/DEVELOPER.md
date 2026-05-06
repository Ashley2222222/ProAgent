# 爬虫开发指南

本指南介绍如何为系统添加新的政府网站爬虫。

## 基础结构

所有爬虫都继承自 `BaseResearchCrawler` 基类，需要实现三个方法：

```python
from crawlers.base import BaseResearchCrawler

class ExampleCrawler(BaseResearchCrawler):
    """示例爬虫"""

    def get_site_name(self) -> str:
        """返回网站名称"""
        return "示例网站"

    def fetch_notice_list(self, list_url: str, max_pages: int = 3) -> List[Dict[str, str]]:
        """抓取通知列表"""
        # 实现逻辑
        pass

    def fetch_notice_detail(self, detail_url: str) -> Dict[str, Any]:
        """抓取通知详情"""
        # 实现逻辑
        pass
```

## 方法说明

### 1. get_site_name()

返回网站的完整名称。

```python
def get_site_name(self) -> str:
    return "广东省XXX厅"
```

### 2. fetch_notice_list(list_url, max_pages)

抓取通知列表，返回通知列表数据。

**参数：**
- `list_url`: 列表页URL
- `max_pages`: 最大抓取页数

**返回值：**
```python
[
    {
        "标题": "通知标题",
        "链接": "https://...",
        "发布日期": "2026-03-11"
    },
    ...
]
```

**实现要点：**
- 处理分页（如果有的话）
- 使用 `self.should_include_notice(title)` 过滤不相关的通知
- 使用 `self.extract_date_from_text(text)` 提取日期
- 使用 `self.build_full_url(href)` 构建完整URL

**示例：**

```python
def fetch_notice_list(self, list_url: str, max_pages: int = 3) -> List[Dict[str, str]]:
    all_notices = []

    try:
        page_num = 1
        while page_num <= max_pages:
            print(f"  [INFO] 正在抓取第 {page_num} 页...")

            # 处理分页URL
            if page_num > 1:
                if "?" in list_url:
                    url = f"{list_url}&page={page_num}"
                else:
                    url = f"{list_url}?page={page_num}"
            else:
                url = list_url

            # 发送请求
            res = self.get(url, timeout=20)
            res.encoding = res.apparent_encoding or "utf-8"
            soup = BeautifulSoup(res.text, "html.parser")

            # 查找列表项
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

            # 解析每个列表项
            page_notices = []
            for item in items:
                a_tag = item.find("a", href=True)
                if not a_tag:
                    continue

                title = a_tag.get_text(strip=True)
                href = a_tag["href"]

                if len(title) < 5:
                    continue

                # 过滤不相关的通知
                if self.should_include_notice(title):
                    # 处理链接
                    if href.startswith("//"):
                        href = "https:" + href
                    elif not href.startswith("http"):
                        href = self.build_full_url(href)

                    # 提取日期
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
```

### 3. fetch_notice_detail(detail_url)

抓取通知详情页的正文和发布日期。

**参数：**
- `detail_url`: 详情页URL

**返回值：**
```python
{
    "content": "正文内容文本",
    "pub_date": "2026-03-11"
}
```

**实现要点：**
- 清理不需要的标签（script, style等）
- 查找正文内容区域
- 从正文或特定元素中提取日期
- 限制正文长度避免过长

**示例：**

```python
def fetch_notice_detail(self, detail_url: str) -> Dict[str, Any]:
    try:
        res = self.get(detail_url, timeout=20)
        res.encoding = res.apparent_encoding or "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        # 清理不需要的标签
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = ""
        pub_date = None

        # 查找正文内容区域
        content_div = None
        for class_name in ["content", "article-content", "main-content", "text", "detail-content"]:
            content_div = soup.find("div", class_=class_name)
            if content_div:
                break

        # 从正文提取日期
        if content_div:
            content_text = content_div.get_text(strip=True)
            pub_date = self.extract_date_from_text(content_text)

        # 查找其他日期元素
        if not pub_date:
            for class_name in ["date", "time", "pub-date", "publish-time"]:
                elem = soup.find(["div", "span", "p"], class_=class_name)
                if elem:
                    pub_date = self.extract_date_from_text(elem.get_text(strip=True))
                    if pub_date:
                        break

        # 提取正文
        if content_div:
            paragraphs = content_div.find_all(["p", "div"])
            text = "\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 3])

        # 兜底提取
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
```

## 注册新爬虫

### 1. 创建爬虫文件

在 `crawlers/` 目录下创建新文件，例如 `example.py`。

### 2. 导出爬虫类

在 `crawlers/__init__.py` 中添加：

```python
from .example import ExampleCrawler

__all__ = [
    # ... 其他爬虫
    "ExampleCrawler",
]
```

### 3. 添加网站配置

在 `crawler_factory.py` 的 `SITE_CONFIGS` 中添加：

```python
SITE_CONFIGS = {
    # ... 其他网站配置
    "example.com": {
        "class": ExampleCrawler,
        "base_url": "https://example.com",
        "list_urls": [
            {"url": "https://example.com/notice/", "name": "通知公告"},
        ],
        "description": "示例网站",
        "max_pages": 3,
    },
}
```

## 特殊情况处理

### SPA架构网站

如果网站使用前端渲染（如React、Vue等），需要使用 Playwright：

```python
def fetch_notice_list(self, list_url: str, max_pages: int = 3) -> List[Dict[str, str]]:
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

            page.goto(list_url, wait_until='commit', timeout=20000)
            page.wait_for_timeout(1500)  # 等待JS执行

            html = page.content()
            browser.close()

        # 解析HTML...
        # 后续代码与普通爬虫相同

    except ImportError:
        print(f"  [WARN] 未安装Playwright，无法渲染SPA页面")
        print(f"  [TIP] 请运行: pip install playwright && playwright install chromium")
    except Exception as e:
        print(f"  [WARN] Playwright渲染失败: {str(e)}")

    return all_notices
```

参考 `crawlers/gddrc.py` 和 `crawlers/huadu.py` 的实现。

## 测试

创建测试文件在 `tests/` 目录：

```python
# tests/test_example.py
from crawler_factory import ResearchCrawlerFactory

crawler = ResearchCrawlerFactory.create_crawler('example.com')
config = ResearchCrawlerFactory.SITE_CONFIGS['example.com']

print(f'测试网站: {config["description"]}')

for list_config in config['list_urls']:
    print(f'【列表页】{list_config["name"]}')
    notices = crawler.fetch_notice_list(list_config['url'], max_pages=1)
    print(f'找到 {len(notices)} 条通知')
```

运行测试：
```bash
python tests/test_example.py
```

## 最佳实践

1. **错误处理**：所有网络请求和解析操作都应该有try-except
2. **日志输出**：使用标准化的日志格式 `[INFO]` `[WARN]` 等
3. **日期提取**：优先从列表页提取日期，失败时再从详情页提取
4. **链接处理**：正确处理相对链接和绝对链接
5. **编码问题**：确保使用 `apparent_encoding` 或 `utf-8`
6. **请求频率**：在抓取多个页面时添加适当延迟
7. **文本清理**：移除script、style等无关标签
8. **长度限制**：限制正文长度避免内存问题

## 注意事项

- 遵守网站的robots.txt规则
- 控制请求频率，避免给服务器造成压力
- 不要抓取受版权保护的内容
- 注意个人隐私信息的保护
- 定期检查网站结构变化，及时更新爬虫
