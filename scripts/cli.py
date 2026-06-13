#!/usr/bin/env python3
"""
巨潮财报下载 - 上市公司定期报告 PDF 搜索与下载 CLI

从巨潮资讯网（cninfo.com.cn）搜索并下载 A 股上市公司定期报告 PDF。
支持年报、半年报、一季报、三季报，支持批量下载多年/多种报告。
使用 Python3 标准库，无第三方依赖。

用法：
  python3 scripts/cli.py download --stock "三一重工" --year 2025
  python3 scripts/cli.py download --stock "三一重工" --year 2025 --type semi
  python3 scripts/cli.py download --stock "三一重工" --years 2023-2025 -o /tmp/
  python3 scripts/cli.py download --stock "三一重工" --year 2025 --type all -o /tmp/
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import List, Optional


SKILL_NAME = "cninfo-annual-report"
SKILL_VERSION = "1.2.0"

CNINFO_QUERY_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_PDF_BASE = "https://static.cninfo.com.cn/"

DEFAULT_TIMEOUT = 30
DEFAULT_PAGE_SIZE = 15

# 报告类型配置
REPORT_TYPES = {
    "annual": {
        "label": "年报",
        "category": "category_ndbg_szsh",
        "search_key": "年度报告",
        "filename_suffix": "年年度报告",
        "include_keyword": "年度报告",
        "date_range": lambda y: (f"{y + 1}-01-01", f"{y + 1}-06-30"),
    },
    "semi": {
        "label": "半年报",
        "category": "category_bndbg_szsh",
        "search_key": "半年度报告",
        "filename_suffix": "年半年度报告",
        "include_keyword": "半年度报告",
        "date_range": lambda y: (f"{y}-07-01", f"{y}-12-31"),
    },
    "q1": {
        "label": "一季报",
        "category": "category_yjdbg_szsh",
        "search_key": "第一季度报告",
        "filename_suffix": "年第一季度报告",
        "include_keyword": "第一季度",
        "date_range": lambda y: (f"{y}-03-01", f"{y}-06-30"),
    },
    "q3": {
        "label": "三季报",
        "category": "category_sjdbg_szsh",
        "search_key": "第三季度报告",
        "filename_suffix": "年第三季度报告",
        "include_keyword": "第三季度",
        "date_range": lambda y: (f"{y}-09-01", f"{y}-12-31"),
    },
}

# 排除关键词（摘要、更正、补充等）
EXCLUDE_KEYWORDS = ["摘要", "更正", "补充", "修改", "英文", "已取消"]


class DownloadError(Exception):
    """下载错误异常类"""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ─── 工具函数 ───────────────────────────────────────────────

def detect_column(stock: str) -> Optional[str]:
    """
    根据股票代码判断交易所。
    6 开头 → sse（上交所），0/3 开头 → szse（深交所）
    非数字（名称）返回 None，后续会两个交易所都试。
    """
    code = stock.strip()
    if re.match(r"^\d{6}$", code):
        if code.startswith("6"):
            return "sse"
        else:
            return "szse"
    return None


def extract_company_name(title: str) -> str:
    """
    从公告标题中提取公司简称。
    优先匹配"股份有限公司"，其次"有限公司"，最后尝试截取到"集团"。
    """
    # 优先匹配最长的公司名前缀
    patterns = [
        r"(.+?)股份有限公司",
        r"(.+?)有限公司",
        r"(.+?)集团",
    ]
    for pattern in patterns:
        m = re.match(pattern, title)
        if m:
            return m.group(1)

    # 都没匹配到，取标题第一个逗号/数字之前的部分
    m = re.match(r"(.+?)(?:\d{4}年|,|，)", title)
    if m:
        return m.group(1)

    return title[:6]


def parse_years(years_str: str) -> List[int]:
    """
    解析年份参数，支持：
    - 单年：2025
    - 范围：2023-2025
    - 枚举：2023,2024,2025
    """
    if "-" in years_str:
        parts = years_str.split("-")
        if len(parts) == 2:
            start, end = int(parts[0]), int(parts[1])
            if start > end:
                start, end = end, start
            return list(range(start, end + 1))
    elif "," in years_str:
        return [int(y.strip()) for y in years_str.split(",")]
    else:
        return [int(years_str)]


# ─── 搜索与下载核心 ─────────────────────────────────────────

def search_announcements(
    stock: str,
    year: int,
    report_type: str = "annual",
    column: str = "sse",
    timeout: int = DEFAULT_TIMEOUT,
) -> list:
    """
    调用巨潮公告查询 API，搜索指定公司的定期报告公告。
    """
    rt = REPORT_TYPES[report_type]
    start_date, end_date = rt["date_range"](year)

    search_key = f"{stock} {rt['search_key']}"

    data = urllib.parse.urlencode({
        "pageNum": "1",
        "pageSize": str(DEFAULT_PAGE_SIZE),
        "column": column,
        "tabName": "fulltext",
        "plate": "",
        "stock": "",
        "searchkey": search_key,
        "secid": "",
        "category": rt["category"],
        "trade": "",
        "seach": "",
        "startDate": start_date,
        "endDate": end_date,
        "isFuzzy": "true",
        "sortName": "",
        "sortOrder": "",
    }).encode("utf-8")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/137.0.0.0 Safari/537.36",
        "Referer": "http://www.cninfo.com.cn/new/disclosure/stock",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    req = urllib.request.Request(
        CNINFO_QUERY_URL, data=data, headers=headers, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise DownloadError(f"巨潮 API 请求失败: HTTP {e.code} {e.reason}", e.code)
    except urllib.error.URLError as e:
        raise DownloadError(f"网络错误: {e.reason}")
    except json.JSONDecodeError:
        raise DownloadError("巨潮 API 返回了非 JSON 格式的响应")

    announcements = result.get("announcements") or []
    if not announcements:
        return []

    parsed = []
    for ann in announcements:
        title = ann.get("announcementTitle", "")
        ts = ann.get("announcementTime", 0)
        adjunct_url = ann.get("adjunctUrl", "")

        if not title or not adjunct_url:
            continue

        # 客户端按年份过滤：标题中必须包含目标年份
        if str(year) not in title:
            continue

        # 时间戳转日期
        date_str = ""
        if ts:
            try:
                date_str = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
            except (ValueError, OSError):
                date_str = str(ts)

        parsed.append({
            "title": title,
            "date": date_str,
            "adjunct_url": adjunct_url,
            "pdf_url": CNINFO_PDF_BASE + adjunct_url,
        })

    return parsed


def search_all_columns(
    stock: str, year: int, report_type: str = "annual",
    timeout: int = DEFAULT_TIMEOUT,
) -> list:
    """搜索公告。如果无法确定交易所，会两个交易所都尝试。"""
    column = detect_column(stock)

    if column:
        return search_announcements(
            stock, year, report_type=report_type, column=column, timeout=timeout
        )
    else:
        all_results = []
        for col in ["sse", "szse"]:
            try:
                results = search_announcements(
                    stock, year, report_type=report_type,
                    column=col, timeout=timeout,
                )
                all_results.extend(results)
            except DownloadError:
                continue

        # 去重（按 pdf_url）
        seen = set()
        unique = []
        for r in all_results:
            if r["pdf_url"] not in seen:
                seen.add(r["pdf_url"])
                unique.append(r)
        return unique


def filter_report(announcements: list, report_type: str = "annual") -> Optional[dict]:
    """从公告列表中筛选出报告正本（排除摘要、更正等）。"""
    rt = REPORT_TYPES[report_type]
    include_kw = rt["include_keyword"]

    candidates = []
    for ann in announcements:
        title = ann["title"]
        if include_kw not in title:
            continue
        if any(kw in title for kw in EXCLUDE_KEYWORDS):
            continue
        candidates.append(ann)

    if not candidates:
        # 放宽条件：只排除"摘要"
        for ann in announcements:
            title = ann["title"]
            if include_kw in title and "摘要" not in title:
                candidates.append(ann)

    if not candidates:
        return None

    # 优先选标题最短的（正本标题通常最短）
    candidates.sort(key=lambda x: len(x["title"]))
    return candidates[0]


def download_pdf(
    pdf_url: str,
    output_dir: str,
    filename: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """下载 PDF 文件到本地。"""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/137.0.0.0 Safari/537.36",
        "Referer": "http://www.cninfo.com.cn/",
    }

    req = urllib.request.Request(pdf_url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        raise DownloadError(f"PDF 下载失败: HTTP {e.code} {e.reason}", e.code)
    except urllib.error.URLError as e:
        raise DownloadError(f"PDF 下载网络错误: {e.reason}")

    # 验证是否为 PDF
    if not data[:5] == b"%PDF-":
        raise DownloadError(
            f"下载的文件不是合法 PDF（文件头: {data[:20]}），可能是反爬拦截。"
        )

    with open(filepath, "wb") as f:
        f.write(data)

    size_bytes = len(data)
    if size_bytes >= 1024 * 1024:
        size_display = f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        size_display = f"{size_bytes / 1024:.1f}KB"

    return {
        "filepath": filepath,
        "size_bytes": size_bytes,
        "size_display": size_display,
    }


def format_announcements(announcements: list) -> list:
    """格式化公告列表用于输出。"""
    return [
        {"title": ann["title"], "date": ann["date"], "pdf_url": ann["pdf_url"]}
        for ann in announcements
    ]


def download_single(
    stock: str,
    year: int,
    report_type: str,
    output_dir: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """
    下载单个报告。返回结果 dict（含 success 字段）。
    不抛异常，失败时返回 success=false。
    """
    rt = REPORT_TYPES[report_type]

    try:
        # 搜索公告
        announcements = search_all_columns(
            stock=stock, year=year, report_type=report_type, timeout=timeout,
        )

        if not announcements:
            return {
                "success": False,
                "year": year,
                "report_type": report_type,
                "report_label": rt["label"],
                "error": f"未找到 {stock} {year} {rt['label']}",
            }

        # 筛选正本
        target = filter_report(announcements, report_type=report_type)
        if not target:
            return {
                "success": False,
                "year": year,
                "report_type": report_type,
                "report_label": rt["label"],
                "error": "未找到正本（只有摘要或更正版）",
            }

        # 生成文件名
        stock_name = extract_company_name(target["title"])
        filename = f"{stock_name}_{year}{rt['filename_suffix']}.pdf"
        filename = re.sub(r'[\\/:*?"<>|]', '_', filename)

        # 下载
        result = download_pdf(
            pdf_url=target["pdf_url"],
            output_dir=output_dir,
            filename=filename,
            timeout=timeout,
        )

        return {
            "success": True,
            "year": year,
            "report_type": report_type,
            "report_label": rt["label"],
            "title": target["title"],
            "date": target["date"],
            "pdf_url": target["pdf_url"],
            "downloaded": result["filepath"],
            "file_size": result["size_display"],
        }

    except DownloadError as e:
        return {
            "success": False,
            "year": year,
            "report_type": report_type,
            "report_label": rt["label"],
            "error": e.message,
        }


# ─── 子命令：search ──────────────────────────────────────────

def cmd_search(args):
    """搜索报告公告列表。"""
    report_type = args.type
    if report_type == "all":
        # 列出所有类型
        types_to_search = list(REPORT_TYPES.keys())
    else:
        types_to_search = [report_type]

    years = parse_years(args.year)

    all_announcements = []
    for rt_key in types_to_search:
        rt = REPORT_TYPES[rt_key]
        for y in years:
            try:
                anns = search_all_columns(
                    stock=args.stock, year=y, report_type=rt_key, timeout=args.timeout,
                )
                for ann in anns:
                    ann["report_type"] = rt_key
                    ann["report_label"] = rt["label"]
                all_announcements.extend(anns)
            except DownloadError:
                continue

    output = {
        "success": True,
        "stock": args.stock,
        "total": len(all_announcements),
        "announcements": format_announcements(all_announcements),
    }

    if not all_announcements:
        output["tip"] = "未找到公告。可能该报告尚未发布，或公司名称/年份有误。"

    print(json.dumps(output, ensure_ascii=False, indent=2))


# ─── 子命令：download ───────────────────────────────────────

def cmd_download(args):
    """搜索并下载报告 PDF。"""
    output_dir = args.output or "."
    years = parse_years(args.year)

    # 确定要下载的报告类型列表
    if args.type == "all":
        type_keys = list(REPORT_TYPES.keys())
    else:
        type_keys = [args.type]

    # 构建下载任务列表
    tasks = []
    for y in years:
        for t in type_keys:
            tasks.append({"year": y, "type": t})

    # 逐个下载
    results = []
    for task in tasks:
        result = download_single(
            stock=args.stock,
            year=task["year"],
            report_type=task["type"],
            output_dir=output_dir,
            timeout=args.timeout,
        )
        results.append(result)

    # 汇总输出
    succeeded = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    output = {
        "success": len(succeeded) > 0,
        "stock": args.stock,
        "total": len(tasks),
        "downloaded": len(succeeded),
        "failed": len(failed),
        "results": results,
    }

    if failed:
        output["failed_details"] = [
            {"year": r["year"], "type": r.get("report_type", ""), "error": r.get("error", "")}
            for r in failed
        ]

    print(json.dumps(output, ensure_ascii=False, indent=2))


# ─── 参数解析 ────────────────────────────────────────────────

def build_parser():
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="巨潮财报下载 - 上市公司定期报告 PDF 搜索与下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 下载年报（默认）
  python3 scripts/cli.py download --stock "三一重工" --year 2025 -o /tmp/

  # 下载半年报
  python3 scripts/cli.py download --stock "三一重工" --year 2025 --type semi -o /tmp/

  # 下载一季报
  python3 scripts/cli.py download --stock "徐工机械" --year 2025 --type q1 -o /tmp/

  # 下载某年全部报告类型（年报+半年报+一季报+三季报）
  python3 scripts/cli.py download --stock "三一重工" --year 2025 --type all -o /tmp/

  # 批量下载近3年年报
  python3 scripts/cli.py download --stock "三一重工" --year 2023-2025 -o /tmp/

  # 批量下载指定年份
  python3 scripts/cli.py download --stock "三一重工" --year 2023,2024,2025 -o /tmp/

  # 搜索公告
  python3 scripts/cli.py search --stock "三一重工" --year 2025
  python3 scripts/cli.py search --stock "三一重工" --year 2025 --type all

报告类型:
  annual  年报（默认）
  semi    半年报
  q1      一季报
  q3      三季报
  all     全部类型

年份格式:
  2025          单年
  2023-2025     范围（2023、2024、2025）
  2023,2024,2025  枚举

数据来源: 巨潮资讯网 (cninfo.com.cn)
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ── search 子命令
    search_parser = subparsers.add_parser("search", help="搜索报告公告列表")
    _add_common_args(search_parser)

    # ── download 子命令
    download_parser = subparsers.add_parser("download", help="搜索并下载报告 PDF")
    _add_common_args(download_parser)
    download_parser.add_argument(
        "--output", "-o",
        type=str,
        default=".",
        help="下载目录（默认: 当前目录）",
    )

    return parser


def _add_common_args(parser):
    """添加公共参数。"""
    parser.add_argument(
        "--stock", "-s",
        type=str,
        required=True,
        help="股票名称或代码（如 '三一重工' 或 '600031'）",
    )
    parser.add_argument(
        "--year", "-y",
        type=str,
        required=True,
        help="年份：单年(2025) / 范围(2023-2025) / 枚举(2023,2025)",
    )
    parser.add_argument(
        "--type", "-t",
        type=str,
        choices=list(REPORT_TYPES.keys()) + ["all"],
        default="annual",
        help="报告类型: annual/semi/q1/q3/all（默认: annual）",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"请求超时秒数（默认: {DEFAULT_TIMEOUT}）",
    )


def main():
    """主函数"""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "search":
        cmd_search(args)
    elif args.command == "download":
        cmd_download(args)


if __name__ == "__main__":
    main()
