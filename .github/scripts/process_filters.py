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
    """检查是否是注释行（AdGuard 规则中的 # 或 ! 开头）"""
    line = line.strip()
    return line.startswith('#') or line.startswith('!') or not line

def normalize_line(line):
    """标准化行以便去重比较（去除多余空格）"""
    line = line.strip()
    if is_comment_line(line):
        return line
    return re.sub(r'\s+', ' ', line)

def read_existing_file():
    """
    读取现有的 AdGHome-PCDN.txt 文件，提取自定义规则部分的内容。
    支持旧标记 "# === 自定义规则 ===" 和新标记 "### 自定义规则 ###"。
    返回自定义部分的所有行（不含标题行，含注释和空行）。
    """
    existing_file = "AdGHome-PCDN.txt"
    try:
        with open(existing_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []

    custom_lines = []
    in_custom = False
    custom_markers = ["# === 自定义规则 ===", "### 自定义规则 ###"]
    end_markers = ["### 合并规则 ###", "# === 合并规则 ==="]  # 可能存在的结束标记

    for line in lines:
        stripped = line.strip()
        if not in_custom:
            if stripped in custom_markers:
                in_custom = True
            continue
        else:
            # 遇到结束标记则停止收集
            if stripped in end_markers:
                break
            # 保留原始行（包括空行和注释）
            custom_lines.append(line.rstrip('\r\n'))
    
    # 去除末尾多余的空行
    while custom_lines and not custom_lines[-1].strip():
        custom_lines.pop()
    return custom_lines

def process_filter_lists():
    """主处理函数"""
    urls = [
        "https://raw.githubusercontent.com/Womsxd/MyAdBlockRules/refs/heads/master/p2pcdnblock.txt",
        "https://raw.githubusercontent.com/4fuu/AdGuard-Home-PCDN/refs/heads/main/ban.txt",
        "https://raw.githubusercontent.com/daboq11/ban-pcdn/refs/heads/main/Ban-pcdn.txt",
        "https://raw.githubusercontent.com/743859910/OpenHosts/refs/heads/master/Block_PCDN_Domain.txt",
        "https://cdn.jsdelivr.net/gh/susetao/PCDNFilter-CHN-@main/PCDNFilter.txt",
        "https://thhbdd.github.io/Block-pcdn-domains/ban.txt"
    ]

    # 读取现有自定义内容
    custom_lines = read_existing_file()

    all_lines = []      # 最终输出的所有行
    seen = set()        # 用于全局去重（只对规则行，不影响注释和标题）

    # ---------- 文件头 ----------
    header = f"""# PCDN Filter List
# 合并自多个来源
# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 来源:
# - https://github.com/Womsxd/MyAdBlockRules
# - https://github.com/4fuu/AdGuard-Home-PCDN
# - https://github.com/daboq11/ban-pcdn
# - https://github.com/743859910/OpenHosts
# - https://github.com/susetao/PCDNFilter-CHN-
# - https://github.com/thhbdd/Block-pcdn-domains
#
# 注意：手动添加的规则请放在文件的"自定义规则"部分
#
"""
    for line in header.split('\n'):
        if line.strip():
            all_lines.append(line)
            seen.add(normalize_line(line))  # 头部注释也加入 seen 以防意外重复（实际不会）

    # ---------- 自定义规则 ----------
    if custom_lines:
        all_lines.append("### 自定义规则 ###")
        seen.add("### 自定义规则 ###")
        for line in custom_lines:
            all_lines.append(line)
            # 如果行是规则（非注释、非空），则加入 seen 以便合并时去重
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('!'):
                seen.add(normalize_line(line))
        all_lines.append("")  # 与后续区块分隔

    # ---------- 合并规则（从网络下载） ----------
    raw_merged = []  # 暂存所有合并规则（未排序）
    for url in urls:
        print(f"Processing URL: {url}")
        content = download_url(url)
        if not content:
            continue
        for line in content.split('\n'):
            original_line = line.rstrip('\r\n')
            norm = normalize_line(original_line)
            # 跳过空行或注释行（这些不需要去重，也不加入 seen）
            if not norm or is_comment_line(original_line):
                continue
            # 如果规则尚未出现过（包括自定义部分已有），则加入暂存列表并标记已见
            if norm not in seen:
                raw_merged.append(original_line)
                seen.add(norm)

    # 对合并规则排序：@@ 白名单规则放在最前面
    allowed = []
    blocked = []
    for rule in raw_merged:
        if rule.startswith('@@'):
            allowed.append(rule)
        else:
            blocked.append(rule)
    merged_final = allowed + blocked

    if merged_final:
        all_lines.append("### 合并规则 ###")
        seen.add("### 合并规则 ###")
        for rule in merged_final:
            all_lines.append(rule)
        all_lines.append("")  # 结尾空行

    # ---------- 写入文件 ----------
    output_file = "AdGHome-PCDN.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        # 合并连续空行，保持文件整洁
        previous_empty = False
        for line in all_lines:
            current_empty = not line.strip()
            if current_empty:
                if not previous_empty:
                    f.write('\n')
                previous_empty = True
            else:
                f.write(line + '\n')
                previous_empty = False

    print(f"Successfully processed and saved to {output_file}")
    total_rules = len([l for l in all_lines if l.strip() and not l.startswith('#') and not l.startswith('!') and not l.startswith('###')])
    print(f"Total unique rules: {total_rules}")

if __name__ == "__main__":
    process_filter_lists()
