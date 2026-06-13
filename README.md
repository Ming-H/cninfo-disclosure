# cninfo-annual-report 📄

> Claude Code Skill - 从巨潮资讯网下载 A 股上市公司定期报告 PDF

## 功能

- 📥 **下载定期报告**：年报、半年报、一季报、三季报
- 🔍 **搜索公告**：按公司名称或股票代码搜索
- 📦 **批量下载**：支持下载多年报告、某年全部报告类型
- 🏢 **自动识别交易所**：上交所 / 深交所
- ✅ **智能筛选正本**：自动排除摘要、更正、补充等

## 安装

将此 skill 复制到 Claude Code 的 skills 目录：

```bash
# 全局安装
cp -r cninfo-annual-report ~/.claude/skills/

# 或项目级安装
cp -r cninfo-annual-report your-project/.claude/skills/
```

## 使用方法

### Claude Code 中使用

直接告诉 Claude：

```
帮我下载三一重工 2025 年年报
帮我下载徐工机械近3年的年报
帮我下载杭叉集团 2025 年全部财报
```

### CLI 命令行使用

```bash
# 下载年报
python3 scripts/cli.py download --stock "三一重工" --year 2025 -o /tmp/

# 下载半年报
python3 scripts/cli.py download --stock "三一重工" --year 2025 --type semi -o /tmp/

# 下载一季报
python3 scripts/cli.py download --stock "徐工机械" --year 2025 --type q1 -o /tmp/

# 下载某年全部报告（年报+半年报+一季报+三季报）
python3 scripts/cli.py download --stock "三一重工" --year 2025 --type all -o /tmp/

# 批量下载近3年年报
python3 scripts/cli.py download --stock "三一重工" --year 2023-2025 -o /tmp/

# 搜索公告
python3 scripts/cli.py search --stock "三一重工" --year 2025
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--stock` / `-s` | 股票名称或代码 | 必填 |
| `--year` / `-y` | 年份：`2025` / `2023-2025` / `2023,2025` | 必填 |
| `--type` / `-t` | 报告类型：`annual` / `semi` / `q1` / `q3` / `all` | `annual` |
| `--output` / `-o` | 下载目录 | 当前目录 |
| `--timeout` | 超时秒数 | 30 |

### 报告类型

| 类型 | 参数 | 发布时间 |
|------|------|---------|
| 年报 | `annual` | 次年 3-4 月 |
| 半年报 | `semi` | 当年 7-8 月 |
| 一季报 | `q1` | 当年 4-5 月 |
| 三季报 | `q3` | 当年 10-11 月 |

## 技术特点

- **零依赖**：纯 Python 3 标准库，无需安装任何第三方包
- **数据来源**：[巨潮资讯网](http://www.cninfo.com.cn)（证监会指定信息披露平台）
- **PDF 校验**：自动验证下载文件是否为合法 PDF

## 输出示例

```json
{
  "success": true,
  "stock": "三一重工",
  "total": 3,
  "downloaded": 3,
  "failed": 0,
  "results": [
    {
      "year": 2023,
      "report_label": "年报",
      "downloaded": "/tmp/三一重工_2023年年度报告.pdf",
      "file_size": "5.0MB"
    },
    {
      "year": 2024,
      "report_label": "年报",
      "downloaded": "/tmp/三一重工_2024年年度报告.pdf",
      "file_size": "5.1MB"
    },
    {
      "year": 2025,
      "report_label": "年报",
      "downloaded": "/tmp/三一重工_2025年年度报告.pdf",
      "file_size": "1.6MB"
    }
  ]
}
```

## 许可证

MIT License
