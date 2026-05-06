# 快速开始指南

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

如果某些网站需要渲染（SPA架构），还需要安装 Playwright：

```bash
pip install playwright
playwright install chromium
```

## 2. 配置参数

编辑 `config.py` 文件，根据需要修改配置：

```python
# ========== AI分析配置 ==========

# 是否启用AI分析（需要配置API Key）
ENABLE_AI_ANALYSIS = False

# AI分析过滤选项（推荐设置为True）
AI_ONLY_ANALYZE_VALID = True
# True: 只对符合要求的通知进行AI分析（推荐，节省token）
# False: 对所有通知进行AI分析

# ========== 爬取配置 ==========

# 是否限制每个网站分析的通知数量
LIMIT_NOTICES_PER_SITE = False
# False: 分析所有符合要求的通知（推荐）
# True: 限制数量，使用下面的 MAX_NOTICES_PER_SITE

# 每个网站最多分析的通知数量（仅在 LIMIT_NOTICES_PER_SITE = True 时生效）
MAX_NOTICES_PER_SITE = 3

# ========== 日期范围配置 ==========

DATE_RANGE = {
    "start_date": "2025-01-01",
    "end_date": "2026-12-31",
}
```

### 爬取数量说明

**LIMIT_NOTICES_PER_SITE** 参数控制是否限制分析数量：

- **设置为False**（推荐）：
  - 分析所有符合要求的通知
  - 不会错过任何有价值的信息
  - 系统已经通过关键词和日期过滤，确保所有通知都有价值

- **设置为True**：
  - 只分析前 N 条通知（N = MAX_NOTICES_PER_SITE）
  - 适合通知数量特别多的网站
  - 节省时间和token

**推荐配置**：
```python
LIMIT_NOTICES_PER_SITE = False  # 分析所有符合要求的通知
```

### AI分析过滤说明

**AI_ONLY_ANALYZE_VALID** 参数控制AI分析的范围：

- **设置为True**（推荐）：
  - 只对符合申报要求的通知进行AI分析
  - 符合要求 = 包含"申报"、"课题"、"项目"等关键词，且不包含"公示"、"结果"等排除关键词
  - 大幅节省AI token消耗
  - 输出会显示 `[AI] 通知符合要求，开始AI分析...` 或 `[SKIP] 通知不符合要求，跳过AI分析`

- **设置为False**：
  - 对所有通知进行AI分析
  - 消耗更多AI token
  - 适用于需要全面分析的场景

## 3. 运行程序

```bash
python main.py
```

## 4. 查看结果

结果会保存在 `data/` 目录下：

- `crawl_results.json` - 爬取结果（未启用AI分析时）
- `analysis_results.json` - 分析结果（启用AI分析时）

## 常见问题

### 1. 部分网站抓取失败

某些网站使用SPA架构，需要安装 Playwright。如果看到类似错误：
```
未安装Playwright，无法渲染SPA页面
```

运行以下命令安装：
```bash
pip install playwright
playwright install chromium
```

### 2. 中文乱码问题

程序已配置UTF-8编码，如果在Windows终端看到乱码，请使用PowerShell或支持UTF-8的终端。

### 3. 抓取速度慢

可以减少 `MAX_NOTICES_PER_SITE` 的值，或者减少需要抓取的网站数量。

### 4. 想要只测试某个网站

可以参考 `tests/` 目录中的测试文件，创建自己的测试脚本。

## 输出示例

```
============================================================
科研课题申报智能体 - 开始运行
AI分析模式: 关闭（仅爬取）
============================================================

============================================================
【网站】广东省科学技术厅 - https://gdstc.gd.gov.cn
============================================================

  【列表页】通知公告
  URL: https://gdstc.gd.gov.cn/zwgk_n/tzgg/
  📄 正在抓取第 1 页...
    ✅ 找到 10 条通知

  📊 该网站共找到 10 条相关通知
  📅 日期范围: 2025-01-01 至 2026-12-31
  ✅ 日期过滤后剩余 10 条通知

  【第 1 条】广东省科学技术厅关于征集2026～2027年度广东省重点领域研发计划"量子创新应用"专项指南建议的通知
  发布日期: 2026-03-09
  文章链接: http://gdstc.gd.gov.cn/zwgk_n/tzgg/content/post_4864602.html
  📄 正文长度: 121 字符
  📝 正文预览: 版权所有：广东省科学技术厅粤ICP备05018469...
  ✅ 爬取完成（AI分析已跳过）
```

## 下一步

- 查看 `README.md` 了解更多详细信息
- 查看 `config.py` 了解所有配置选项
- 查看 `tests/` 目录中的测试文件学习如何单独测试某个网站
