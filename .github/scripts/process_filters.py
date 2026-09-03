#!/usr/bin/env python3
import requests
import re
from datetime import datetime
from pathlib import Path

def download_url(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return ""

def is_comment_line(line):
    """判断是否为注释行（# 或 ! 开头）"""
    line = line.strip()
    return line.startswith('#') or line.startswith('!')

def normalize_rule(line):
    """标准化规则行（去除多余空格）用于去重比较"""
    return re.sub(r'\s+', ' ', line.strip())

def read_existing_file():
    """读取现有文件，提取自定义规则区块的所有行（含注释和空行）"""
    existing_file = "AdGHome-PCDN.txt"
    try:
        with open(existing_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []

    custom_lines = []
    in_custom = False
    custom_markers = ["# === 自定义规则 ===", "### 自定义规则 ###"]
    end_markers = ["### 合并规则 ###", "# === 合并规则 ==="]

    for line in lines:
        stripped = line.strip()
        if not in_custom:
            if stripped in custom_markers:
                in_custom = True
            continue
        else:
            if stripped in end_markers:
                break
            custom_lines.append(line.rstrip('\r\n'))

    # 去掉末尾多余空行
    while custom_lines and not custom_lines[-1].strip():
        custom_lines.pop()
    return custom_lines

def process_filter_lists():
    urls = [
        "https://raw.githubusercontent.com/Womsxd/MyAdBlockRules/refs/heads/master/p2pcdnblock.txt",
        "https://raw.githubusercontent.com/4fuu/AdGuard-Home-PCDN/refs/heads/main/ban.txt",
        "https://raw.githubusercontent.com/daboq11/ban-pcdn/refs/heads/main/Ban-pcdn.txt",
        "https://raw.githubusercontent.com/743859910/OpenHosts/refs/heads/master/Block_PCDN_Domain.txt",
        "https://cdn.jsdelivr.net/gh/susetao/PCDNFilter-CHN-@main/PCDNFilter.txt",
        "https://thhbdd.github.io/Block-pcdn-domains/ban.txt"
    ]

    # 读取现有的自定义规则
    custom_lines = read_existing_file()

    # 最终输出行（不含文件头）
    output_lines = []

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
            output_lines.append(line)

    # ---------- 自定义规则 ----------
    if custom_lines:
        output_lines.append("### 自定义规则 ###")
        output_lines.extend(custom_lines)
        output_lines.append("")   # 空行分隔

    # ---------- 合并规则（从网络下载） ----------
    # 存储白名单规则（集中前置）
    whitelist_rules = []
    # 存储其他所有行（注释 + 非白名单规则），按来源顺序
    other_lines = []

    # 全局去重集合
    seen_whitelist = set()
    seen_other_rules = set()
    seen_comments = set()

    for url in urls:
        print(f"Processing URL: {url}")
        content = download_url(url)
        if not content:
            continue

        for line in content.split('\n'):
            original = line.rstrip('\r\n')
            if not original.strip():
                continue

            # 注释行
            if is_comment_line(original):
                key = original.strip()
                if key not in seen_comments:
                    seen_comments.add(key)
                    other_lines.append(original)   # 注释保留在原始位置
                continue

            # 规则行
            norm = normalize_rule(original)
            if original.startswith('@@'):   # 白名单规则
                if norm not in seen_whitelist:
                    seen_whitelist.add(norm)
                    whitelist_rules.append(original)
            else:
                if norm not in seen_other_rules:
                    seen_other_rules.add(norm)
                    other_lines.append(original)   # 普通规则保留在原始位置

    # 构建合并区块
    if whitelist_rules or other_lines:
        output_lines.append("### 合并规则 ###")

        # 先输出所有白名单规则（前置）
        if whitelist_rules:
            output_lines.extend(whitelist_rules)
            if other_lines:
                output_lines.append("")   # 与后续内容空行分隔

        # 再输出其他所有行（注释和普通规则），保持原始顺序
        if other_lines:
            output_lines.extend(other_lines)

        output_lines.append("")   # 末尾空行

    # ---------- 写入文件 ----------
    output_file = "AdGHome-PCDN.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        prev_empty = False
        for line in output_lines:
            cur_empty = not line.strip()
            if cur_empty:
                if not prev_empty:
                    f.write('\n')
                prev_empty = True
            else:
                f.write(line + '\n')
                prev_empty = False

    print(f"Successfully processed and saved to {output_file}")
    total_rules = len([l for l in output_lines if l.strip() and not l.startswith('#') and not l.startswith('!') and not l.startswith('###')])
    print(f"Total unique rules: {total_rules}")

if __name__ == "__main__":
    process_filter_lists()
