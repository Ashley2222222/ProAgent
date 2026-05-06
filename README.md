# 科研课题申报智能体

一个智能化的政府科研项目申报信息爬取和分析系统，自动从广东省和广州市各级政府部门网站抓取最新的科研项目申报通知，并进行AI智能分析。

[快速开始](#快速开始) | [配置说明](#配置说明) | [更新日志](CHANGELOG.md) | [开发指南](DEVELOPER.md)

## 功能特点

- 🕷️ **多网站爬取**：支持11个政府网站的信息抓取
- 🔍 **智能过滤**：自动过滤申报相关的通知，排除结果公示、评审结束等非申报内容
- 📅 **日期筛选**：支持按日期范围筛选通知
- 🤖 **AI分析**：可选的AI分析功能，自动提取资助金额、截止日期、申请条件等信息
- 📊 **结构化输出**：结果保存为JSON格式，便于后续处理

## 支持的网站

### 省级网站

- 广东省科学技术厅
- 广州市科学技术局
- 花都区科技工业商务和信息化局
- 广东省发展和改革委员会
- 广东省工业和信息化厅
- 广东省商务厅
- 广东省市场监督管理局

### 市级网站

- 广州市发展和改革委员会
- 广州市工业和信息化局
- 广州市商务局
- 广州市市场监督管理局(知识产权)

## 项目结构

```
ProAgent/
├── main.py                 # 主程序入口
├── crawler_factory.py      # 爬虫工厂类
├── ai_analyzer.py          # AI分析器
├── requirements.txt        # 依赖包列表
├── README.md              # 项目说明
├── .gitignore             # Git忽略文件
├── crawlers/              # 爬虫模块
│   ├── base.py           # 基类
│   ├── gdstc.py          # 广东省科学技术厅
│   ├── gzkjj.py          # 广州市科学技术局
│   ├── huadu.py          # 花都区科工商信局
│   ├── gddrc.py          # 广东省发改委
│   ├── gdii.py           # 广东省工信厅
│   ├── gdsw.py           # 广东省商务厅
│   ├── gdmr.py           # 广东省市监局
│   ├── gzfgw.py          # 广州市发改委
│   ├── gzgxi.py          # 广州市工信局
│   ├── gzsw.py           # 广州市商务局
│   └── gzsc.py           # 广州市市监局
├── tests/                # 测试文件
└── data/                 # 数据文件
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 基础使用

# 不指定则爬取所有网站（默认行为）

```bash
python main.py
```

### 命令行选项

运行 `main.py` 时，可以通过命令行参数指定要爬取的网站，而不需要修改配置文件。

| 参数           | 说明                                                         | 示例                                    |
| -------------- | ------------------------------------------------------------ | --------------------------------------- |
| `--sites`      | 指定要爬取的网站标识，多个用逗号分隔。不指定则爬取所有网站。 | `--sites gdstc.gd.gov.cn,kjj.gz.gov.cn` |
| `--list-sites` | 列出所有可用的网站标识及其描述，然后退出程序。               | `--list-sites`                          |

**使用示例：**

````bash
# 查看所有可用的网站标识
python main.py --list-sites

# 只爬取广东省科学技术厅
python main.py --sites gdstc.gd.gov.cn

# 同时爬取广东省科学技术厅和广州市科学技术局
python main.py --sites gdstc.gd.gov.cn,kjj.gz.gov.cn

# 不指定则爬取所有网站（默认行为）
python main.py
```
### 配置选项

编辑 `config.py` 文件，根据需要修改配置：

```python
# ========== AI分析配置 ==========

# 是否启用AI分析
ENABLE_AI_ANALYSIS = False  # True: 启用AI分析, False: 仅爬取和打印信息

# AI分析过滤选项（推荐设置为True）
AI_ONLY_ANALYZE_VALID = True  # True: 只对符合要求的通知进行AI分析, False: 对所有通知进行AI分析

# ========== 爬取配置 ==========

# 是否限制每个网站分析的通知数量
LIMIT_NOTICES_PER_SITE = False  # True: 限制数量, False: 分析所有符合要求的通知（推荐）

# 每个网站最多分析的通知数量（仅在 LIMIT_NOTICES_PER_SITE = True 时生效）
MAX_NOTICES_PER_SITE = 3

# ========== 日期范围配置 ==========

DATE_RANGE = {
    "start_date": "2025-01-01",  # 开始日期（包含）
    "end_date": "2026-12-31",    # 结束日期（包含）
}
````

## 配置说明

### AI分析配置

**AI_ONLY_ANALYZE_VALID** 参数说明：

- **True**（推荐）：只对符合申报要求的通知进行AI分析
  - 节省AI token消耗
  - 只分析有实际价值的通知
  - 符合要求 = 包含申报类关键词 且 不包含排除关键词

- **False**：对所有通知进行AI分析
  - 消耗更多AI token
  - 适用于需要全面分析的场景

### 爬取数量配置

**LIMIT_NOTICES_PER_SITE** 参数说明：

- **False**（推荐）：分析所有符合要求的通知
  - 不会错过任何符合条件的通知
  - 系统已经通过关键词过滤和日期范围过滤，确保所有通知都有价值
  - 建议在首次使用时设置为 False，查看所有符合要求的通知

- **True**：限制分析数量
  - 适合通知数量非常多的网站
  - 节省时间和token
  - 使用 `MAX_NOTICES_PER_SITE` 控制数量

**注意**：系统已经实现了两层过滤：

1. 关键词过滤 - 只保留申报相关的通知
2. 日期范围过滤 - 只保留指定时间段的通知

因此建议设置为 `LIMIT_NOTICES_PER_SITE = False`，分析所有经过过滤的通知。

### 关键词过滤

系统会根据关键词自动过滤申报相关的通知：

**包含关键词**（符合要求）：

- 申报、智慧、人工智能、征集、申请、推荐、遴选、课题、项目、基金、指南、专项、计划

**排除关键词**（不符合要求）：

- 公示、结果、批复、核准、批准、备案、奖励、验收、调研、考察、培训、会议等

### 输出文件

- `crawl_results.json` - 爬取结果（未启用AI分析时）
- `analysis_results.json` - 分析结果（启用AI分析时）

## 开发说明

### 添加新网站

1. 在 `crawlers/` 目录下创建新的爬虫文件，继承 `BaseResearchCrawler`
2. 实现以下方法：
   - `get_site_name()` - 返回网站名称
   - `fetch_notice_list()` - 抓取通知列表
   - `fetch_notice_detail()` - 抓取通知详情
3. 在 `crawlers/__init__.py` 中导出新爬虫类
4. 在 `crawler_factory.py` 中添加网站配置

### 测试

测试文件存放在 `tests/` 目录中，可以单独运行测试文件进行调试。

## 注意事项

- 部分网站使用SPA架构，需要安装 Playwright
- 安装 Playwright: `pip install playwright && playwright install chromium`
- 爬取时请注意网站访问频率，避免给服务器造成压力
- 建议在非高峰时段运行爬虫

## 许可证

MIT License
