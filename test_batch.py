#!/usr/bin/env python3
"""
批量测试脚本
测试1580条URL，对比提取结果与ground truth
"""

import csv
import sys
from datetime import datetime
from web_server import PublishTimeExtractor

def parse_time(time_str):
    """解析ground truth时间"""
    if not time_str or time_str == '/' or time_str.strip() == '':
        return None
    try:
        # 处理各种格式
        time_str = time_str.strip()
        if '/' in time_str:
            dt = datetime.strptime(time_str, '%Y/%m/%d %H:%M:%S')
        elif '-' in time_str:
            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        else:
            return None
        return dt
    except:
        return None

def classify_result(status, extracted_time, gt_type, gt_time):
    """
    分类提取结果
    
    返回类型：
    - 正常：提取成功且时间匹配
    - 未精确到分钟：提取到日期但没有时分秒
    - 无发布时间：正确识别为无发布时间
    - 无法判断时间：无法提取且评分高（应该有时间）
    - 死链：网络错误
    - 无效数据：其他错误
    """
    
    # 死链
    if status == 'timeout' or status == 'browser_error':
        return '死链'
    
    # 无发布时间
    if status == 'no_publish_time':
        if gt_type == '无发布时间':
            return '正常'  # 正确识别
        else:
            return '无效数据'  # 误判为无时间
    
    # 提取失败
    if status == 'extraction_failed':
        if gt_type == '无发布时间' or gt_type == '无法判断时间':
            return '无法判断时间'
        else:
            return '无效数据'  # 应该能提取但失败了
    
    # 提取成功
    if status == 'success':
        if not extracted_time:
            return '无效数据'
        
        # 解析提取到的时间
        try:
            extracted_dt = datetime.strptime(extracted_time, '%Y-%m-%d %H:%M:%S')
        except:
            return '无效数据'
        
        # 如果ground truth是"无发布时间"，但我们提取到了
        if gt_type == '无发布时间':
            return '无效数据'  # 误判
        
        # 如果ground truth是"未精确到分钟"
        if gt_type == '未精确到分钟':
            # 我们提取到了精确时间，算成功
            return '正常'
        
        # 对比时间
        if gt_time:
            gt_dt = parse_time(gt_time)
            if gt_dt:
                # 允许一定误差
                diff_seconds = abs((extracted_dt - gt_dt).total_seconds())
                
                # 完全匹配或相差很小（<5分钟）
                if diff_seconds < 300:
                    return '正常'
                # 日期匹配，时间不同（可能是更新时间）
                elif extracted_dt.date() == gt_dt.date():
                    return '未精确到分钟'
                else:
                    return '无效数据'  # 时间差太大
        
        # 没有ground truth时间，但提取到了
        return '正常'
    
    return '无效数据'

def main():
    print("="*80)
    print("批量测试 - 1580条URL")
    print("="*80)
    
    extractor = PublishTimeExtractor()
    
    # 读取CSV
    results = []
    with open('/Users/miawu/Downloads/突发热点内容覆盖评估 0511-0515-测试.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"总数据量: {len(rows)} 条\n")
    print("开始测试...")
    
    for i, row in enumerate(rows, 1):
        url = row.get('url', '').strip()
        gt_type = row.get('发布时间类型', '').strip()
        gt_time = row.get('发布时间\nxxxx/xx/xx xx:xx:xx', '').strip()
        
        if not url:
            continue
        
        # 提取
        try:
            result = extractor.extract(url, timeout=10)
            status = result.get('status')
            extracted_time = result.get('extracted_publish_time')
            method = result.get('extraction_method')
            
            # 分类
            result_type = classify_result(status, extracted_time, gt_type, gt_time)
            
            results.append({
                'url': url,
                'gt_type': gt_type,
                'gt_time': gt_time,
                'status': status,
                'extracted_time': extracted_time or '',
                'method': method or '',
                'result_type': result_type
            })
            
            # 进度显示
            if i % 50 == 0:
                print(f"进度: {i}/{len(rows)}")
        
        except Exception as e:
            results.append({
                'url': url,
                'gt_type': gt_type,
                'gt_time': gt_time,
                'status': 'error',
                'extracted_time': '',
                'method': '',
                'result_type': '死链'
            })
    
    print("\n测试完成！\n")
    
    # 统计
    type_counts = {}
    for r in results:
        t = r['result_type']
        type_counts[t] = type_counts.get(t, 0) + 1
    
    print("="*80)
    print("结果统计")
    print("="*80)
    total = len(results)
    for t in ['正常', '未精确到分钟', '无发布时间', '无法判断时间', '死链', '无效数据']:
        count = type_counts.get(t, 0)
        pct = count / total * 100 if total > 0 else 0
        print(f"{t}: {count} ({pct:.1f}%)")
    
    print(f"\n总计: {total}")
    
    # 保存结果
    output_file = '/Users/miawu/WorkBuddy/2026-05-11-task-5/test_results.csv'
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = ['url', 'gt_type', 'gt_time', 'status', 'extracted_time', 'method', 'result_type']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n结果已保存到: {output_file}")
    
    # 分析错误case
    print("\n" + "="*80)
    print("错误案例分析（前10个）")
    print("="*80)
    
    error_cases = [r for r in results if r['result_type'] == '无效数据']
    for i, case in enumerate(error_cases[:10], 1):
        print(f"\n【错误{i}】")
        print(f"URL: {case['url']}")
        print(f"Ground Truth: {case['gt_type']} | {case['gt_time']}")
        print(f"提取结果: {case['status']} | {case['extracted_time']}")
        print(f"提取方法: {case['method']}")

if __name__ == '__main__':
    main()
