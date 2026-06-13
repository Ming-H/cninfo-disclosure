---
name: cninfo-annual-report
description: 从巨潮资讯网（cninfo.com.cn）搜索并下载 A 股上市公司定期报告 PDF，支持年报、半年报、一季报、三季报，按公司名称或股票代码查询，自动筛选正本（排除摘要、更正等）。当用户需要下载财报、获取年报 PDF、查看公告原文时使用此技能。
license: Complete terms in LICENSE.txt
---

# 巨潮财报下载 使用指南

## 版本

`1.1.0`

## 技能概述

本技能提供上市公司定期报告 PDF 下载能力，支持：

- **年报**（annual）：年度报告
- **半年报**（semi）：半年度报告
- **一季报**（q1）：第一季度报告
- **三季报**（q3）：第三季度报告
- **搜索报告**：按公司名称或股票代码搜索报告公告列表
- **下载报告**：自动筛选正本并下载 PDF 到本地
- **多交易所支持**：自动识别上交所（sse）和深交所（szse）

数据来源：**巨潮资讯网**（http://www.cninfo.com.cn）— 中国证监会指定信息披露平台

## 核心处理流程

### 步骤 1: 接收用户请求

用户指定：
- 股票名称或代码（如 "三一重工" 或 "600031"）
- 报告年份（如 2025）
- 报告类型（可选，默认年报）：annual / semi / q1 / q3
- 下载目录（可选，默认当前目录）

### 步骤 2: 搜索公告

调用巨潮公告查询 API：

```bash
python3 scripts/cli.py search --stock "三一重工" --year 2025
python3 scripts/cli.py search --stock "三一重工" --year 2025 --type semi
python3 scripts/cli.py search --stock "三一重工" --year 2025 --type q1
```

- 自动判断交易所：6 开头代码 → sse，0/3 开头 → szse
- 如果是公司名称（非代码），会两个交易所都搜索
- 客户端按年份过滤结果，确保返回目标年份的报告

### 步骤 3: 筛选报告正本

从搜索结果中自动筛选：
- **必须包含**：对应报告类型的关键词（如"年度报告"、"半年度报告"等）
- **排除**：摘要、更正、补充、修改、英文版等
- 优先选择标题最短的（正本标题通常比摘要短）

### 步骤 4: 下载 PDF

```bash
# 年报（默认）
python3 scripts/cli.py download --stock "三一重工" --year 2025 --output /tmp/

# 半年报
python3 scripts/cli.py download --stock "三一重工" --year 2025 --type semi -o /tmp/

# 一季报
python3 scripts/cli.py download --stock "徐工机械" --year 2025 --type q1 -o /tmp/

# 三季报
python3 scripts/cli.py download --stock "600031" --year 2025 --type q3 -o /tmp/
```

### 步骤 5: 返回结果

输出 JSON 格式的结果：

```json
{
  "success": true,
  "stock": "三一重工",
  "year": 2025,
  "report_type": "annual",
  "report_label": "年报",
  "title": "三一重工股份有限公司2025年年度报告",
  "date": "2026-03-31",
  "pdf_url": "https://static.cninfo.com.cn/finalpage/2026-03-31/1225061378.PDF",
  "downloaded": "/tmp/三一重工_2025年年度报告.pdf",
  "file_size": "1.6MB"
}
```

## CLI 使用方式

### 命令行参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `command` | STRING | 是 | `search`（搜索）或 `download`（下载）|
| `--stock` / `-s` | STRING | 是 | 股票名称或代码 |
| `--year` / `-y` | INT | 是 | 报告年份 |
| `--type` / `-t` | STRING | 否 | 报告类型: annual/semi/q1/q3（默认: annual）|
| `--output` / `-o` | STRING | 否 | 下载目录，仅 download 命令（默认: 当前目录）|
| `--timeout` | INT | 否 | 请求超时秒数（默认: 30）|

### 报告类型说明

| 类型 | 参数 | 发布时间 | 说明 |
|------|------|---------|------|
| 年报 | `annual`（默认） | 次年 3-4 月 | 年度报告，内容最完整 |
| 半年报 | `semi` | 当年 7-8 月 | 半年度报告 |
| 一季报 | `q1` | 当年 4-5 月 | 第一季度报告 |
| 三季报 | `q3` | 当年 10-11 月 | 第三季度报告 |

### 使用示例

```bash
# 搜索年报
python3 scripts/cli.py search --stock "三一重工" --year 2025

# 用股票代码搜索半年报
python3 scripts/cli.py search --stock "600031" --year 2025 --type semi

# 下载年报到指定目录
python3 scripts/cli.py download --stock "三一重工" --year 2025 --output /tmp/

# 下载一季报
python3 scripts/cli.py download --stock "徐工机械" --year 2025 --type q1 -o ~/Downloads/

# 下载深交所公司三季报
python3 scripts/cli.py download --stock "杭叉集团" --year 2025 --type q3 -o /tmp/

# 大文件下载增加超时
python3 scripts/cli.py download --stock "三一重工" --year 2025 --timeout 60
```

## 空数据处理

如果搜索结果为空：

1. 检查公司名称或代码是否正确
2. 检查报告是否已发布（参考上方发布时间表）
3. 尝试用公司全称搜索（如 "三一重工股份有限公司"）
4. 引导用户访问巨潮资讯网: http://www.cninfo.com.cn

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 网络错误 | 提示检查网络连接，稍后重试 |
| 无搜索结果 | 提示报告可能未发布，引导访问巨潮 |
| 找不到正本 | 列出所有可用公告，由用户选择 |
| 非 PDF 文件 | 提示可能是反爬拦截，建议浏览器下载 |

## 数据来源标注

**重要提示**：
- 引用数据时必须标注来源为**巨潮资讯网**（http://www.cninfo.com.cn）
- 所有 PDF 文件版权归原作者公司所有
- 本工具仅供个人学习研究使用

## 代码结构

```
cninfo-annual-report/
├── SKILL.md              # Skill 定义文件
├── LICENSE.txt           # MIT 许可证
└── scripts/
    └── cli.py            # CLI 入口（纯 Python 标准库，无第三方依赖）
```
