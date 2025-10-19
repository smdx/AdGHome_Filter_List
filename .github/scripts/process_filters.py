#!/usr/bin/env python3
import requests
import re
from datetime import datetime
from pathlib import Path

def download_url(url):
    """下载URL内容"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return ""

def is_comment_line(line):
    """检查是否是注释行"""
    line = line.strip()
    return line.startswith('#') or line.startswith('!') or not line

def normalize_line(line):
    """标准化行以便去重比较"""
    line = line.strip()
    if is_comment_line(line):
        return line
    # 对于规则行，去除多余空格进行标准化
    return re.sub(r'\s+', ' ', line)

def read_existing_file():
    """读取现有的AdGHome-PCDN.txt文件内容"""
    existing_file = "AdGHome-PCDN.txt"
    existing_lines = []
    
    try:
        if Path(existing_file).exists():
            with open(existing_file, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
            print(f"Read {len(existing_lines)} lines from existing file")
            
            # 提取原有的自定义内容（非自动生成的头部分）
            custom_lines = []
            in_header = True
            for line in existing_lines:
                line = line.rstrip('\r\n')
                # 检测是否还在文件头部分（包含更新时间信息的部分）
                if line.startswith('# 更新时间:') or line.startswith('# 合并自多个来源'):
                    in_header = True
                elif line.startswith('#') and in_header:
                    continue  # 跳过原有的头注释
                elif line.strip() == "# === 自定义规则 ===":
                    continue  # 跳过自定义规则标记行
                else:
                    in_header = False
                    if line.strip():  # 只保留非空行
                        custom_lines.append(line)
            
            return custom_lines
    except Exception as e:
        print(f"Error reading existing file: {e}")
    
    return []

def process_filter_lists():
    """处理过滤器列表"""
    urls = [
        "https://raw.githubusercontent.com/Womsxd/MyAdBlockRules/refs/heads/master/p2pcdnblock.txt",
        "https://raw.githubusercontent.com/4fuu/AdGuard-Home-PCDN/refs/heads/main/ban.txt",
        "https://raw.githubusercontent.com/743859910/OpenHosts/refs/heads/master/Block_PCDN_Domain.txt",
        "https://cdn.jsdelivr.net/gh/susetao/PCDNFilter-CHN-@main/PCDNFilter.txt",
        "https://thhbdd.github.io/Block-pcdn-domains/ban.txt"
    ]
    
    # 读取原有的自定义内容
    existing_custom_lines = read_existing_file()
    
    all_lines = []
    seen_lines = set()
    
    # 添加文件头注释
    header = f"""# PCDN Filter List
# 合并自多个来源
# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 来源:
# - https://github.com/Womsxd/MyAdBlockRules
# - https://github.com/4fuu/AdGuard-Home-PCDN
# - https://github.com/743859910/OpenHosts
# - https://github.com/susetao/PCDNFilter-CHN-
# - https://github.com/thhbdd/Block-pcdn-domains
#
# 注意：手动添加的规则请放在文件末尾的"自定义规则"部分
#
"""
    all_lines.extend(header.split('\n'))
    for line in header.split('\n'):
        seen_lines.add(normalize_line(line))
    
    # 首先添加原有的自定义内容（确保它们在最前面）
    print("Adding existing custom rules...")
    custom_section_added = False
    
    for line in existing_custom_lines:
        normalized = normalize_line(line)
        if normalized and normalized not in seen_lines:
            if not custom_section_added:
                all_lines.append("# === 自定义规则 ===")
                custom_section_added = True
                seen_lines.add("# === 自定义规则 ===")  # 将标记行也加入已见集合
            all_lines.append(line)
            seen_lines.add(normalized)
    
    if custom_section_added:
        all_lines.append("")  # 添加空行分隔
    
    # 处理每个URL
    for i, url in enumerate(urls):
        print(f"Processing URL {i+1}: {url}")
        content = download_url(url)
        if not content:
            continue

        # 记录这个URL是否有有效内容
        url_has_content = False
        
        # 处理内容行
        for line in content.split('\n'):
            original_line = line.rstrip('\r\n')
            normalized = normalize_line(original_line)
            
            # 空行处理
            if not normalized:
                continue
                
            # 检查是否已存在
            if normalized not in seen_lines:
                all_lines.append(original_line)
                seen_lines.add(normalized)
                url_has_content = True
        
        # 如果这个URL有有效内容，并且在后面还有URL，则添加一个空行
        if url_has_content and i < len(urls) - 1:
            all_lines.append("")
    
    # 写入文件
    output_file = "AdGHome-PCDN.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        # 重新组织内容，确保连续空行被合并
        previous_line_empty = False
        for line in all_lines:
            current_line_empty = not line.strip()
            
            if current_line_empty:
                if not previous_line_empty:
                    f.write('\n')
                previous_line_empty = True
            else:
                f.write(line + '\n')
                previous_line_empty = False
    
    print(f"Successfully processed and saved to {output_file}")
    total_rules = len([l for l in all_lines if l.strip() and not l.startswith('#')])
    print(f"Total unique rules: {total_rules}")

if __name__ == "__main__":
    process_filter_lists()