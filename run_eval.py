"""
发布时间提取工具 - 标准评测脚本
用法: python3 run_eval.py [seed] [n]
默认: seed=111, n=50
输出: eval_result_seed{seed}.csv
"""
import pandas as pd
import sys, csv
import urllib3
urllib3.disable_warnings()
from datetime import datetime
from web_server import PublishTimeExtractor

# 参数
seed = int(sys.argv[1]) if len(sys.argv) > 1 else 111
n = int(sys.argv[2]) if len(sys.argv) > 2 else 50

# 加载数据
df = pd.read_csv('/Users/miawu/Downloads/【0521】泛时效收录评估 0514-人评数据.csv', encoding='utf-8-sig')
url_col = df.columns[6]
cat_col = df.columns[30]
time_col = df.columns[31]

exclude_cats = ['非文本', '竞品robots封禁', '墙外风险站', '实时更新页面', 
                '死链', '搜索/AI对话结果', '页面语言非中文', '遗留不评']

def should_exclude(cat):
    if pd.isna(cat): return True
    for ex in exclude_cats:
        if ex in str(cat).strip(): return True
    return False

filtered = df[~df[cat_col].apply(should_exclude)].copy()
filtered = filtered[filtered[url_col].notna() & (filtered[url_col].str.strip() != '')]
filtered = filtered[filtered[time_col].notna() & (filtered[time_col].str.strip() != '')]

print("筛选后有效数据: %d条, 抽样%d条 (seed=%d)" % (len(filtered), n, seed))

extractor = PublishTimeExtractor()

def compute_precision(extracted_time):
    if not extracted_time:
        return ''
    try:
        parts = extracted_time.split(' ')
        time_part = parts[1] if len(parts) > 1 else '00:00:00'
        h, m, s = time_part.split(':')
        if s != '00': return '秒'
        elif m != '00': return '分'
        elif h != '00': return '时'
        else: return '日'
    except:
        return ''

def classify_error(status, diff_seconds, extracted, gt_time_str):
    """ABCDE分类"""
    if status != 'success' or not extracted:
        return 'E_漏提取'
    if diff_seconds is None:
        return 'E_漏提取'  # 时间解析失败
    if abs(diff_seconds) <= 60:
        return 'A_正确'
    if abs(diff_seconds) <= 86400:
        if extracted.endswith('00:00:00'):
            try:
                ext_date = extracted[:10]
                gt_dt = None
                for fmt in ['%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M', '%Y-%m-%d %H:%M', '%Y/%m/%d', '%Y-%m-%d']:
                    try:
                        gt_dt = datetime.strptime(gt_time_str, fmt)
                        break
                    except: continue
                if gt_dt and ext_date == gt_dt.strftime('%Y-%m-%d'):
                    return 'C_只有日期'
            except: pass
        return 'B_偏差'
    return 'D_完全错误'

# 执行测试
sample = filtered.sample(n=n, random_state=seed)
rows = []

for idx, (_, row) in enumerate(sample.iterrows(), 1):
    url = str(row[url_col]).strip()
    gt_time_str = str(row[time_col]).strip()
    
    gt_dt = None
    for fmt in ['%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M', '%Y-%m-%d %H:%M', '%Y/%m/%d', '%Y-%m-%d']:
        try:
            gt_dt = datetime.strptime(gt_time_str, fmt)
            break
        except: continue
    
    result = extractor.extract(url, timeout=10)
    status = result.get('status', '')
    extracted = result.get('extracted_publish_time', '') or ''
    raw_time = result.get('raw_publish_time', '') or ''
    method = result.get('extraction_method', '') or ''
    page_score = result.get('page_score')
    page_features = result.get('page_features', '') or ''
    
    # 计算precision
    precision = compute_precision(extracted)
    
    # 计算diff
    diff_seconds = None
    if extracted and gt_dt:
        try:
            ext_dt = datetime.strptime(extracted, '%Y-%m-%d %H:%M:%S')
            diff_seconds = (ext_dt - gt_dt).total_seconds()
        except: pass
    
    # 分类
    error_type = classify_error(status, diff_seconds, extracted, gt_time_str)
    
    rows.append({
        'url': url,
        'gt_time': gt_time_str,
        'extracted_time': extracted,
        'raw_publish_time': raw_time,
        'method': method,
        'status': status,
        'precision': precision,
        'diff_seconds': diff_seconds if diff_seconds is not None else '',
        'diff_hours': '%.2f' % (diff_seconds/3600) if diff_seconds is not None else '',
        'error_type': error_type,
        'page_score': page_score if page_score is not None else '',
        'page_features': page_features,
    })
    
    if idx % 10 == 0:
        c1 = sum(1 for r in rows if r['error_type'] == 'A_正确')
        print("  %d/%d done (A=%d)" % (idx, n, c1))

# 保存
output_path = '/Users/miawu/WorkBuddy/2026-05-11-task-5/eval_result_seed%d.csv' % seed
fields = ['url','gt_time','extracted_time','raw_publish_time','method','status','precision',
          'diff_seconds','diff_hours','error_type','page_score','page_features']
with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

# 统计
total = len(rows)
from collections import Counter
dist = Counter(r['error_type'] for r in rows)

print("\n" + "="*60)
print("结果 (seed=%d, n=%d)" % (seed, total))
print("="*60)
for t in ['A_正确', 'B_偏差', 'C_只有日期', 'D_完全错误', 'E_漏提取']:
    print("  %s: %d (%.0f%%)" % (t, dist[t], dist[t]/total*100))

c1min = dist['A_正确']
c1day = dist['A_正确'] + dist['B_偏差'] + dist['C_只有日期']
print("\n  <=1min: %d/%d = %.0f%%" % (c1min, total, c1min/total*100))
print("  <=1day: %d/%d = %.0f%%" % (c1day, total, c1day/total*100))
print("\n已保存: %s" % output_path)
