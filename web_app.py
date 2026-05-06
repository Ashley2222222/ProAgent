# -*- coding: utf-8 -*-
import json
import os
import threading
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import requests
from urllib3.exceptions import InsecureRequestWarning

from ai_analyzer import ResearchAIAnalyzer
from crawler_factory import ResearchCrawlerFactory
from html_report_generator import generate_html_report
from proposal_generator import generate_proposals_batch
from rag_analyzer import analyze_materials_batch
from config import OUTPUT_DIR, RAG_RESULT_FILENAME, RESULT_FILENAME, WECHAT_WEBHOOK_URL
from urllib.parse import parse_qs, urlparse, unquote

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from config import (
    OUTPUT_DIR,
    RAG_RESULT_FILENAME,
    RESULT_FILENAME,
    WECHAT_WEBHOOK_URL,
    PROJECT_ROOT,
)

JOBS = {}
JOBS_LOCK = threading.Lock()


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _log(job_id: str, message: str) -> None:
    line = f"[{_now_str()}] {message}"
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is not None:
            job["logs"].append(line)


def _send_wechat_message(message: str) -> str:
    if not WECHAT_WEBHOOK_URL:
        return "未配置企业微信 WECHAT_WEBHOOK_URL"
    headers = {"Content-Type": "application/json"}
    data = {"msgtype": "markdown", "markdown": {"content": message}}
    resp = requests.post(
        WECHAT_WEBHOOK_URL, headers=headers, json=data, verify=False, timeout=30
    )
    resp.raise_for_status()
    r = resp.json()
    if r.get("errcode") == 0:
        return "推送成功"
    return f"推送失败: {r.get('errmsg')}"


def _extract_wechat_webhook_key(webhook_url: str) -> str | None:
    try:
        if not webhook_url:
            return None
        if "key=" not in webhook_url:
            return None
        return webhook_url.split("key=", 1)[1].split("&", 1)[0].strip() or None
    except Exception:
        return None


def _upload_file_to_wechat(file_path: str, webhook_key: str) -> str | None:
    try:
        if not file_path or not os.path.exists(file_path):
            return None
        file_size = os.path.getsize(file_path)
        if not (5 <= file_size <= 20 * 1024 * 1024):
            return None
        if not webhook_key:
            return None

        upload_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={webhook_key}&type=file"
        with open(file_path, "rb") as f:
            files = {
                "media": (os.path.basename(file_path), f, "application/octet-stream")
            }
            resp = requests.post(upload_url, files=files, timeout=60, verify=False)
        resp.raise_for_status()
        result = resp.json()
        if result.get("errcode") == 0 and result.get("media_id"):
            return result["media_id"]
        return None
    except Exception:
        return None


def _send_wechat_file(media_id: str) -> str:
    if not WECHAT_WEBHOOK_URL:
        return "未配置企业微信 WECHAT_WEBHOOK_URL"
    if not media_id:
        return "media_id 为空"
    headers = {"Content-Type": "application/json"}
    data = {"msgtype": "file", "file": {"media_id": media_id}}
    resp = requests.post(
        WECHAT_WEBHOOK_URL, headers=headers, json=data, verify=False, timeout=30
    )
    resp.raise_for_status()
    r = resp.json()
    if r.get("errcode") == 0:
        return "文件推送成功"
    return f"文件推送失败: {r.get('errmsg')}"


def _parse_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ("1", "true", "yes", "on")
    return False


def _run_pipeline(job_id: str, options: dict) -> None:
    with JOBS_LOCK:
        JOBS[job_id]["status"] = "running"
        JOBS[job_id]["options"] = options

    enable_ai = _parse_bool(options.get("enable_ai"))
    enable_rag = _parse_bool(options.get("enable_rag"))
    enable_html = _parse_bool(options.get("enable_html"))
    enable_wechat_markdown = _parse_bool(
        options.get("enable_wechat_markdown", options.get("enable_wechat"))
    )
    enable_wechat_file = _parse_bool(options.get("enable_wechat_file"))
    enable_proposal = _parse_bool(options.get("enable_proposal"))
    start_date = (options.get("start_date") or "").strip() or None
    end_date = (options.get("end_date") or "").strip() or None
    selected_sites = options.get("sites") or []
    if isinstance(selected_sites, str):
        selected_sites = [selected_sites]

    site_configs = ResearchCrawlerFactory.get_all_sites()
    if not selected_sites:
        selected_sites = list(site_configs.keys())
    selected_sites = [s for s in selected_sites if s in site_configs]

    _log(
        job_id,
        f"开始执行：网站 {len(selected_sites)} 个，AI分析={enable_ai}，RAG={enable_rag}，HTML={enable_html}，企业微信摘要={enable_wechat_markdown}，企业微信文件={enable_wechat_file}",
    )
    analyzer = ResearchAIAnalyzer() if enable_ai else None

    all_results = []

    try:
        for site_key in selected_sites:
            config = site_configs[site_key]
            _log(job_id, f"网站：{config.get('description')} ({site_key})")
            crawler = ResearchCrawlerFactory.create_crawler(site_key)

            all_notices = []
            for list_config in config.get("list_urls", []):
                list_url = list_config["url"]
                list_name = list_config.get("name", "未命名")
                _log(job_id, f"列表页：{list_name} {list_url}")
                max_pages = config.get("max_pages", 3)
                notices = crawler.fetch_notice_list(list_url, max_pages=max_pages) or []
                _log(job_id, f"抓取列表：{len(notices)} 条")
                all_notices.extend(notices)

            pre_filter_count = len(all_notices)
            all_notices = [
                n
                for n in all_notices
                if crawler.should_include_notice(n.get("标题", ""))
            ]
            if pre_filter_count != len(all_notices):
                _log(
                    job_id,
                    f"标题过滤：保留 {len(all_notices)} 条（剔除 {pre_filter_count - len(all_notices)} 条）",
                )

            deduped = []
            seen = set()
            for n in all_notices:
                link = (n.get("链接") or "").strip()
                title = (n.get("标题") or "").strip()
                key = link or title
                if not key:
                    continue
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(n)
            if len(deduped) != len(all_notices):
                _log(job_id, f"去重：保留 {len(deduped)} 条（剔除 {len(all_notices) - len(deduped)} 条重复）")
            all_notices = deduped

            for idx, notice in enumerate(all_notices, 1):
                title = notice.get("标题") or ""
                link = notice.get("链接") or ""
                _log(job_id, f"详情抓取：{idx}/{len(all_notices)} {title[:40]}")
                detail = crawler.fetch_notice_detail(link)
                content = detail.get("content", "") if isinstance(detail, dict) else ""
                pub_date = notice.get("发布日期")
                if isinstance(detail, dict) and detail.get("pub_date"):
                    pub_date = detail.get("pub_date")

                if start_date or end_date:
                    if not crawler.is_date_in_range(pub_date, start_date, end_date):
                        continue

                if not content or "失败" in content:
                    continue

                if enable_ai and analyzer is not None:
                    ai_result = analyzer.analyze_notice(title, content)
                    result = {
                        "网站": crawler.get_site_name(),
                        "标题": title,
                        "发布日期": pub_date,
                        "链接": link,
                        "正文长度": len(content),
                        "正文预览": content[:30000],
                        "分析结果": ai_result,
                    }
                else:
                    result = {
                        "网站": crawler.get_site_name(),
                        "标题": title,
                        "发布日期": pub_date,
                        "链接": link,
                        "正文长度": len(content),
                        "正文预览": content[:30000],
                    }
                all_results.append(result)

        os.makedirs(os.path.join(PROJECT_ROOT, OUTPUT_DIR), exist_ok=True)
        crawl_path = os.path.join(PROJECT_ROOT, OUTPUT_DIR, RESULT_FILENAME)
        with open(crawl_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        _log(job_id, f"爬取结果已保存：{crawl_path}")

        results_for_html = all_results
        rag_path = None
        html_path = None
        html_filename = None
        materials_results = None
        if enable_rag and all_results:
            _log(job_id, "开始RAG材料提取")
            materials_results = analyze_materials_batch(all_results)
            rag_path = os.path.join(PROJECT_ROOT, OUTPUT_DIR, RAG_RESULT_FILENAME)
            with open(rag_path, "w", encoding="utf-8") as f:
                json.dump(materials_results, f, ensure_ascii=False, indent=2)
            _log(job_id, f"RAG结果已保存:{rag_path}")
            if materials_results:
                results_for_html = materials_results
            else:
                results_for_html = all_results  # 回退到原始爬取结果

        if enable_proposal and all_results:
            proposals_dir = os.path.join(OUTPUT_DIR, "proposals")
            if enable_rag and materials_results:
                _log(job_id, "开始生成申报建议书（优先使用RAG结果）")
                count = generate_proposals_batch(
                    materials_results, output_dir=proposals_dir
                )
                if count <= 0:
                    _log(job_id, "RAG建议书生成数量为0，回退为基于原始爬取结果生成")
                    from proposal_generator import generate_proposals_from_raw

                    count = generate_proposals_from_raw(
                        all_results, output_dir=proposals_dir
                    )
                _log(job_id, f"建议书生成完成：{count} 份，目录：{proposals_dir}")
            else:
                _log(job_id, "开始生成申报建议书（基于原始爬取结果）")
                from proposal_generator import generate_proposals_from_raw

                count = generate_proposals_from_raw(
                    all_results, output_dir=proposals_dir
                )
                _log(job_id, f"建议书生成完成：{count} 份，目录：{proposals_dir}")

        if enable_html:
            # 决定用于显示的数据源：如果启用了AI分析，优先使用 all_results（含分析结果）
            if enable_ai:
                display_results = all_results
            else:
                display_results = results_for_html if results_for_html else all_results
            if display_results:
                html_filename = (
                    f"政策爬取日报_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                )
                data_dir = OUTPUT_DIR
                os.makedirs(data_dir, exist_ok=True)
                html_path = os.path.join(data_dir, html_filename)
                generate_html_report(display_results, html_path)
                _log(job_id, f"HTML日报已生成：{html_path}")

        if enable_wechat_markdown:
            _log(job_id, "开始企业微信推送（摘要）")
            today = datetime.now().strftime("%Y-%m-%d")
            msg_title = f"【科研课题申报日报】{today}"
            message = f"## {msg_title}\n\n"
            message += f"- **网站**: {len(selected_sites)} 个\n"
            message += f"- **通知**: {len(all_results)} 条\n"
            if start_date or end_date:
                message += (
                    f"- **日期范围**: {start_date or '不限'} 至 {end_date or '不限'}\n"
                )
            if html_filename:
                message += f"- **HTML日报**: {html_filename}\n"
            if rag_path:
                message += f"- **RAG结果**: {os.path.basename(rag_path)}\n"
            res = _send_wechat_message(message)
            _log(job_id, f"企业微信摘要：{res}")

        if enable_wechat_file:
            if not html_path or not os.path.exists(html_path):
                _log(job_id, "企业微信文件：未生成HTML或文件不存在，跳过发送")
            else:
                _log(job_id, "开始企业微信推送（HTML文件）")
                webhook_key = _extract_wechat_webhook_key(WECHAT_WEBHOOK_URL) or ""
                media_id = _upload_file_to_wechat(html_path, webhook_key)
                if not media_id:
                    _log(job_id, "企业微信文件：上传失败（未获取到 media_id）")
                else:
                    res = _send_wechat_file(media_id)
                    _log(job_id, f"企业微信文件：{res}")

        with JOBS_LOCK:
            JOBS[job_id]["status"] = "done"
            JOBS[job_id]["outputs"] = {
                "crawl_path": crawl_path,
                "rag_path": rag_path,
                "html_path": html_path,
                "html_filename": html_filename,
            }
    except Exception as e:
        _log(job_id, f"执行失败：{str(e)}")
        with JOBS_LOCK:
            JOBS[job_id]["status"] = "error"
            JOBS[job_id]["error"] = str(e)


def _html_page() -> str:
    sites = ResearchCrawlerFactory.get_all_sites()
    site_items = []
    for k, cfg in sites.items():
        desc = cfg.get("description") or k
        site_items.append(
            f'<label class="site"><input type="checkbox" name="sites" value="{k}" checked> {desc} <span class="muted">({k})</span></label>'
        )
    sites_html = "\n".join(site_items)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>科研课题申报智能体</title>
  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica Neue,Arial,sans-serif; background:#f6f7fb; margin:0; }}
    .wrap {{ max-width: 1100px; margin: 24px auto; padding: 0 16px; }}
    .card {{ background:#fff; border-radius: 12px; box-shadow: 0 6px 22px rgba(0,0,0,.06); overflow:hidden; }}
    .header {{ padding: 16px 20px; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color:#fff; }}
    .content {{ padding: 18px 20px; display:grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .box {{ border: 1px solid #eef0f6; border-radius: 10px; padding: 14px; }}
    .row {{ display:flex; gap:12px; flex-wrap:wrap; align-items:center; }}
    label {{ font-size: 14px; }}
    input[type="date"] {{ padding: 8px 10px; border: 1px solid #dfe3ee; border-radius: 8px; }}
    .checks {{ display:flex; gap:14px; flex-wrap:wrap; }}
    .site-list {{ max-height: 320px; overflow:auto; padding-right: 6px; }}
    .site {{ display:block; padding: 8px 10px; border-radius: 8px; border: 1px solid #eef0f6; margin-bottom: 8px; }}
    .muted {{ color:#6b7280; font-size:12px; }}
    .actions {{ padding: 0 20px 18px 20px; display:flex; gap:12px; }}
    button {{ border:0; padding: 10px 14px; border-radius: 10px; cursor:pointer; font-weight:600; }}
    .primary {{ background: #2563eb; color:#fff; }}
    .ghost {{ background:#eef2ff; color:#1f3a8a; }}
    .log {{ white-space: pre-wrap; background:#0b1220; color:#cbd5e1; border-radius: 12px; padding: 14px; font-family: ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size: 12px; max-height: 360px; overflow:auto; }}
    .footer {{ padding: 14px 20px; border-top: 1px solid #eef0f6; display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap; }}
    a {{ color:#2563eb; text-decoration:none; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="header">
        <div style="font-size:18px;font-weight:700;">科研课题申报智能体（Web）</div>
        <div style="opacity:.95;margin-top:6px;font-size:13px;">选择日期与网站，点击执行。AI分析 / 生成HTML / 企业微信推送可选。</div>
      </div>
      <div class="content">
        <div class="box">
          <div style="font-weight:700;margin-bottom:10px;">日期范围</div>
          <div class="row">
            <label>开始 <input id="start_date" type="date"></label>
            <label>结束 <input id="end_date" type="date"></label>
          </div>
          <div style="font-weight:700;margin:14px 0 10px;">选项</div>
          <div class="checks">
            <label><input id="enable_ai" type="checkbox"> AI分析</label>
            <label><input id="enable_rag" type="checkbox" checked> RAG提取</label>
            <label><input id="enable_html" type="checkbox" checked> 生成HTML</label>
            <label><input id="enable_wechat_markdown" type="checkbox"> 推送摘要</label>
            <label><input id="enable_wechat_file" type="checkbox"> 推送HTML文件</label>
            <label><input id="enable_proposal" type="checkbox" checked> 生成建议书</label>
          </div>
        </div>
        <div class="box">
          <div style="font-weight:700;margin-bottom:10px;">网站选择</div>
          <div class="site-list" id="site_list">
            {sites_html}
          </div>
          <div class="row" style="margin-top:10px;">
            <button class="ghost" type="button" onclick="selectAll(true)">全选</button>
            <button class="ghost" type="button" onclick="selectAll(false)">全不选</button>
          </div>
        </div>
      </div>
      <div class="actions">
        <button class="primary" onclick="runJob()">开始执行</button>
        <button class="ghost" onclick="clearLog()">清空日志</button>
        <div id="result_links" style="align-self:center;"></div>
      </div>
      <div style="padding: 0 20px 18px 20px;">
        <div class="log" id="log"></div>
      </div>
      <div class="footer">
        <div class="muted">提示：执行期间可保持页面打开，日志会实时刷新。</div>
        <div class="muted">服务端仅在本机运行：建议用于内网/本机环境。</div>
      </div>
    </div>
  </div>

  <script>
    let currentJobId = null;
    let logOffset = 0;

    function selectAll(v) {{
      document.querySelectorAll('input[name=\"sites\"]').forEach(cb => cb.checked = v);
    }}

    function clearLog() {{
      document.getElementById('log').textContent = '';
      document.getElementById('result_links').innerHTML = '';
      logOffset = 0;
    }}

    function getOptions() {{
      const sites = Array.from(document.querySelectorAll('input[name=\"sites\"]:checked')).map(x => x.value);
      return {{
        start_date: document.getElementById('start_date').value,
        end_date: document.getElementById('end_date').value,
        sites,
        enable_ai: document.getElementById('enable_ai').checked,
        enable_rag: document.getElementById('enable_rag').checked,
        enable_html: document.getElementById('enable_html').checked,
        enable_wechat_markdown: document.getElementById('enable_wechat_markdown').checked,
        enable_wechat_file: document.getElementById('enable_wechat_file').checked,
        enable_proposal: document.getElementById('enable_proposal').checked
      }};
    }}

    async function runJob() {{
      clearLog();
      const options = getOptions();
      const resp = await fetch('/api/run', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(options)
      }});
      const data = await resp.json();
      currentJobId = data.job_id;
      pollStatus();
    }}

    async function pollStatus() {{
      if (!currentJobId) return;
      const resp = await fetch('/api/status?id=' + encodeURIComponent(currentJobId));
      const data = await resp.json();
      const logs = data.logs || [];
      if (logs.length > logOffset) {{
        const newLines = logs.slice(logOffset).join('\\n') + '\\n';
        const el = document.getElementById('log');
        el.textContent += newLines;
        el.scrollTop = el.scrollHeight;
        logOffset = logs.length;
      }}
      if (data.outputs && data.outputs.html_filename) {{
        const url = '/files/' + encodeURIComponent(data.outputs.html_filename);
        document.getElementById('result_links').innerHTML = `<a href="${{url}}" target="_blank">打开HTML日报</a>`;
      }}
      if (data.status === 'running') {{
        setTimeout(pollStatus, 1200);
      }}
      if (data.status === 'error') {{
        setTimeout(pollStatus, 2000);
      }}
    }}
  </script>
</body>
</html>"""


def _json_response(handler: BaseHTTPRequestHandler, code: int, obj: dict) -> None:
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _text_response(
    handler: BaseHTTPRequestHandler,
    code: int,
    text: str,
    content_type: str = "text/html; charset=utf-8",
) -> None:
    data = text.encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _safe_report_path(filename: str) -> str | None:
    if not filename:
        return None
    if not filename.endswith(".html"):
        return None
    if not filename.startswith("政策爬取日报_"):
        return None
    # 先在 data 目录下查找（OUTPUT_DIR 已是绝对路径）
    data_dir = OUTPUT_DIR
    full = os.path.abspath(os.path.join(data_dir, filename))
    if not full.startswith(os.path.abspath(data_dir) + os.sep):
        return None
    if os.path.exists(full):
        return full
    # 兼容旧版：再在根目录下查找
    full_root = os.path.abspath(os.path.join(PROJECT_ROOT, filename))
    if full_root.startswith(os.path.abspath(PROJECT_ROOT) + os.sep) and os.path.exists(
        full_root
    ):
        return full_root
    return None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return _text_response(self, 200, _html_page())
        if parsed.path == "/api/status":
            q = parse_qs(parsed.query)
            job_id = (q.get("id") or [""])[0]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
                if not job:
                    return _json_response(self, 404, {"error": "job_not_found"})
                return _json_response(
                    self,
                    200,
                    {
                        "status": job.get("status"),
                        "logs": job.get("logs", []),
                        "outputs": job.get("outputs", {}),
                        "error": job.get("error", ""),
                    },
                )
        if parsed.path.startswith("/files/proposals/"):
            raw_filename = parsed.path[len("/files/proposals/") :]
            filename = unquote(raw_filename)
            if not filename.endswith(".md"):
                return _text_response(
                    self, 404, "not found", "text/plain; charset=utf-8"
                )
            proposals_dir = os.path.join(OUTPUT_DIR, "proposals")
            file_path = os.path.join(proposals_dir, filename)
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            return _text_response(self, 404, "not found", "text/plain; charset=utf-8")
        if parsed.path.startswith("/files/"):
            raw_filename = parsed.path[len("/files/") :]
            # 解码 URL 编码的文件名
            filename = unquote(raw_filename)  # 关键：解码
            # 直接使用 OUTPUT_DIR 绝对路径拼接
            file_path = os.path.join(OUTPUT_DIR, filename)
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            else:
                # 可选：兼容根目录下的旧文件
                file_path_root = os.path.join(PROJECT_ROOT, filename)
                if os.path.exists(file_path_root):
                    with open(file_path_root, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                return _text_response(
                    self, 404, "not found", "text/plain; charset=utf-8"
                )
        if parsed.path.startswith("/proposal/"):
            raw_filename = parsed.path[len("/proposal/") :]
            filename = unquote(raw_filename)
            # 安全检查
            if not filename.endswith(".md"):
                return _text_response(
                    self, 404, "not found", "text/plain; charset=utf-8"
                )
            # 建议书保存在 data/proposals/ 目录下
            proposals_dir = os.path.join(OUTPUT_DIR, "proposals")
            file_path = os.path.join(proposals_dir, filename)
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            else:
                return _text_response(
                    self, 404, "not found", "text/plain; charset=utf-8"
                )

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/run":
            length = int(self.headers.get("Content-Length") or "0")
            body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                options = json.loads(body.decode("utf-8"))
            except Exception:
                options = {}
            job_id = uuid.uuid4().hex
            with JOBS_LOCK:
                JOBS[job_id] = {"status": "queued", "logs": [], "outputs": {}}
            _log(job_id, "任务已创建")
            t = threading.Thread(
                target=_run_pipeline, args=(job_id, options), daemon=True
            )
            t.start()
            return _json_response(self, 200, {"job_id": job_id})
        return _json_response(self, 404, {"error": "not_found"})

    def log_message(self, format, *args):
        return


def serve(host: str = "127.0.0.1", port: int = 8000):
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Web已启动: http://{host}:{port}/", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    serve()
