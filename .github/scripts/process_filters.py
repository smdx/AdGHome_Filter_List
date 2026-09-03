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
    """检查是否是注释行（# 或 ! 开头）"""
    line = line.strip()
    return line.startswith('#') or line.startswith('!')

def normalize_rule(line):
    """标准化规则行以便去重比较（去除多余空格，保留内容）"""
    line = line.strip()
    # 对规则行，去掉多余空格，但保留原内容（不改变正则等）
    return re.sub(r'\s+', ' ', line)

def read_existing_file():
    """
    读取现有的 AdGHome-PCDN.txt 文件，提取自定义规则部分的内容。
    支持旧标记 "# === 自定义规则 ===" 和新标记 "### 自定义规则 ###"。
    返回自定义部分的所有行（含注释和空行），不做任何去重。
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
    
    # 去除末尾多余空行
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

    all_lines = []          # 最终输出的所有行
    seen_rules = set()      # 用于规则去重
    comment_seen = set()    # 用于注释去重（相同注释只保留一条）
    comment_lines = []      # 收集所有去重后的注释行（用于合并区块）
    raw_merged_rules = []   # 暂存所有规则行（去重后）

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

    # ---------- 自定义规则 ----------
    if custom_lines:
        all_lines.append("### 自定义规则 ###")
        for line in custom_lines:
            all_lines.append(line)
        all_lines.append("")  # 分隔空行

    # ---------- 从网络下载并收集合并内容 ----------
    for url in urls:
        print(f"Processing URL: {url}")
        content = download_url(url)
        if not content:
            continue
        for line in content.split('\n'):
            original_line = line.rstrip('\r\n')
            if not original_line.strip():
                continue
            # 判断是否为注释行
            if is_comment_line(original_line):
                # 注释去重：用 strip 后的内容作为 key
                key = original_line.strip()
                if key not in comment_seen:
                    comment_seen.add(key)
                    comment_lines.append(original_line)  # 保留原始行（含空格等）
            else:
                # 规则行去重
                norm = normalize_rule(original_line)
                if norm not in seen_rules:
                    seen_rules.add(norm)
                    raw_merged_rules.append(original_line)

    # ---------- 合并规则区块 ----------
    if raw_merged_rules or comment_lines:
        all_lines.append("### 合并规则 ###")
        # 先输出所有注释行（去重后）
        for line in comment_lines:
            all_lines.append(line)
        # 如有注释和规则，加空行分隔
        if comment_lines and raw_merged_rules:
            all_lines.append("")
        # 规则排序：白名单（@@开头）优先
        allowed = [r for r in raw_merged_rules if r.startswith('@@')]
        blocked = [r for r in raw_merged_rules if not r.startswith('@@')]
        for rule in allowed + blocked:
            all_lines.append(rule)
        all_lines.append("")  # 结尾空行

    # ---------- 写入文件 ----------
    output_file = "AdGHome-PCDN.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        # 合并连续空行，保持整洁
        prev_empty = False
        for line in all_lines:
            cur_empty = not line.strip()
            if cur_empty:
                if not prev_empty:
                    f.write('\n')
                prev_empty = True
            else:
                f.write(line + '\n')
                prev_empty = False

    print(f"Successfully processed and saved to {output_file}")
    total_rules = len([l for l in all_lines if l.strip() and not l.startswith('#') and not l.startswith('!') and not l.startswith('###')])
    print(f"Total unique rules: {total_rules}")

if __name__ == "__main__":
    process_filter_lists()
