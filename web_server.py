#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL发布时间提取工具 - Web服务版
本地运行Flask服务，提供网页界面操作
"""

from flask import Flask, render_template_string, request, jsonify, send_file
import requests
import pandas as pd
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime
import time
import io
import traceback
from urllib.parse import urlparse

# Playwright 是可选依赖，不影响静态提取
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    PlaywrightTimeout = Exception  # fallback

app = Flask(__name__)

# HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="data:,">
    <title>URL发布时间提取工具</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }

        .header p {
            opacity: 0.9;
            font-size: 14px;
        }

        .content {
            padding: 30px;
        }

        .section {
            margin-bottom: 30px;
        }

        .section-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #333;
        }

        .upload-area {
            border: 2px dashed #667eea;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            background: #f8f9ff;
            cursor: pointer;
            transition: all 0.3s;
        }

        .upload-area:hover {
            border-color: #764ba2;
            background: #f0f1ff;
        }

        .upload-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }

        input[type="file"] {
            margin-top: 8px;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
        }

        .btn:hover {
            transform: translateY(-2px);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .config-row {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            align-items: center;
        }

        .config-row label {
            font-weight: 500;
            color: #555;
        }

        .config-row select {
            padding: 8px 15px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }

        .progress-section {
            display: none;
        }

        .progress-bar {
            width: 100%;
            height: 30px;
            background: #f0f0f0;
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 15px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 14px;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: #f8f9ff;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }

        .stat-value {
            font-size: 24px;
            font-weight: 700;
            color: #667eea;
        }

        .stat-label {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }

        .log-area {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 8px;
            height: 200px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.6;
        }

        .log-entry {
            margin-bottom: 5px;
        }

        .log-info { color: #4ec9b0; }
        .log-error { color: #f48771; }
        .log-success { color: #89d185; }

        .results-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 14px;
        }

        .results-table th {
            background: #f8f9ff;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #667eea;
        }

        .results-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
        }

        .results-table tr:hover {
            background: #f8f9ff;
        }

        .status-badge {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }

        .status-success {
            background: #d4edda;
            color: #155724;
        }

        .status-error {
            background: #f8d7da;
            color: #721c24;
        }
        
        .status-warning {
            background: #fff3cd;
            color: #856404;
        }
        
        .status-info {
            background: #d1ecf1;
            color: #0c5460;
        }
        
        .feature-text {
            font-size: 12px;
            color: #666;
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .score-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
            margin-right: 5px;
        }
        
        .score-high {
            background: #d4edda;
            color: #155724;
        }
        
        .score-low {
            background: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📅 URL发布时间提取工具</h1>
            <p>本地Python服务 | 强大抓取能力 | 多层提取策略</p>
        </div>

        <div class="content">
            <div class="section">
                <div class="section-title">1. 输入URL</div>
                <!-- 直接粘贴URL -->
                <div style="margin-bottom: 12px;">
                    <textarea id="urlTextarea" placeholder="直接粘贴URL，每行一条" rows="3" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:8px; font-size:13px; resize:vertical;"></textarea>
                    <button class="btn" id="pasteBtn" style="margin-top:8px; padding:6px 16px; font-size:13px;">使用粘贴的URL</button>
                </div>
                <div style="text-align:center; color:#999; font-size:12px; margin-bottom:12px;">—— 或 ——</div>
                <!-- 上传CSV -->
                <div class="upload-area" id="uploadArea">
                    <div class="upload-icon">📁</div>
                    <div>点击或拖拽CSV文件到此处</div>
                    <div style="font-size: 12px; color: #999; margin-top: 10px;">支持包含URL列的CSV文件</div>
                </div>
                <input type="file" id="fileInput" accept=".csv" style="display:none;">
                <button class="btn" id="selectFileBtn" style="margin-top:8px; padding:6px 16px; font-size:13px; background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);">选择CSV文件</button>
            </div>

            <div class="section" id="configSection" style="display: none;">
                <div class="section-title">2. 选择配置</div>
                <div class="config-row">
                    <label>URL所在列名：</label>
                    <select id="urlColumn"></select>
                </div>
                <div class="config-row">
                    <label>提取数量限制：</label>
                    <select id="limitSelect" onchange="toggleCustomLimit()">
                        <option value="10">前10条（测试）</option>
                        <option value="50">前50条</option>
                        <option value="100">前100条</option>
                        <option value="500">前500条</option>
                        <option value="0" selected>全部</option>
                        <option value="custom">自定义</option>
                    </select>
                    <input type="number" id="customLimit" placeholder="输入条数" min="1" style="display:none; width:80px; margin-left:8px; padding:4px 8px; border:1px solid #ddd; border-radius:4px;">
                </div>
                <div style="display: flex; gap: 10px;">
                    <button class="btn" id="startBtn">开始提取</button>
                    <button class="btn" id="pauseBtn" style="display: none; background: linear-gradient(135deg, #ffa500 0%, #ff6347 100%);">暂停</button>
                    <button class="btn" id="stopBtn" style="display: none; background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%);">终止</button>
                </div>
            </div>

            <div class="section progress-section" id="progressSection">
                <div class="section-title">3. 提取进度</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill">0%</div>
                </div>
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-value" id="statTotal">0</div>
                        <div class="stat-label">总数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="statProcessed">0</div>
                        <div class="stat-label">已处理</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="statSuccess">0</div>
                        <div class="stat-label">成功</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="statFailed">0</div>
                        <div class="stat-label">失败</div>
                    </div>
                </div>
                <div class="log-area" id="logArea"></div>
            </div>

            <div class="section" id="resultsSection" style="display: none;">
                <div class="section-title">4. 提取结果</div>
                <button class="btn" id="downloadBtn">下载结果CSV</button>
                <div style="overflow-x: auto; max-height: 500px; overflow-y: auto; margin-top: 20px;">
                    <table class="results-table" id="resultsTable">
                        <thead>
                            <tr>
                                <th>URL</th>
                                <th>提取的发布时间</th>
                                <th>精度</th>
                                <th>状态</th>
                                <th>提取方法</th>
                                <th>页面特征分析</th>
                                <th>页面评分</th>
                                <th>原始时间</th>
                            </tr>
                        </thead>
                        <tbody id="resultsBody"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        console.log('JS loading...');
        let csvData = [];
        let headers = [];
        let results = [];
        let isProcessing = false;
        let isPaused = false;
        let isStopped = false;

        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const pasteBtn = document.getElementById('pasteBtn');
        console.log('Elements:', {uploadArea: !!uploadArea, fileInput: !!fileInput, pasteBtn: !!pasteBtn});

        // 粘贴URL按钮
        pasteBtn.addEventListener('click', () => {
            const text = document.getElementById('urlTextarea').value.trim();
            if (!text) { alert('请先粘贴URL'); return; }
            const urls = text.split(/\\n|\\r/).map(u => u.trim()).filter(u => u && (u.startsWith('http') || u.startsWith('//')));
            if (urls.length === 0) { alert('未检测到有效URL（需以http开头）'); return; }
            // 模拟CSV数据格式
            csvData = urls.map(u => ({url: u}));
            document.getElementById('configSection').style.display = 'block';
            // 自动设置URL列
            const urlColumnSelect = document.getElementById('urlColumn');
            urlColumnSelect.innerHTML = '<option value="url">url</option>';
            urlColumnSelect.value = 'url';
            uploadArea.innerHTML = '<div class="upload-icon">✅</div><div>已加载 ' + urls.length + ' 条URL</div>';
        });

        uploadArea.addEventListener('click', () => fileInput.click());
        document.getElementById('selectFileBtn').addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file) handleFile(file);
        });
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) handleFile(file);
        });

        function handleFile(file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                const text = e.target.result;
                parseCSV(text);
            };
            reader.readAsText(file);
        }

        function parseCSV(text) {
            // 正确解析CSV，支持引号内的换行符
            const rows = [];
            let currentRow = [];
            let currentField = '';
            let inQuotes = false;
            
            for (let i = 0; i < text.length; i++) {
                const char = text[i];
                const nextChar = text[i + 1];
                
                if (char === '"') {
                    if (inQuotes && nextChar === '"') {
                        // 双引号转义
                        currentField += '"';
                        i++; // 跳过下一个引号
                    } else {
                        // 切换引号状态
                        inQuotes = !inQuotes;
                    }
                } else if (char === ',' && !inQuotes) {
                    // 字段分隔符
                    currentRow.push(currentField.trim());
                    currentField = '';
                } else if ((char === '\\n' || char === '\\r') && !inQuotes) {
                    // 行结束（引号外）
                    if (currentField || currentRow.length > 0) {
                        currentRow.push(currentField.trim());
                        if (currentRow.some(f => f)) { // 跳过空行
                            rows.push(currentRow);
                        }
                        currentRow = [];
                        currentField = '';
                    }
                    // 跳过\\r\\n中的\\n
                    if (char === '\\r' && nextChar === '\\n') {
                        i++;
                    }
                } else {
                    // 普通字符（引号内的换行符会保留）
                    currentField += char;
                }
            }
            
            // 处理最后一个字段
            if (currentField || currentRow.length > 0) {
                currentRow.push(currentField.trim());
                if (currentRow.some(f => f)) {
                    rows.push(currentRow);
                }
            }
            
            if (rows.length === 0) {
                addLog('CSV文件为空或格式错误', 'error');
                return;
            }
            
            // 第一行是表头，移除BOM和清理
            headers = rows[0].map(h => h.replace(/^\\uFEFF/, '').replace(/[\\r\\n]+/g, ' ').trim());
            
            // 剩余行是数据
            csvData = rows.slice(1).map(row => {
                const obj = {};
                headers.forEach((h, i) => {
                    obj[h] = row[i] || '';
                });
                return obj;
            });

            const urlColumn = document.getElementById('urlColumn');
            urlColumn.innerHTML = headers.map(h => `<option value="${h}">${h}</option>`).join('');
            
            document.getElementById('configSection').style.display = 'block';
            addLog('文件加载成功，共 ' + csvData.length + ' 行数据，' + headers.length + ' 列', 'success');
        }

        document.getElementById('startBtn').addEventListener('click', startExtraction);
        document.getElementById('pauseBtn').addEventListener('click', togglePause);
        document.getElementById('stopBtn').addEventListener('click', stopExtraction);

        function togglePause() {
            isPaused = !isPaused;
            const pauseBtn = document.getElementById('pauseBtn');
            if (isPaused) {
                pauseBtn.textContent = '继续';
                pauseBtn.style.background = 'linear-gradient(135deg, #4CAF50 0%, #45a049 100%)';
                addLog('已暂停，点击"继续"恢复提取', 'info');
            } else {
                pauseBtn.textContent = '暂停';
                pauseBtn.style.background = 'linear-gradient(135deg, #ffa500 0%, #ff6347 100%)';
                addLog('继续提取...', 'info');
            }
        }

        function stopExtraction() {
            if (confirm('确定要终止提取吗？已提取的结果将保留。')) {
                isStopped = true;
                addLog('用户终止了提取任务', 'error');
                document.getElementById('startBtn').disabled = false;
                document.getElementById('pauseBtn').style.display = 'none';
                document.getElementById('stopBtn').style.display = 'none';
                isProcessing = false;
                if (results.length > 0) {
                    showResults();
                }
            }
        }

        function toggleCustomLimit() {
            const sel = document.getElementById('limitSelect');
            const input = document.getElementById('customLimit');
            input.style.display = sel.value === 'custom' ? 'inline-block' : 'none';
        }

        function getLimit() {
            const sel = document.getElementById('limitSelect').value;
            if (sel === 'custom') {
                return parseInt(document.getElementById('customLimit').value) || 0;
            }
            return parseInt(sel);
        }

        async function startExtraction() {
            if (isProcessing) return;
            
            const urlColumn = document.getElementById('urlColumn').value;
            const limit = getLimit();
            
            const urlsToProcess = limit > 0 ? csvData.slice(0, limit) : csvData;
            
            document.getElementById('progressSection').style.display = 'block';
            document.getElementById('resultsSection').style.display = 'none';
            document.getElementById('startBtn').disabled = true;
            document.getElementById('pauseBtn').style.display = 'inline-block';
            document.getElementById('stopBtn').style.display = 'inline-block';
            isProcessing = true;
            isPaused = false;
            isStopped = false;
            
            results = [];
            updateStats(urlsToProcess.length, 0, 0, 0);
            
            addLog('开始提取，共 ' + urlsToProcess.length + ' 条URL', 'info');

            for (let i = 0; i < urlsToProcess.length; i++) {
                // 检查是否终止
                if (isStopped) {
                    addLog('提取已终止', 'error');
                    break;
                }
                
                // 检查是否暂停
                while (isPaused && !isStopped) {
                    await sleep(500);
                }
                
                if (isStopped) break;
                
                const row = urlsToProcess[i];
                const url = row[urlColumn];
                
                addLog(`[${i+1}/${urlsToProcess.length}] 提取: ${url}`, 'info');
                
                try {
                    const response = await fetch('/extract', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({url: url})
                    });
                    
                    const result = await response.json();
                    results.push(result);
                    
                    const success = results.filter(r => r.status === 'success').length;
                    const failed = results.filter(r => r.status !== 'success').length;
                    updateStats(urlsToProcess.length, i + 1, success, failed);
                    
                    if (result.status === 'success') {
                        addLog(`✓ 成功: ${result.extracted_publish_time} (${result.extraction_method})`, 'success');
                    } else {
                        addLog(`✗ 失败: ${result.status}`, 'error');
                    }
                } catch (error) {
                    addLog(`✗ 错误: ${error.message}`, 'error');
                }
                
                await sleep(300);
            }

            if (!isStopped) {
                addLog('全部完成！', 'success');
            }
            document.getElementById('startBtn').disabled = false;
            document.getElementById('pauseBtn').style.display = 'none';
            document.getElementById('stopBtn').style.display = 'none';
            isProcessing = false;
            if (results.length > 0) {
                showResults();
            }
        }

        function updateStats(total, processed, success, failed) {
            document.getElementById('statTotal').textContent = total;
            document.getElementById('statProcessed').textContent = processed;
            document.getElementById('statSuccess').textContent = success;
            document.getElementById('statFailed').textContent = failed;
            
            const percentage = Math.round((processed / total) * 100);
            const fill = document.getElementById('progressFill');
            fill.style.width = percentage + '%';
            fill.textContent = percentage + '%';
        }

        function addLog(message, type = 'info') {
            const logArea = document.getElementById('logArea');
            const entry = document.createElement('div');
            entry.className = 'log-entry log-' + type;
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            logArea.appendChild(entry);
            logArea.scrollTop = logArea.scrollHeight;
        }

        function showResults() {
            document.getElementById('resultsSection').style.display = 'block';
            const tbody = document.getElementById('resultsBody');
            tbody.innerHTML = results.map(r => {
                // 精度样式
                let precisionClass = 'status-info';
                const precision = r.precision || '';
                if (precision === '秒' || precision === '分') precisionClass = 'status-success';
                else if (precision === '时' || precision === '日') precisionClass = 'status-warning';
                else if (precision === '无发布时间') precisionClass = 'status-info';
                
                // 状态样式
                let statusClass = 'status-success';
                const status = r.status || '';
                if (status === 'success') statusClass = 'status-success';
                else if (status === 'no_publish_time') statusClass = 'status-info';
                else statusClass = 'status-error';
                
                // 页面评分
                let scoreHtml = '-';
                if (r.page_score !== null && r.page_score !== undefined) {
                    const scoreClass = r.page_score >= 30 ? 'score-high' : 'score-low';
                    scoreHtml = `<span class="score-badge ${scoreClass}">${r.page_score}</span>`;
                }
                
                return `
                    <tr>
                        <td style="max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${r.url}">${r.url}</td>
                        <td>${r.extracted_publish_time || '-'}</td>
                        <td><span class="status-badge ${precisionClass}">${precision || '-'}</span></td>
                        <td><span class="status-badge ${statusClass}">${status}</span></td>
                        <td>${r.extraction_method || '-'}</td>
                        <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis;" title="${r.page_features || ''}">${r.page_features || '-'}</td>
                        <td>${scoreHtml}</td>
                        <td>${r.raw_publish_time || '-'}</td>
                    </tr>
                `;
            }).join('');
        }

        document.getElementById('downloadBtn').addEventListener('click', async () => {
            const response = await fetch('/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({results: results})
            });
            
            const blob = await response.blob();
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'extracted_publish_times_' + Date.now() + '.csv';
            link.click();
        });

        function sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }
    </script>
</body>
</html>
'''

class PublishTimeExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive'
        })
        # LLM配置
        self.llm_enabled = True
        self.llm_url = 'http://localhost:11434/api/generate'
        self.llm_model = 'qwen2.5:7b'
    
    def extract_with_llm(self, soup, url):
        """使用本地LLM从HTML中提取发布时间（兜底方法）"""
        if not self.llm_enabled:
            return None, None
        
        try:
            import json as json_mod
            
            # 构造精简HTML片段（控制token量）
            snippets = []
            
            # 1. head中的meta标签
            head = soup.find('head')
            if head:
                metas = head.find_all('meta')
                meta_str = '\n'.join(str(m) for m in metas[:20])
                if meta_str:
                    snippets.append(meta_str[:800])
            
            # 2. 含时间关键词的元素
            import re as re_mod
            time_keywords = re_mod.compile(r'(time|date|publish|发布|更新|时间|日期)', re_mod.I)
            time_elements = []
            for elem in soup.find_all(True):
                # 检查class/id/属性名中是否含时间关键词
                classes = ' '.join(elem.get('class', []))
                elem_id = elem.get('id', '')
                elem_text = elem.get_text(strip=True)[:100]
                if time_keywords.search(classes) or time_keywords.search(elem_id) or (elem_text and time_keywords.search(elem_text)):
                    if elem_text:
                        time_elements.append(str(elem)[:200])
                if len(time_elements) >= 10:
                    break
            if time_elements:
                snippets.append('\n'.join(time_elements))
            
            # 3. 页面正文前1000字符
            body = soup.find('body')
            if body:
                body_text = body.get_text(separator=' ', strip=True)[:1000]
                snippets.append(body_text)
            
            html_snippet = '\n---\n'.join(snippets)[:3000]
            
            if not html_snippet or len(html_snippet) < 10:
                return None, None
            
            # 构造prompt
            current_year = datetime.now().year
            prompt = f"""你是页面时间提取器。从HTML片段中找到页面内容的最新时间。

规则：
1. 优先找"更新时间"、"修改时间"、"数据更新时间"、"modified"
2. 如果没有更新时间，找"发布时间"、"published"
3. 如果时间没有年份，默认是{current_year}年
4. 忽略评论时间、用户注册时间、页脚版权年份
5. 如果找不到，返回null

只输出一行JSON（不要其他文字）：
{{"time":"YYYY-MM-DD HH:MM:SS"}} 或 {{"time":null}}

HTML：
{html_snippet}"""

            resp = requests.post(self.llm_url, json={
                'model': self.llm_model,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0, 'num_predict': 60}
            }, timeout=30)
            
            if resp.status_code != 200:
                return None, None
            
            response_text = resp.json().get('response', '').strip()
            
            # 解析JSON响应
            # 尝试从响应中提取JSON
            json_match = re_mod.search(r'\{[^}]+\}', response_text)
            if json_match:
                try:
                    parsed = json_mod.loads(json_match.group())
                    time_val = parsed.get('time')
                    if time_val and time_val != 'null':
                        # 标准化时间格式
                        normalized = self.normalize_datetime(time_val)
                        if normalized:
                            return normalized, 'llm-qwen2.5'
                except:
                    pass
            
            return None, None
            
        except Exception:
            return None, None
    
    def analyze_page_features(self, soup, url):
        """
        分析页面特征，判断页面是否应该有发布时间
        返回评分（0-100）和特征描述
        分数 >= 30 表示页面应该有发布时间
        """
        score = 0
        features = []
        
        # 正面特征（表示内容页）
        if soup.find('article'):
            score += 20
            features.append('+article标签')
        
        # 作者信息
        author_keywords = ['author', 'byline', 'writer', '作者', '编辑']
        for keyword in author_keywords:
            if soup.find(class_=re.compile(keyword, re.I)) or soup.find(attrs={'name': re.compile(keyword, re.I)}):
                score += 15
                features.append('+作者信息')
                break
        
        # 正文段落数量
        paragraphs = soup.find_all('p')
        meaningful_paragraphs = [p for p in paragraphs if len(p.get_text(strip=True)) > 50]
        if len(meaningful_paragraphs) >= 3:
            score += 15
            features.append(f'+{len(meaningful_paragraphs)}段正文')
        
        # 评论区
        comment_keywords = ['comment', 'reply', '评论', '回复']
        for keyword in comment_keywords:
            if soup.find(class_=re.compile(keyword, re.I)) or soup.find(id=re.compile(keyword, re.I)):
                score += 10
                features.append('+评论区')
                break
        
        # 分享按钮
        share_keywords = ['share', 'social', '分享']
        for keyword in share_keywords:
            if soup.find(class_=re.compile(keyword, re.I)):
                score += 10
                features.append('+分享按钮')
                break
        
        # 标题包含日期
        title = soup.find('title')
        if title and re.search(r'20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}', title.get_text()):
            score += 10
            features.append('+标题含日期')
        
        # 负面特征（表示非内容页）
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        # URL路径特征
        data_page_patterns = ['/team/', '/squad/', '/data/', '/results/', '/lottery/', 
                             '/caipiao/', '/player/', '/person/', '/about/', '/index',
                             '/analyse/', '/analysis/', '/match/', '/fixture/', '/vs/',
                             '/baike/', '/wiki/', '/encyclopedia/',
                             '/matchdetail/']  # P2-1: 懂球帝赛事详情页
        for pattern in data_page_patterns:
            if pattern in path:
                score -= 20
                features.append(f'-URL含{pattern}')
                break
        
        # P2-1: 特殊处理 - 懂球帝赛事页（Script中有历史比赛数据）
        if 'dongqiudi.com' in parsed_url.netloc and '/matchdetail/' in path:
            score -= 30  # 额外降低评分
            features.append('-懂球帝赛事页')
        
        # P2-4: 赛事网站识别（goal.com、statarea.com等）
        match_site_patterns = [
            ('/match/', 'goal.com'),
            ('/partido/', 'espn'),
            ('/compare/', 'statarea'),
            ('/vs-', ''),
            ('/gameId/', 'espn')
        ]
        for url_pattern, domain_hint in match_site_patterns:
            if url_pattern in path:
                if not domain_hint or domain_hint in parsed_url.netloc:
                    score -= 25
                    features.append(f'-赛事比分页({url_pattern})')
                    break
        
        # 标题特征（赛事页/百科页）
        title = soup.find('title')
        if title:
            title_text = title.get_text().lower()
            if ' vs ' in title_text or ' vs. ' in title_text or 'vs' in title_text:
                score -= 15
                features.append('-标题含VS(赛事页)')
            if any(keyword in title_text for keyword in ['分析', 'analysis', '预测', 'prediction']):
                score -= 10
                features.append('-赛事分析页')
            if any(keyword in title_text for keyword in ['百科', 'wiki', '词条', 'encyclopedia']):
                score -= 10
                features.append('-百科页')
        
        # 页面内容特征（百科/人物页）
        text = soup.get_text()
        if any(keyword in text for keyword in ['出生', '生于', '诞生', 'born', 'birthday', 'birth date']):
            birth_count = sum(1 for k in ['出生', '生于', '诞生', 'born'] if k in text.lower())
            if birth_count >= 2:  # 出现2次以上，很可能是人物页
                score -= 10
                features.append('-人物页特征')
        
        # 大量表格（数据页特征）
        tables = soup.find_all('table')
        if len(tables) >= 3:
            score -= 15
            features.append(f'-{len(tables)}个表格')
        
        # 页面极简（可能是静态页）
        all_elements = len(soup.find_all())
        if all_elements < 20:
            score -= 10
            features.append('-极简页面')
        
        # 大量数字（体育数据页特征）
        text = soup.get_text()
        digits_ratio = sum(c.isdigit() for c in text) / max(len(text), 1)
        if digits_ratio > 0.3:
            score -= 10
            features.append('-高数字密度')
        
        return score, features
    
    def extract_with_browser(self, url, timeout=15000):
        """使用浏览器渲染页面后提取（每次创建新实例，避免线程问题）"""
        if not PLAYWRIGHT_AVAILABLE:
            return {'url': url, 'extracted_publish_time': None, 'raw_publish_time': None,
                   'extraction_method': None, 'status': 'browser_unavailable',
                   'page_score': None, 'page_features': 'Playwright未安装，仅支持静态提取'}
        playwright = None
        browser = None
        try:
            # 每次都创建新的 Playwright 实例，避免线程冲突
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=True)
            
            page = browser.new_page()
            page.goto(url, timeout=timeout, wait_until='domcontentloaded')
            
            # 等待可能的动态内容加载
            page.wait_for_timeout(2000)
            
            html = page.content()
            page.close()
            
            soup = BeautifulSoup(html, 'lxml')
            
            # P2优化：提取前先检查是否是明确的赛事页
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            path = parsed_url.path.lower()
            
            # 明确的赛事页模式
            is_match_page = False
            if ('dongqiudi.com' in parsed_url.netloc and '/matchdetail/' in path):
                is_match_page = True
            elif ('goal.com' in parsed_url.netloc and ('/match/' in path or '%e8%a9%a6%e5%90%88' in path)):
                is_match_page = True
            elif ('statarea.com' in parsed_url.netloc and '/compare/' in path):
                is_match_page = True
            elif ('espn' in parsed_url.netloc and ('/partido/' in path or '/gameid/' in path)):
                is_match_page = True
            elif ('7m.com' in parsed_url.netloc and 'analyse' in parsed_url.netloc):
                is_match_page = True
            
            # 明确的无发布时间页面：百科页、首页
            is_no_time_page = False
            if ('baike.com' in parsed_url.netloc and '/wiki/' in path):
                is_no_time_page = True
            elif path in ['/', '']:
                is_no_time_page = True
            
            # P3优化：查询工具页/列表页（有日期显示但不是"发布时间"）
            # 油价查询
            elif ('icauto.com.cn' in parsed_url.netloc and '/oil/price' in path):
                is_no_time_page = True
            # 快递查询
            elif ('kuaidi100.com' in parsed_url.netloc):
                is_no_time_page = True
            # 股吧列表页
            elif ('eastmoney.com' in parsed_url.netloc and '/list/' in path):
                is_no_time_page = True
            # 火车票/机票查询
            elif ('ctrip.com' in parsed_url.netloc and '/trainbooking/' in path.lower()):
                is_no_time_page = True
            # 淘宝产品页
            elif ('taobao.com' in parsed_url.netloc and ('/product' in path or '/chanpin/' in path)):
                is_no_time_page = True
            # UPS快递追踪
            elif ('ups.com' in parsed_url.netloc and '/track' in path):
                is_no_time_page = True
            
            if is_match_page or is_no_time_page:
                return {
                    'url': url,
                    'extracted_publish_time': None,
                    'raw_publish_time': None,
                    'extraction_method': None,
                    'status': 'no_publish_time',
                    'page_score': -30,
                    'page_features': '赛事比分页（无发布时间）'
                }
            
            # 使用相同的提取方法
            methods = [
                lambda s: self.extract_from_meta(s, url),
                lambda s: self.extract_from_jsonld(s, url),
                self.extract_from_script_vars,  # 新增：Script变量提取（SPA应用）
                self.extract_from_time_tag,
                self.extract_from_data_attributes,
                self.extract_from_class_id,
                self.extract_from_regex
            ]
            
            for method in methods:
                result, method_name = method(soup)
                if result:
                    normalized_time = self.normalize_datetime(result)
                    # normalize失败 → 继续尝试下一个方法
                    if not normalized_time:
                        continue
                    # 多重时间校验
                    # 校验1: 未来时间（可能是赛事时间）
                    if self.is_future_time(normalized_time):
                        continue
                    # 校验2: 过于久远（可能是人物生日）
                    if self.is_too_old(normalized_time):
                        continue
                    # 校验3: 页面访问时间（可能是JS生成的当前时间）
                    if self.is_likely_access_time(normalized_time):
                        continue
                    
                    return {
                        'url': url,
                        'extracted_publish_time': normalized_time,
                        'raw_publish_time': result,
                        'extraction_method': f'{method_name}-browser',
                        'status': 'success',
                        'page_score': None,
                        'page_features': None
                    }
            
            # 规则提取失败，尝试LLM兜底（只要HTML有内容就给LLM）
            score, features = self.analyze_page_features(soup, url)
            
            llm_time, llm_method = self.extract_with_llm(soup, url)
            if llm_time:
                # LLM提取成功，同样做时间校验
                if not self.is_future_time(llm_time) and not self.is_too_old(llm_time) and not self.is_likely_access_time(llm_time):
                    return {
                        'url': url,
                        'extracted_publish_time': llm_time,
                        'raw_publish_time': llm_time,
                        'extraction_method': llm_method,
                        'status': 'success',
                        'page_score': score,
                        'page_features': '; '.join(features)
                    }
            
            # LLM也失败
            if score < 30:
                # 判定为：页面本身可能没有发布时间
                return {
                    'url': url,
                    'extracted_publish_time': None,
                    'raw_publish_time': None,
                    'extraction_method': None,
                    'status': 'no_publish_time',
                    'page_score': score,
                    'page_features': '; '.join(features)
                }
            else:
                # 判定为：应该有时间但提取失败
                return {
                    'url': url,
                    'extracted_publish_time': None,
                    'raw_publish_time': None,
                    'extraction_method': None,
                    'status': 'extraction_failed',
                    'page_score': score,
                    'page_features': '; '.join(features)
                }
            
        except PlaywrightTimeout:
            return {'url': url, 'extracted_publish_time': None, 'raw_publish_time': None,
                   'extraction_method': None, 'status': 'timeout', 
                   'page_score': None, 'page_features': None}
        except Exception as e:
            return {'url': url, 'extracted_publish_time': None, 'raw_publish_time': None,
                   'extraction_method': None, 'status': f'browser_error: {str(e)[:50]}',
                   'page_score': None, 'page_features': None}
        finally:
            # 确保每次都关闭浏览器和 Playwright 实例
            if browser:
                try:
                    browser.close()
                except:
                    pass
            if playwright:
                try:
                    playwright.stop()
                except:
                    pass
        
    # dateModified不可信的推荐平台（这些平台的modified是系统刷新时间，不是内容修改时间）
    MODIFIED_UNTRUSTED_PLATFORMS = [
        'toutiao.com',       # 今日头条
        'toutiaocdn.com',    # 头条CDN
        'toutiaoimg.com',    # 头条图片域名
        'baijiahao.baidu.com',  # 百家号
        'mbd.baidu.com',     # 百度信息流
        'dy.163.com',        # 网易号
        'yidianzixun.com',   # 一点资讯
        'k.sina.cn',         # 新浪看点
        'k.sina.com.cn',     # 新浪看点
    ]
    
    def _is_modified_untrusted(self, url):
        """判断URL是否属于dateModified不可信的推荐平台"""
        from urllib.parse import urlparse
        netloc = urlparse(url).netloc.lower()
        for platform in self.MODIFIED_UNTRUSTED_PLATFORMS:
            if platform in netloc:
                return True
        return False
    
    def extract_from_meta(self, soup, url=''):
        """提取meta中的时间，推荐平台忽略dateModified"""
        meta_properties_modified = [
            'article:modified_time', 'og:updated_time', 'lastmod',
            'last-modified', 'dateModified', 'updatedate',
        ]
        meta_properties_published = [
            'article:published_time', 'article:published', 'og:published_time',
            'publishdate', 'date', 'pubdate', 'publication_date', 'datePublished'
        ]
        
        # 如果是不可信平台，直接跳过modified，只取published
        skip_modified = self._is_modified_untrusted(url)
        
        modified_time = None
        published_time = None
        
        if not skip_modified:
            for prop in meta_properties_modified:
                meta = (soup.find('meta', property=prop) or 
                       soup.find('meta', attrs={'name': prop}) or
                       soup.find('meta', itemprop=prop))
                if meta and meta.get('content'):
                    modified_time = meta['content']
                    break
        
        for prop in meta_properties_published:
            meta = (soup.find('meta', property=prop) or 
                   soup.find('meta', attrs={'name': prop}) or
                   soup.find('meta', itemprop=prop))
            if meta and meta.get('content'):
                published_time = meta['content']
                break
        
        # 优先级：modified > published（非黑名单平台）
        if modified_time:
            return modified_time, 'meta-modified'
        elif published_time:
            return published_time, 'meta'
        return None, None
    
    def extract_from_jsonld(self, soup, url=''):
        scripts = soup.find_all('script', type='application/ld+json')
        skip_modified = self._is_modified_untrusted(url)
        
        for script in scripts:
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    modified_val = None
                    published_val = None
                    
                    if not skip_modified:
                        for field in ['dateModified', 'lastModified', 'modifiedDate']:
                            if field in item:
                                modified_val = item[field]
                                break
                    for field in ['datePublished', 'publishDate', 'dateCreated', 'uploadDate']:
                        if field in item:
                            published_val = item[field]
                            break
                    
                    # 优先级：modified > published（非黑名单平台）
                    if modified_val:
                        return modified_val, 'json-ld-modified'
                    elif published_val:
                        return published_val, 'json-ld'
            except:
                continue
        return None, None
    
    def extract_from_script_vars(self, soup):
        """
        从JavaScript变量中提取时间
        适用于SPA应用（微博、知乎、小红书等）
        """
        scripts = soup.find_all('script')
        
        # 模式1: JSON对象中的时间字段（优先更新时间）
        json_patterns_modified = [
            r'"updateTime"\s*:\s*"([^"]+)"',
            r'"modifiedTime"\s*:\s*"([^"]+)"',
            r'"update_time"\s*:\s*"([^"]+)"',
            r'"modified_at"\s*:\s*"([^"]+)"',
            r'"lastModified"\s*:\s*"([^"]+)"',
        ]
        json_patterns_published = [
            r'"created_at"\s*:\s*"([^"]+)"',      # 微博格式
            r'"publishTime"\s*:\s*"([^"]+)"',     # 常见格式
            r'"createTime"\s*:\s*"([^"]+)"',
            r'"postDate"\s*:\s*"([^"]+)"',
            r'"publish_time"\s*:\s*"([^"]+)"',
            r'"date_published"\s*:\s*"([^"]+)"',
        ]
        
        # 模式2: 时间戳
        timestamp_patterns = [
            r'"created_at"\s*:\s*(\d{10,13})',
            r'"publishTime"\s*:\s*(\d{10,13})',
            r'"timestamp"\s*:\s*(\d{10,13})',
        ]
        
        for script in scripts:
            if not script.string:
                continue
            
            # 优先尝试更新时间的JSON模式
            for pattern in json_patterns_modified:
                match = re.search(pattern, script.string)
                if match:
                    time_str = match.group(1)
                    if any(char in time_str for char in [':', '-', '/', '年', '月']) or re.match(r'^\d{10,13}$', time_str):
                        return time_str, 'script-var-modified'
            
            # 其次尝试发布时间的JSON模式
            for pattern in json_patterns_published:
                match = re.search(pattern, script.string)
                if match:
                    time_str = match.group(1)
                    if any(char in time_str for char in [':', '-', '/', '年', '月']) or re.match(r'^\d{10,13}$', time_str):
                        return time_str, 'script-var'
            
            # 尝试时间戳模式
            for pattern in timestamp_patterns:
                match = re.search(pattern, script.string)
                if match:
                    return match.group(1), 'script-timestamp'
        
        return None, None
    
    def extract_from_time_tag(self, soup):
        time_tags = soup.find_all('time')
        for tag in time_tags:
            if tag.get('datetime'):
                return tag['datetime'], 'time-tag'
        return None, None
    
    def extract_from_class_id(self, soup):
        patterns = ['publish.*time', 'post.*time', 'date', 'time', 'create.*time', 'update.*time']
        
        for pattern in patterns:
            elem = soup.find(class_=re.compile(pattern, re.I))
            if elem:
                text = elem.get_text(strip=True)
                if self.looks_like_date(text):
                    return text, 'class'
        return None, None
    
    def extract_from_data_attributes(self, soup):
        """从HTML元素的data-*属性中提取日期"""
        # 常见的数据属性名
        data_attrs = [
            'data-time', 'data-publish-time', 'data-pubtime', 'data-date',
            'data-created', 'data-timestamp', 'data-publish', 'data-createtime'
        ]
        
        for attr in data_attrs:
            # 查找所有带此属性的元素
            elems = soup.find_all(attrs={attr: True})
            for elem in elems:
                value = elem.get(attr, '').strip()
                if value and (self.looks_like_date(value) or re.match(r'^\d{10,13}$', value)):
                    return value, 'data-attribute'
        
        return None, None
    
    def extract_from_regex(self, soup):
        """使用正则表达式从页面文本中提取日期"""
        text = soup.get_text()
        html_source = str(soup)  # 也搜索原始HTML（捕获data属性、JS变量等）
        
        # 页面头部文本（前500字符）—— 裸日期regex只在这里匹配，避免被正文日期干扰
        head_text = text[:500]
        
        # 正则模式（按优先级排序）
        # 分两类：
        # 1. 有关键词保护的（"发布时间/更新时间"等前缀）→ 全文匹配（text）
        # 2. 裸日期格式（无关键词）→ 只匹配页面头部（head_text），避免正文干扰
        patterns = [
            # JavaScript对象中的日期（有字段名保护，全文匹配）
            (r'(?:publishTime|pubTime|publish_time|createTime|create_time)["\']?\s*[:=]\s*["\'](\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)["\']?', 'regex-js-full', html_source),
            (r'(?:publishTime|pubTime|publish_time)["\']?\s*[:=]\s*["\'](\d{4}[-/]\d{1,2}[-/]\d{1,2})["\']?', 'regex-js-date', html_source),
            # 数据属性（有属性名保护）
            (r'data-time["\']?\s*[:=]\s*["\'](\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)["\']?', 'regex-data-attr', html_source),
            # 有关键词保护的 → 全文匹配
            (r'(?:更新时间|最后更新|修改时间|最后修改)[：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?\s+\d{1,2}:\d{2}(?::\d{2})?)', 'regex-full-modified', text),
            (r'(?:更新时间|最后更新|修改时间)[：:\s]*(\d{2}-\d{2}\s+\d{2}:\d{2})', 'regex-noYear-modified', text),
            (r'(?:发布时间|时间)[：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?\s+\d{1,2}:\d{2}(?::\d{2})?)', 'regex-full', text),
            (r'(?:发布时间|更新时间)[：:\s]*(\d{2}-\d{2}\s+\d{2}:\d{2})', 'regex-noYear', text),
            (r'(?:发布于|发表于|创建于)[：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?\s*\d{1,2}[：:]\d{2})', 'regex-prefix-full', text),
            (r'(?:发布于|发表于|创建于)[：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', 'regex-prefix', text),
            (r'更新于[：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', 'regex-prefix', text),
            # 裸日期格式（无关键词保护）→ 只匹配头部，避免正文干扰
            (r'(\d{4}年\d{1,2}月\d{1,2}日\s*\d{1,2}[：:]\d{2}(?:[：:]\d{2})?)', 'regex-cn-datetime', head_text),
            (r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', 'regex-standard', head_text),
            (r'(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})', 'regex-standard', head_text),
            (r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', 'regex-standard', head_text),
            (r'(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})', 'regex-standard', head_text),
            # JavaScript变量（有字段名保护）
            (r'createTime[：:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})', 'regex-js', html_source),
            (r'publishTime[：:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})', 'regex-js', html_source),
            # 纯日期（最后兜底，只匹配头部）
            (r'(\d{4}年\d{1,2}月\d{1,2}日)', 'regex-cn-date', head_text),
        ]
        
        for pattern, method_name, search_text in patterns:
            match = re.search(pattern, search_text, re.I)
            if match:
                return match.group(1), method_name
        
        return None, None
    
    
    def looks_like_date(self, text):
        """判断文本是否像日期"""
        if not text or len(text) > 50:
            return False
        
        # 排除常见非日期模式
        if re.match(r'^\d{2}:\d{2}', text):  # 排除时长格式 00:00
            return False
        if '/' in text and ':' in text and len(text) < 15:  # 排除 00:00/00:16 格式
            return False
        
        has_digits = any(c.isdigit() for c in text)
        has_separators = any(sep in text for sep in ['-', '/', ':', '年', '月', '日'])
        
        # 必须包含年份标识
        has_year = bool(re.search(r'(20\d{2}|19\d{2})', text))
        
        return has_digits and has_separators and has_year
    
    def is_future_time(self, dt_string):
        """判断时间是否是未来时间（比当前时间晚超过1天）"""
        if not dt_string:
            return False
        try:
            from datetime import timedelta
            # 尝试解析时间
            parsed = datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
            # 允许1天的误差（考虑时区）
            now = datetime.now()
            return parsed > (now + timedelta(days=1))
        except:
            return False
    
    def is_too_old(self, dt_string):
        """判断时间是否过于久远（超过20年前）"""
        if not dt_string:
            return False
        try:
            from datetime import timedelta
            parsed = datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            # 超过20年前判定为无效（可能是人物生日等）
            return parsed < (now - timedelta(days=365*20))
        except:
            return False
    
    def is_likely_access_time(self, dt_string):
        """
        判断是否可能是页面访问时间（而非真实发布时间）
        逻辑：发布时间不会精确到"此时此刻"
        只过滤与当前时间相差<60秒的时间
        """
        if not dt_string:
            return False
        try:
            parsed = datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            # 如果时间精确到秒，且与当前时间相差<60秒
            # 很可能是JavaScript生成的当前时间或页面加载时间
            diff = abs((now - parsed).total_seconds())
            return diff < 60  # 60秒，只过滤"此时此刻"
        except:
            return False
    
    def normalize_datetime(self, date_string):
        """将各种日期格式统一转换为 YYYY-MM-DD HH:MM:SS (CST/+0800)"""
        if not date_string:
            return None
        
        from datetime import timezone, timedelta
        CST = timezone(timedelta(hours=8))
        
        # 去除多余空白
        date_string = date_string.strip()
        
        # 快速过滤明显无效的值
        # 含非时间字符（中文、字母超过合理长度）→ 直接返回None
        if len(date_string) > 50:
            return None
        # 含占位符XX或全0日期
        if 'XX' in date_string or 'xx' in date_string:
            return None
        if date_string.startswith('0000'):
            return None
        
        # ASP.NET JSON日期格式: /Date(1759851179000+0800)/
        asp_match = re.match(r'/Date\((\d{10,13})([+-]\d{4})?\)/', date_string)
        if asp_match:
            ts = int(asp_match.group(1))
            if ts > 9999999999:  # 13位毫秒
                ts = ts / 1000
            try:
                dt = datetime.fromtimestamp(ts)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return None
        
        # RFC 2822格式: Sun, 09 Mar 2025 22:21:38 +0900
        if re.match(r'^[A-Z][a-z]{2},\s', date_string):
            from email.utils import parsedate_to_datetime
            try:
                dt = parsedate_to_datetime(date_string)
                dt = dt.astimezone(CST)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        # 预处理：2位年份补全为4位（如 26-05-22 → 2026-05-22）
        if re.match(r'^\d{2}-\d{2}-\d{2}', date_string):
            date_string = '20' + date_string
        
        # 预处理：点号分隔日期 2026.06.14 系列格式
        # 先处理带时间的（含中文星期的）：2026.06.14  星期日  12:00:59
        dot_time_match = re.match(r'^(\d{4})\.(\d{1,2})\.(\d{1,2})\s+(?:\S+\s+)?(\d{2}:\d{2}(?::\d{2})?)', date_string)
        if dot_time_match:
            date_string = '%s-%02d-%02d %s' % (dot_time_match.group(1), int(dot_time_match.group(2)), int(dot_time_match.group(3)), dot_time_match.group(4))
        else:
            # 纯日期（可能带星期）：2026.06.14 星期日 或 2026.6.14星期日
            dot_match = re.match(r'^(\d{4})\.(\d{1,2})\.(\d{1,2})', date_string)
            if dot_match:
                date_string = '%s-%02d-%02d' % (dot_match.group(1), int(dot_match.group(2)), int(dot_match.group(3)))
        
        # 预处理：倒序日期 DD-MM-YYYY（路虎等欧洲网站）
        dmy_match = re.match(r'^(\d{2})-(\d{2})-(\d{4})$', date_string)
        if dmy_match:
            d, m, y = dmy_match.groups()
            # 只有当第一组是合法日期（>12）才确认为DD-MM-YYYY
            if int(d) > 12:
                date_string = '%s-%s-%s' % (y, m, d)
        
        # 预处理：中文空格格式 "2026 年 6 月 14 日" → "2026年6月14日"
        date_string = re.sub(r'(\d)\s+年\s*(\d)', r'\1年\2', date_string)
        date_string = re.sub(r'(\d)\s+月\s*(\d)', r'\1月\2', date_string)
        date_string = re.sub(r'(\d)\s+日', r'\1日', date_string)
        
        # 预处理：带括号的中文时间 "（最近更新时间：2026年4月）" → 提取其中的时间
        bracket_match = re.search(r'(\d{4}年\d{1,2}月(?:\d{1,2}日)?)', date_string)
        if bracket_match and ('（' in date_string or '(' in date_string):
            date_string = bracket_match.group(1)
        
        # 新华网格式: 202605/2313:03:30 → 2026-05-23 13:03:30
        xinhua_match = re.match(r'^(\d{4})(\d{2})/(\d{2})(\d{2}:\d{2}:\d{2})$', date_string)
        if xinhua_match:
            y, m, d, t = xinhua_match.groups()
            date_string = '%s-%s-%s %s' % (y, m, d, t)
        
        # 检查是否是时间戳（10位或13位数字）
        if re.match(r'^\d{10}$', date_string):
            # 10位时间戳（秒）- 自动转为本地时间
            try:
                dt = datetime.fromtimestamp(int(date_string))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        elif re.match(r'^\d{13}$', date_string):
            # 13位时间戳（毫秒）
            try:
                dt = datetime.fromtimestamp(int(date_string) / 1000)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        # 尝试多种日期格式
        formats = [
            # 微博格式：Mon May 11 07:56:02 +0800 2026
            '%a %b %d %H:%M:%S %z %Y',
            # ISO 8601 格式
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%S',
            # 标准格式
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y/%m/%d %H:%M',
            '%Y-%m-%d',
            '%Y/%m/%d',
            # 中文格式
            '%Y年%m月%d日 %H:%M:%S',
            '%Y年%m月%d日 %H:%M',
            '%Y年%m月%d日',
        ]
        
        # 预处理：移除常见前缀
        date_string = re.sub(r'^(发布时间|更新时间|时间|当前页面更新时间)[：:]\s*', '', date_string)
        
        # 预处理：无年份的MM-DD HH:MM格式，补全当前年份
        no_year_match = re.match(r'^(\d{2})-(\d{2})\s+(\d{2}:\d{2})$', date_string)
        if no_year_match:
            year = datetime.now().year
            date_string = '%d-%s-%s %s:00' % (year, no_year_match.group(1), no_year_match.group(2), no_year_match.group(3))
        
        # 预处理：修复缺少分隔符的日期（如 2026-05-1213:00 -> 2026-05-12 13:00）
        # 预处理：将Z后缀替换为+00:00（strptime不识别Z）
        date_string = re.sub(r'(\d{2}:\d{2}:\d{2})Z$', r'\1+00:00', date_string)
        date_string = re.sub(r'(\d{2}:\d{2}:\d{2}\.\d+)Z$', r'\1+00:00', date_string)
        
        date_string = re.sub(r'(\d{4}-\d{2}-\d{2})(\d{2}:\d{2})', r'\1 \2', date_string)
        date_string = re.sub(r'(\d{4}/\d{2}/\d{2})(\d{2}:\d{2})', r'\1 \2', date_string)
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_string, fmt)
                # 如果有时区信息，转换为CST(+0800)
                if dt.tzinfo is not None:
                    dt = dt.astimezone(CST)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
        
        # 如果所有格式都失败，尝试正则提取（支持仅有年月的情况）
        match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?\s*(\d{1,2})?[：:]?(\d{1,2})?[：:]?(\d{1,2})?', date_string)
        if not match:
            # 只有年月（如"2026年4月"）
            match = re.search(r'(\d{4})[-/年](\d{1,2})月?$', date_string)
            if match:
                year, month, day = match.group(1), match.group(2), '1'
                hour, minute, second = '00', '00', '00'
                try:
                    dt = datetime(int(year), int(month), int(day))
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    return None
        if match:
            year, month, day = match.group(1), match.group(2), match.group(3)
            hour = match.group(4) or '00'
            minute = match.group(5) or '00'
            second = match.group(6) or '00'
            # 校验：月不能为0；日为0时说明是无效原始日期（如2026-04-00），过滤掉
            if int(month) == 0 or int(day) == 0:
                return None
            try:
                dt = datetime(int(year), int(month), int(day), 
                            int(hour), int(minute), int(second))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                return None
        
        # 无法解析，返回None（不再返回原始值，避免脏数据）
        return None
    
    def extract(self, url, timeout=15, use_browser=True):
        """
        提取发布时间，支持自动降级到浏览器渲染
        
        Args:
            url: 目标URL
            timeout: 超时时间（秒）
            use_browser: 静态提取失败时是否自动尝试浏览器渲染
        """
        try:
            response = self.session.get(url, timeout=timeout, allow_redirects=True, verify=False)
            
            if response.status_code != 200:
                # HTTP错误，直接尝试浏览器
                if use_browser:
                    return self.extract_with_browser(url)
                return {
                    'url': url,
                    'extracted_publish_time': None,
                    'raw_publish_time': None,
                    'extraction_method': None,
                    'status': f'http_{response.status_code}',
                    'page_score': None,
                    'page_features': None
                }
            
            response.encoding = response.apparent_encoding or 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            
            # P2优化：提取前先检查是否是明确的赛事页
            # 如果是，直接判定为无发布时间，不继续提取
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            path = parsed_url.path.lower()
            
            # 明确的赛事页模式
            is_match_page = False
            if ('dongqiudi.com' in parsed_url.netloc and '/matchdetail/' in path):
                is_match_page = True
            elif ('goal.com' in parsed_url.netloc and ('/match/' in path or '%e8%a9%a6%e5%90%88' in path)):
                is_match_page = True
            elif ('statarea.com' in parsed_url.netloc and '/compare/' in path):
                is_match_page = True
            elif ('espn' in parsed_url.netloc and ('/partido/' in path or '/gameid/' in path)):
                is_match_page = True
            elif ('7m.com' in parsed_url.netloc and 'analyse' in parsed_url.netloc):
                is_match_page = True
            
            # 明确的无发布时间页面：百科页、首页
            is_no_time_page = False
            if ('baike.com' in parsed_url.netloc and '/wiki/' in path):
                is_no_time_page = True
            elif path in ['/', '']:
                is_no_time_page = True
            
            # P3优化：查询工具页/列表页（有日期显示但不是"发布时间"）
            # 油价查询
            elif ('icauto.com.cn' in parsed_url.netloc and '/oil/price' in path):
                is_no_time_page = True
            # 快递查询
            elif ('kuaidi100.com' in parsed_url.netloc):
                is_no_time_page = True
            # 股吧列表页
            elif ('eastmoney.com' in parsed_url.netloc and '/list/' in path):
                is_no_time_page = True
            # 火车票/机票查询
            elif ('ctrip.com' in parsed_url.netloc and '/trainbooking/' in path.lower()):
                is_no_time_page = True
            # 淘宝产品页
            elif ('taobao.com' in parsed_url.netloc and ('/product' in path or '/chanpin/' in path)):
                is_no_time_page = True
            # UPS快递追踪
            elif ('ups.com' in parsed_url.netloc and '/track' in path):
                is_no_time_page = True
            
            if is_match_page or is_no_time_page:
                return {
                    'url': url,
                    'extracted_publish_time': None,
                    'raw_publish_time': None,
                    'extraction_method': None,
                    'status': 'no_publish_time',
                    'page_score': -30,
                    'page_features': '赛事比分页（无发布时间）'
                }
            
            methods = [
                lambda s: self.extract_from_meta(s, url),
                lambda s: self.extract_from_jsonld(s, url),
                self.extract_from_script_vars,  # 新增：Script变量提取（SPA应用）
                self.extract_from_time_tag,
                self.extract_from_data_attributes,
                self.extract_from_class_id,
                self.extract_from_regex
            ]
            
            # 如果早期方法只提取到日级精度，先暂存，继续找更精确的
            day_level_result = None
            day_level_method = None
            
            for method in methods:
                result, method_name = method(soup)
                if result:
                    normalized_time = self.normalize_datetime(result)
                    # normalize失败 → 继续尝试下一个方法
                    if not normalized_time:
                        continue
                    # 多重时间校验
                    # 校验1: 未来时间（可能是赛事时间）
                    if self.is_future_time(normalized_time):
                        continue
                    # 校验2: 过于久远（可能是人物生日）
                    if self.is_too_old(normalized_time):
                        continue
                    # 校验3: 页面访问时间（可能是JS生成的当前时间）
                    if self.is_likely_access_time(normalized_time):
                        continue
                    
                    # 检查精度：如果只到日（00:00:00结尾），暂存并继续找
                    if normalized_time.endswith('00:00:00') and day_level_result is None:
                        day_level_result = normalized_time
                        day_level_method = method_name
                        continue  # 不立即返回，继续往下找更精确的
                    
                    # 如果有暂存的日级结果，验证当前更精确的结果日期是否匹配
                    if day_level_result and normalized_time[:10] == day_level_result[:10]:
                            # 同一天，用更精确的
                            return {
                                'url': url,
                                'extracted_publish_time': normalized_time,
                                'raw_publish_time': result,
                                'extraction_method': method_name,
                                'status': 'success',
                                'page_score': None,
                                'page_features': None
                            }
                    
                    return {
                        'url': url,
                        'extracted_publish_time': normalized_time,
                        'raw_publish_time': result,
                        'extraction_method': method_name,
                        'status': 'success',
                        'page_score': None,
                        'page_features': None
                    }
            
            # 所有方法都没找到更精确的，但有日级结果 → 返回日级
            if day_level_result:
                return {
                    'url': url,
                    'extracted_publish_time': day_level_result,
                    'raw_publish_time': day_level_result,
                    'extraction_method': day_level_method,
                    'status': 'success',
                    'page_score': None,
                    'page_features': None
                }
            
            # 静态提取失败，自动尝试浏览器渲染
            if use_browser:
                return self.extract_with_browser(url)
            
            # 不使用浏览器时，尝试LLM兜底
            score, features = self.analyze_page_features(soup, url)
            
            llm_time, llm_method = self.extract_with_llm(soup, url)
            if llm_time:
                if not self.is_future_time(llm_time) and not self.is_too_old(llm_time) and not self.is_likely_access_time(llm_time):
                    return {
                        'url': url,
                        'extracted_publish_time': llm_time,
                        'raw_publish_time': llm_time,
                        'extraction_method': llm_method,
                        'status': 'success',
                        'page_score': score,
                        'page_features': '; '.join(features)
                    }
            
            # LLM也失败
            if score < 30:
                return {
                    'url': url,
                    'extracted_publish_time': None,
                    'raw_publish_time': None,
                    'extraction_method': None,
                    'status': 'no_publish_time',
                    'page_score': score,
                    'page_features': '; '.join(features)
                }
            else:
                return {
                    'url': url,
                    'extracted_publish_time': None,
                    'raw_publish_time': None,
                    'extraction_method': None,
                    'status': 'extraction_failed',
                    'page_score': score,
                    'page_features': '; '.join(features)
                }
            
        except requests.Timeout:
            # 超时也尝试浏览器
            if use_browser:
                return self.extract_with_browser(url)
            return {'url': url, 'extracted_publish_time': None, 'raw_publish_time': None, 
                   'extraction_method': None, 'status': 'timeout',
                   'page_score': None, 'page_features': None}
        except Exception as e:
            # 其他错误也尝试浏览器
            if use_browser:
                return self.extract_with_browser(url)
            return {'url': url, 'extracted_publish_time': None, 'raw_publish_time': None,
                   'extraction_method': None, 'status': f'error: {str(e)[:50]}',
                   'page_score': None, 'page_features': None}

extractor = PublishTimeExtractor()

@app.route('/')
def index():
    response = app.make_response(render_template_string(HTML_TEMPLATE))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response

@app.route('/extract', methods=['POST'])
def extract():
    data = request.json
    url = data.get('url')
    result = extractor.extract(url)
    
    status = result.get('status', '')
    extracted_time = result.get('extracted_publish_time', '')
    
    # precision字段：
    # - 提取成功时标记精度（秒/分/时/日）
    # - 判定为无发布时间时标记"无发布时间"
    # - 其他失败（timeout等）置空
    
    if status == 'success' and extracted_time:
        try:
            parts = extracted_time.split(' ')
            time_part = parts[1] if len(parts) > 1 else '00:00:00'
            h, m, s = time_part.split(':')
            
            if s != '00':
                result['precision'] = '秒'
            elif m != '00':
                result['precision'] = '分'
            elif h != '00':
                result['precision'] = '时'
            else:
                result['precision'] = '日'
        except:
            result['precision'] = '日'
    elif status == 'no_publish_time':
        result['precision'] = '无发布时间'
    else:
        # 其他失败（timeout/browser_error/extraction_failed等）也标记到precision
        result['precision'] = '提取失败'
    
    # 移除status_type字段（已合并到precision）
    result.pop('status_type', None)
    
    return jsonify(result)

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    results = data.get('results', [])
    
    df = pd.DataFrame(results)
    
    # 指定字段顺序
    desired_cols = ['url', 'extracted_publish_time', 'precision', 'status', 
                    'extraction_method', 'page_features', 'page_score', 'raw_publish_time']
    # 只保留存在的列，按顺序排
    cols = [c for c in desired_cols if c in df.columns]
    # 加上其他未列出的列
    remaining = [c for c in df.columns if c not in cols]
    df = df[cols + remaining]
    
    output = io.BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'extracted_results_{int(time.time())}.csv'
    )

if __name__ == '__main__':
    print('='*60)
    print('URL发布时间提取工具 - Web服务版')
    print('='*60)
    print('🚀 启动成功！')
    print('📝 请在浏览器打开: http://127.0.0.1:5001')
    print('⚠️  按 Ctrl+C 停止服务')
    print('='*60)
    app.run(debug=True, port=5001, use_reloader=False)
