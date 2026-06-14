"""测试更多日期提取模式"""
import re
from bs4 import BeautifulSoup

# 模拟一些常见的HTML模式
test_cases = [
    # 常见的动态网站模式
    '<div class="pub-time">发布于 2026-03-15</div>',
    '<span data-time="1678876800">2026-03-15 14:30</span>',
    '<div class="article-info"><span>2026年3月15日14:30</span></div>',
    # JSON格式
    'window.__INITIAL_STATE__ = {"publishTime": "2026-03-15 14:30:00"}',
    'var articleData = {pubTime: "2026-03-15"}',
    # 特殊格式
    '<time class="entry-date" datetime="2026-03-15T14:30:00+08:00">March 15, 2026</time>',
]

# 增强的正则模式
enhanced_patterns = [
    # 数据属性
    (r'data-time["\']?\s*[:=]\s*["\']?(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?\s*\d{1,2}:\d{2})', 'data-attr'),
    # JavaScript变量
    (r'(?:publishTime|pubTime|publish_time)["\']?\s*[:=]\s*["\'](\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?\s*\d{1,2}:\d{2})', 'js-var'),
    # 时间戳
    (r'data-timestamp["\']?\s*[:=]\s*["\']?(\d{10})', 'timestamp'),
    # 更多前缀
    (r'(?:发布于|发表于|创建于)[：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', 'prefix-cn'),
]

for html in test_cases:
    print(f"\n测试: {html[:60]}...")
    for pattern, name in enhanced_patterns:
        match = re.search(pattern, html, re.I)
        if match:
            print(f"  ✓ 匹配 [{name}]: {match.group(1)}")
            break
    else:
        print("  ✗ 未匹配")
