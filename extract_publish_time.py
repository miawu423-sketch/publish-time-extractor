#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量提取URL页面发布时间（基于HTML源码）
支持断点续传、多层提取策略
"""

import requests
import pandas as pd
import json
import re
from bs4 import BeautifulSoup
from dateparser import parse as date_parse
from datetime import datetime
from pathlib import Path
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PublishTimeExtractor:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
    def extract_from_meta(self, soup):
        """从meta标签提取"""
        meta_properties = [
            'article:published_time',
            'og:published_time',
            'publishdate',
            'date',
            'pubdate'
        ]
        
        for prop in meta_properties:
            meta = soup.find('meta', property=prop) or soup.find('meta', attrs={'name': prop})
            if meta and meta.get('content'):
                return meta['content'], 'meta'
        return None, None
    
    def extract_from_jsonld(self, soup):
        """从JSON-LD结构化数据提取"""
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                # 处理单个对象或数组
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    # 检查常见字段
                    for field in ['datePublished', 'publishDate', 'dateCreated', 'uploadDate']:
                        if field in item:
                            return item[field], 'json-ld'
            except:
                continue
        return None, None
    
    def extract_from_time_tag(self, soup):
        """从time标签提取"""
        time_tags = soup.find_all('time')
        for tag in time_tags:
            # 优先取datetime属性
            if tag.get('datetime'):
                return tag['datetime'], 'time-tag'
            # 其次取文本内容
            if tag.get_text(strip=True):
                return tag.get_text(strip=True), 'time-tag-text'
        return None, None
    
    def extract_from_text(self, soup):
        """从页面文本正则匹配"""
        # 常见日期模式
        patterns = [
            r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}',  # 2026-05-08T10:30:00
            r'\d{4}-\d{2}-\d{2}',  # 2026-05-08
            r'\d{4}/\d{2}/\d{2}',  # 2026/05/08
            r'\d{4}年\d{1,2}月\d{1,2}日',  # 2026年5月8日
        ]
        
        text = soup.get_text()
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(), 'text-regex'
        return None, None
    
    def normalize_date(self, date_str):
        """标准化日期格式为ISO 8601"""
        if not date_str:
            return None
        
        try:
            # 使用dateparser解析各种格式
            dt = date_parse(date_str, languages=['en', 'zh'])
            if dt:
                return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass
        
        return date_str  # 解析失败返回原始值
    
    def extract(self, url, timeout=10):
        """提取单个URL的发布时间"""
        try:
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # 按优先级尝试各种提取方法
            methods = [
                self.extract_from_meta,
                self.extract_from_jsonld,
                self.extract_from_time_tag,
                self.extract_from_text
            ]
            
            for method in methods:
                result, method_name = method(soup)
                if result:
                    normalized = self.normalize_date(result)
                    return {
                        'url': url,
                        'extracted_publish_time': normalized,
                        'extraction_method': method_name,
                        'status': 'success'
                    }
            
            return {
                'url': url,
                'extracted_publish_time': None,
                'extraction_method': None,
                'status': 'no_time_found'
            }
            
        except requests.Timeout:
            return {
                'url': url,
                'extracted_publish_time': None,
                'extraction_method': None,
                'status': 'timeout'
            }
        except Exception as e:
            return {
                'url': url,
                'extracted_publish_time': None,
                'extraction_method': None,
                'status': f'error: {str(e)[:100]}'
            }

def batch_extract(input_csv, output_csv, url_column='url', checkpoint_interval=50):
    """批量提取并支持断点续传"""
    
    # 读取输入文件
    df = pd.read_csv(input_csv)
    total = len(df)
    logger.info(f"总共需要处理 {total} 条URL")
    
    # 检查是否有已完成的进度
    checkpoint_file = Path(output_csv)
    if checkpoint_file.exists():
        df_done = pd.read_csv(output_csv)
        done_urls = set(df_done['url'].tolist())
        df = df[~df[url_column].isin(done_urls)]
        logger.info(f"检测到已完成 {len(done_urls)} 条，剩余 {len(df)} 条")
    else:
        df_done = pd.DataFrame()
    
    # 初始化提取器
    extractor = PublishTimeExtractor()
    results = []
    
    # 开始提取
    for idx, row in df.iterrows():
        url = row[url_column]
        logger.info(f"处理 [{idx+1}/{total}]: {url}")
        
        result = extractor.extract(url)
        results.append(result)
        
        # 定期保存检查点
        if len(results) % checkpoint_interval == 0:
            df_new = pd.DataFrame(results)
            df_combined = pd.concat([df_done, df_new], ignore_index=True)
            df_combined.to_csv(output_csv, index=False)
            logger.info(f"已保存检查点，累计完成 {len(df_combined)} 条")
            results = []
            df_done = df_combined
        
        # 礼貌延迟，避免被封
        time.sleep(0.5)
    
    # 保存最终结果
    if results:
        df_new = pd.DataFrame(results)
        df_combined = pd.concat([df_done, df_new], ignore_index=True)
        df_combined.to_csv(output_csv, index=False)
    
    logger.info(f"全部完成！结果已保存到: {output_csv}")
    
    # 输出统计
    df_final = pd.read_csv(output_csv)
    stats = df_final['status'].value_counts()
    logger.info("\n提取结果统计:")
    for status, count in stats.items():
        logger.info(f"  {status}: {count} 条 ({count/len(df_final)*100:.1f}%)")

if __name__ == '__main__':
    # 配置文件路径
    INPUT_CSV = '/Users/miawu/Downloads/0509泛时效抓竞品_20260509180033_coverage_result_google.csv'
    OUTPUT_CSV = '/Users/miawu/WorkBuddy/2026-05-11-task-5/extracted_publish_times.csv'
    
    batch_extract(INPUT_CSV, OUTPUT_CSV, url_column='url')
