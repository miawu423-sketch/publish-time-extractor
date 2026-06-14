# 发布时间提取工具 (Publish Time Extractor)

基于规则 + LLM 兜底的网页发布时间提取工具，用于评估网页内容时效性。

## 功能特性

- **多层提取策略**：meta → JSON-LD → script变量 → time标签 → data属性 → class/id → 正则
- **LLM兜底**：规则失败时调用本地 Qwen2.5:7b（通过 Ollama）
- **浏览器渲染**：SPA页面支持 Playwright headless 渲染
- **时间校验**：自动过滤未来时间、过早时间、访问时间
- **推荐平台黑名单**：头条/百家号等平台取 `datePublished`（避免推荐系统刷新的 `dateModified`）
- **normalize 支持格式**：ISO 8601、RFC 2822、ASP.NET `/Date()`、时间戳、中文日期、点号分隔等
- **Web UI**：支持 CSV 上传和直接粘贴 URL

## 快速开始

### 依赖安装

```bash
pip3 install flask requests beautifulsoup4 lxml pandas playwright
playwright install chromium
```

如需 LLM 兜底，需本地运行 Ollama：
```bash
# 安装 Ollama: https://ollama.com
ollama pull qwen2.5:7b
```

### 启动服务

```bash
# 推荐用系统 Python 3.12（macOS Python 3.13 有 greenlet 签名问题）
nohup /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 web_server.py &
```

访问：http://127.0.0.1:5001

## 文件说明

| 文件 | 说明 |
|------|------|
| `web_server.py` | 核心提取服务（Flask + 提取逻辑） |
| `run_eval.py` | 标准评测脚本，用法：`python run_eval.py [seed] [n]` |
| `dynamic_query_classifier_prompt.md` | 动态更新需求识别 Prompt（天气/彩票/股票等） |
| `extract_publish_time.py` | 早期版本，已弃用 |

## 输出字段

| 字段 | 说明 |
|------|------|
| `extracted_publish_time` | 标准化后的时间（YYYY-MM-DD HH:MM:SS） |
| `precision` | 时间精度：秒/分/时/日/无发布时间/提取失败 |
| `status` | 原始状态：success/no_publish_time/timeout/browser_error 等 |
| `extraction_method` | 提取方法：meta/json-ld/regex/llm-qwen2.5 等 |
| `page_features` | 页面特征分析 |
| `page_score` | 页面评分（>=30 为文章页） |
| `raw_publish_time` | normalize 前的原始时间字符串 |

## 准确率基准（2026-05 评测集）

| 口径 | 准确率 |
|------|--------|
| ≤1分钟 | ~71% |
| ≤1天 | ~78% |

> 注：动态页面（天气/彩票/金融数据）GT与工具提取存在时间差（GT为标注时，工具提取为当前最新），实际有效准确率更高。

## 多设备协同

```bash
# 每次开始工作前，检查是否有远程更新（轻量，只比较commit hash，不下载文件）
git fetch origin main && [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ] && git pull origin main

# 每次完成工作后，提交并推送
git add -A
git commit -m "简述改动"
git push origin main
```
