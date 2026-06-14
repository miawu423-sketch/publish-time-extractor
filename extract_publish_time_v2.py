#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量提取URL页面发布时间（增强版）
- 支持requests + 浏览器User-Agent
- 多层提取策略
- 支持断点续传
"""

import requests
import pandas as pd
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import time
import logging
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PublishTimeExtractor:
    def __init__(self):
        self.session = requests.Session()
        # 模拟真实浏览器
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
    def extract_from_meta(self, soup):
        """从meta标签提取"""
        meta_properties = [
            'article:published_time',
            'article:published',
            'og:published_time',
            'publishdate',
            'date',
            'pubdate',
            'publication_date',
            'DC.date.issued',
            'datePublished'
        ]
        
        for prop in meta_properties:
            # 尝试 property 属性
            meta = soup.find('meta', property=prop)
            if meta and meta.get('content'):
                return meta['content'], 'meta-property'
            
            # 尝试 name 属性
            meta = soup.find('meta', attrs={'name': prop})
            if meta and meta.get('content'):
                return meta['content'], 'meta-name'
            
            # 尝试 itemprop 属性
            meta = soup.find('meta', itemprop=prop)
            if meta and meta.get('content'):
                return meta['content'], 'meta-itemprop'
        
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
                    fields = [
                        'datePublished', 
                        'publishDate', 
                        'dateCreated', 
                        'uploadDate',
                        'dateModified',
                        'releaseDate'
                    ]
                    for field in fields:
                        if field in item:
                            return item[field], 'json-ld'
                    
                    # 递归检查嵌套对象
                    if isinstance(item, dict):
                        for key, value in item.items():
                            if isinstance(value, dict):
                                for field in fields:
                                    if field in value:
                                        return value[field], 'json-ld-nested'
            except Exception as e:
                continue
        return None, None
    
    def extract_from_time_tag(self, soup):
        """从time标签提取"""
        time_tags = soup.find_all('time')
        for tag in time_tags:
            # 优先取datetime属性
            if tag.get('datetime'):
                return tag['datetime'], 'time-datetime'
            # 其次取pubdate属性的time标签
            if tag.get('pubdate'):
                if tag.get_text(strip=True):
                    return tag.get_text(strip=True), 'time-pubdate'
        
        # 尝试找第一个time标签的文本
        if time_tags:
            text = time_tags[0].get_text(strip=True)
            if text:
                return text, 'time-text'
        
        return None, None
    
    def extract_from_class_id(self, soup):
        """从常见的class/id名称提取"""
        patterns = [
            'publish-time', 'publish_time', 'publishtime',
            'post-time', 'post_time', 'posttime',
            'article-time', 'article_time',
            'date', 'time', 'datetime',
            'pub-date', 'pub_date', 'pubdate',
            'create-time', 'create_time', 'createtime'
        ]
        
        for pattern in patterns:
            # 尝试 class
            elem = soup.find(class_=re.compile(pattern, re.I))
            if elem:
                text = elem.get_text(strip=True)
                if text and self.looks_like_date(text):
                    return text, f'class-{pattern}'
            
            # 尝试 id
            elem = soup.find(id=re.compile(pattern, re.I))
            if elem:
                text = elem.get_text(strip=True)
                if text and self.looks_like_date(text):
                    return text, f'id-{pattern}'
        
        return None, None
    
    def extract_from_text_regex(self, soup):
        """从页面文本正则匹配"""
        # 获取主要内容区域的文本
        main_content = soup.find('article') or soup.find('main') or soup.find('body')
        if not main_content:
            return None, None
        
        text = main_content.get_text()
        
        # 常见日期模式（按优先级）
        patterns = [
            # ISO 8601格式
            (r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}', 'iso-datetime'),
            (r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}', 'datetime-space'),
            (r'\d{4}/\d{2}/\d{2}\s\d{2}:\d{2}', 'datetime-slash'),
            
            # 中文格式
            (r'\d{4}年\d{1,2}月\d{1,2}日\s*\d{1,2}:\d{2}', 'cn-datetime'),
            (r'\d{4}年\d{1,2}月\d{1,2}日', 'cn-date'),
            
            # 纯日期
            (r'\d{4}-\d{2}-\d{2}', 'date-dash'),
            (r'\d{4}/\d{2}/\d{2}', 'date-slash'),
            
            # 月/日/年（美式）
            (r'\d{1,2}/\d{1,2}/\d{4}', 'us-date'),
        ]
        
        # 限制搜索范围：前3000字符（通常发布时间在文章开头）
        text_sample = text[:3000]
        
        for pattern, method_name in patterns:
            match = re.search(pattern, text_sample)
            if match:
                return match.group(), f'regex-{method_name}'
        
        return None, None
    
    def looks_like_date(self, text):
        """判断文本是否像日期"""
        if not text or len(text) > 50:
            return False
        
        # 包含数字和常见日期分隔符
        has_digits = any(c.isdigit() for c in text)
        has_separators = any(sep in text for sep in ['-', '/', ':', '年', '月', '日'])
        
        return has_digits and has_separators
    
    def normalize_date(self, date_str):
        """标准化日期格式为ISO 8601"""
        if not date_str:
            return None
        
        try:
            # 清理文本
            date_str = date_str.strip()
            
            # 常见格式尝试
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d %H:%M',
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    continue
            
            # 处理中文格式
            if '年' in date_str and '月' in date_str:
                # 提取数字
                match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日(?:\s*(\d{1,2}):(\d{2}))?', date_str)
                if match:
                    year, month, day = match.group(1, 2, 3)
                    hour, minute = match.group(4, 5) if match.group(4) else ('00', '00')
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)} {hour.zfill(2)}:{minute}:00"
            
            # 无法解析，返回原始值
            return date_str
            
        except Exception as e:
            return date_str
    
    def extract(self, url, timeout=15):
        """提取单个URL的发布时间"""
        try:
            # 发送请求
            response = self.session.get(
                url, 
                timeout=timeout,
                allow_redirects=True,
                verify=False  # 忽略SSL证书验证
            )
            
            # 检查状态码
            if response.status_code != 200:
                return {
                    'url': url,
                    'extracted_publish_time': None,
                    'extraction_method': None,
                    'status': f'http_{response.status_code}'
                }
            
            # 尝试检测编码
            response.encoding = response.apparent_encoding or 'utf-8'
            html = response.text
            
            # 解析HTML
            soup = BeautifulSoup(html, 'lxml')
            
            # 按优先级尝试各种提取方法
            methods = [
                self.extract_from_meta,
                self.extract_from_jsonld,
                self.extract_from_time_tag,
                self.extract_from_class_id,
                self.extract_from_text_regex
            ]
            
            for method in methods:
                result, method_name = method(soup)
                if result:
                    normalized = self.normalize_date(result)
                    return {
                        'url': url,
                        'extracted_publish_time': normalized,
                        'raw_publish_time': result,
                        'extraction_method': method_name,
                        'status': 'success'
                    }
            
            return {
                'url': url,
                'extracted_publish_time': None,
                'raw_publish_time': None,
                'extraction_method': None,
                'status': 'no_time_found'
            }
            
        except requests.Timeout:
            return {
                'url': url,
                'extracted_publish_time': None,
                'raw_publish_time': None,
                'extraction_method': None,
                'status': 'timeout'
            }
        except requests.ConnectionError:
            return {
                'url': url,
                'extracted_publish_time': None,
                'raw_publish_time': None,
                'extraction_method': None,
                'status': 'connection_error'
            }
        except Exception as e:
            return {
                'url': url,
                'extracted_publish_time': None,
                'raw_publish_time': None,
                'extraction_method': None,
                'status': f'error: {str(e)[:100]}'
            }

def batch_extract(input_csv, output_csv, url_column='url', limit=None, checkpoint_interval=10):
    """批量提取并支持断点续传"""
    
    # 读取输入文件
    df = pd.read_csv(input_csv)
    
    # 限制数量
    if limit and limit > 0:
        df = df.head(limit)
    
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
    start_time = time.time()
    for idx, row in df.iterrows():
        url = row[url_column]
        logger.info(f"处理 [{idx+1}/{total}]: {url}")
        
        result = extractor.extract(url)
        results.append(result)
        
        # 显示结果
        if result['status'] == 'success':
            logger.info(f"  ✓ 成功: {result['extracted_publish_time']} ({result['extraction_method']})")
        else:
            logger.info(f"  ✗ 失败: {result['status']}")
        
        # 定期保存检查点
        if len(results) % checkpoint_interval == 0:
            df_new = pd.DataFrame(results)
            df_combined = pd.concat([df_done, df_new], ignore_index=True)
            df_combined.to_csv(output_csv, index=False, encoding='utf-8-sig')
            logger.info(f"  💾 已保存检查点，累计完成 {len(df_combined)} 条")
            results = []
            df_done = df_combined
        
        # 礼貌延迟
        time.sleep(0.3)
    
    # 保存最终结果
    if results:
        df_new = pd.DataFrame(results)
        df_combined = pd.concat([df_done, df_new], ignore_index=True)
        df_combined.to_csv(output_csv, index=False, encoding='utf-8-sig')
    
    # 统计
    elapsed = time.time() - start_time
    logger.info(f"\n{'='*60}")
    logger.info(f"全部完成！耗时: {elapsed:.1f}秒")
    logger.info(f"结果已保存到: {output_csv}")
    
    df_final = pd.read_csv(output_csv)
    stats = df_final['status'].value_counts()
    logger.info(f"\n提取结果统计 (共{len(df_final)}条):")
    for status, count in stats.items():
        logger.info(f"  {status}: {count} 条 ({count/len(df_final)*100:.1f}%)")
    
    # 提取方法统计
    method_stats = df_final[df_final['status'] == 'success']['extraction_method'].value_counts()
    if not method_stats.empty:
        logger.info(f"\n成功提取方法分布:")
        for method, count in method_stats.items():
            logger.info(f"  {method}: {count} 条")

if __name__ == '__main__':
    import sys
    
    # 配置
    INPUT_CSV = '/Users/miawu/Downloads/泛时效评估_0510-人评数据.csv'
    OUTPUT_CSV = '/Users/miawu/WorkBuddy/2026-05-11-task-5/extracted_results.csv'
    
    # 支持命令行参数
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10  # 默认测试10条
    
    logger.info(f"开始处理，限制数量: {limit if limit > 0 else '全部'}")
    batch_extract(INPUT_CSV, OUTPUT_CSV, url_column='url', limit=limit)
