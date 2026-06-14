#!/usr/bin/env python3
"""
P2优化计划：针对真实数据测试发现的问题逐个优化

优化项：
1. 懂球帝赛事页识别 - 避免误提取比赛数据
2. regex-cn-date增强 - 提取完整时间（含时分秒）
3. 球迷屋网站专项优化 - 调查页面结构
4. 赛事网站识别 - goal.com等
"""

# P2优化任务清单
优化任务 = [
    {
        "优先级": "P2-1",
        "问题": "懂球帝(m.dongqiudi.com)赛事页误提取历史比赛数据",
        "影响": "3个matchDetail页面提取到2024-2025年的比赛时间",
        "原因": "script-var提取到比赛JSON中的时间",
        "方案": "URL模式识别：/matchDetail/ + 页面特征评分降低",
        "实施": "web_server.py - calculate_page_score()"
    },
    {
        "优先级": "P2-2", 
        "问题": "regex-cn-date方法不完整",
        "影响": "多个页面只提取到年月日，丢失时分秒",
        "原因": "正则模式不包含时间部分",
        "方案": "增强正则：匹配'YYYY年MM月DD日 HH:MM'格式",
        "实施": "web_server.py - extract_from_regex()"
    },
    {
        "优先级": "P2-3",
        "问题": "球迷屋(m.qiumiwu.com)时间不准",
        "影响": "4/4错误，偏差2-23小时",
        "原因": "提取到错误字段或只有日期",
        "方案": "调查页面结构，找准确字段",
        "实施": "需要人工检查HTML"
    },
    {
        "优先级": "P2-4",
        "问题": "赛事网站(goal.com等)提取到比赛时间",
        "影响": "多个赛事页提取到比赛开始时间",
        "原因": "time-tag/meta存放的是比赛时间",
        "方案": "URL模式：/match/、/partido/ + 降低评分",
        "实施": "web_server.py - calculate_page_score()"
    }
]

print("P2优化计划")
print("="*80)
for task in 优化任务:
    print(f"\n【{task['优先级']}】{task['问题']}")
    print(f"影响: {task['影响']}")
    print(f"原因: {task['原因']}")
    print(f"方案: {task['方案']}")
    print(f"实施: {task['实施']}")
