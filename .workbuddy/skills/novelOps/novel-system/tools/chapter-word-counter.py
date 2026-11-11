#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节字数统计工具

统计章节文件的中文字符数（排除标点、空白），并判断是否达到番茄小说平台标准。
质量标准：单章 1200-1500 字（中文字符，不含标点和空白）。

用法示例:
    # 单章统计
    python chapter-word-counter.py chapters/ch001.md

    # 批量统计多个文件
    python chapter-word-counter.py chapters/ch001.md chapters/ch002.md chapters/ch003.md

    # 通配符批量统计（shell 会自动展开）
    python chapter-word-counter.py "chapters/ch*.md"

    # JSON 输出（便于其他工具调用）
    python chapter-word-counter.py chapters/ch001.md --json

    # 自定义字数范围
    python chapter-word-counter.py chapters/ch001.md --min 1000 --max 2000

依赖:
    无第三方依赖，仅使用 Python 标准库。
"""

import sys
import os
import re
import glob
import json
import argparse
from datetime import datetime


# ============ Constants ============

# Default word count thresholds (Fanqie platform standard)
DEFAULT_MIN_WORDS = 1200
DEFAULT_MAX_WORDS = 1500

# Chinese character Unicode ranges:
#   CJK Unified Ideographs:          U+4E00 - U+9FFF
#   CJK Unified Ideographs Ext A:    U+3400 - U+4DBF
#   CJK Compatibility Ideographs:    U+F900 - U+FAFF
#   CJK Unified Ideographs Ext B+:   U+20000 - U+2A6DF (and beyond)
CJK_PATTERN = re.compile(
    r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff'
    r'\U00020000-\U0002a6df\U0002a700-\U0002b73f'
    r'\U0002b740-\U0002b81f\U0002b820-\U0002ceaf]'
)


# ============ Core Functions ============

def count_chinese_chars(text):
    """统计文本中的中文字符数（排除标点、空白、英文字母、数字等非中文字符）。

    Args:
        text: 待统计的文本字符串

    Returns:
        int: 中文字符数量
    """
    return len(CJK_PATTERN.findall(text))


def count_all_chars(text):
    """统计文本中的所有可见字符数（排除空白字符）。

    Args:
        text: 待统计的文本字符串

    Returns:
        int: 可见字符数量
    """
    # Remove all whitespace characters
    visible = re.sub(r'\s+', '', text)
    return len(visible)


def count_total_chars(text):
    """统计文本总字符数（包含所有字符）。

    Args:
        text: 待统计的文本字符串

    Returns:
        int: 总字符数量
    """
    return len(text)


def analyze_file(filepath):
    """分析单个章节文件，返回字数统计结果。

    Args:
        filepath: 章节文件路径

    Returns:
        dict: 包含文件路径、中文字数、总字符数、是否达标等信息。
              如果文件读取失败，包含 error 字段。
    """
    result = {
        "file": filepath,
        "chinese_chars": 0,
        "total_chars": 0,
        "visible_chars": 0,
        "line_count": 0,
        "status": "unknown",
        "meets_standard": False,
    }

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        result["error"] = f"文件不存在: {filepath}"
        result["status"] = "error"
        return result
    except PermissionError:
        result["error"] = f"无读取权限: {filepath}"
        result["status"] = "error"
        return result
    except Exception as e:
        result["error"] = f"读取失败: {filepath} ({e})"
        result["status"] = "error"
        return result

    result["chinese_chars"] = count_chinese_chars(content)
    result["total_chars"] = count_total_chars(content)
    result["visible_chars"] = count_all_chars(content)
    result["line_count"] = content.count('\n') + 1 if content else 0

    return result


def check_standard(char_count, min_words=DEFAULT_MIN_WORDS, max_words=DEFAULT_MAX_WORDS):
    """检查字数是否达到平台标准。

    Args:
        char_count: 中文字符数
        min_words: 最低字数标准
        max_words: 最高字数标准

    Returns:
        tuple: (是否达标 bool, 状态描述 str)
    """
    if char_count < min_words:
        diff = min_words - char_count
        return False, f"不足 (差 {diff} 字)"
    elif char_count > max_words:
        diff = char_count - max_words
        return False, f"超标 (多 {diff} 字)"
    else:
        return True, "达标"


def format_result(result, min_words=DEFAULT_MIN_WORDS, max_words=DEFAULT_MAX_WORDS):
    """格式化单个文件的分析结果为可读字符串。

    Args:
        result: analyze_file 返回的结果字典
        min_words: 最低字数标准
        max_words: 最高字数标准

    Returns:
        str: 格式化后的结果字符串
    """
    filepath = result["file"]
    filename = os.path.basename(filepath)

    if result.get("error"):
        return f"  [ERROR] {filename}: {result['error']}"

    cn_chars = result["chinese_chars"]
    meets, status = check_standard(cn_chars, min_words, max_words)

    mark = "[OK]  " if meets else "[FAIL]"
    bar = _render_bar(cn_chars, min_words, max_words)

    lines = [
        f"  {mark} {filename}",
        f"         中文字数: {cn_chars:>6d}  {bar}  {status}",
        f"         可见字符: {result['visible_chars']:>6d}  总字符: {result['total_chars']:>6d}  行数: {result['line_count']}",
    ]
    return "\n".join(lines)


def _render_bar(count, min_val, max_val, bar_width=30):
    """Render a visual progress bar showing where the count falls relative to the standard range.

    Args:
        count: current value
        min_val: minimum threshold
        max_val: maximum threshold
        bar_width: width of the bar in characters

    Returns:
        str: visual bar string
    """
    # Scale: 0 to max_val * 1.5 maps to bar_width
    scale_max = int(max_val * 1.5)
    pos = min(int(count / scale_max * bar_width), bar_width)
    min_pos = int(min_val / scale_max * bar_width)
    max_pos = int(max_val / scale_max * bar_width)

    bar = []
    for i in range(bar_width):
        if i == pos:
            bar.append("|")
        elif i < min_pos:
            bar.append("-")
        elif i < max_pos:
            bar.append("=")
        else:
            bar.append("-")

    # Ensure the position marker is visible
    if pos >= bar_width:
        bar[-1] = "|"

    return f"[{''.join(bar)}]"


# ============ File Expansion ============

def expand_files(patterns):
    """Expand file patterns (including glob wildcards) into a list of actual file paths.

    On Windows, the shell does not expand glob patterns automatically, so we use
    Python's glob module to handle patterns like "chapters/ch*.md".

    Args:
        patterns: list of file path patterns or direct paths

    Returns:
        list: sorted list of unique file paths
    """
    files = []
    seen = set()

    for pattern in patterns:
        # Try glob expansion first
        matched = glob.glob(pattern)

        if matched:
            # Pattern matched actual files via glob
            for f in matched:
                abs_f = os.path.abspath(f)
                if abs_f not in seen:
                    files.append(f)
                    seen.add(abs_f)
        elif os.path.isfile(pattern):
            # Direct file path (not a glob pattern)
            abs_f = os.path.abspath(pattern)
            if abs_f not in seen:
                files.append(pattern)
                seen.add(abs_f)
        else:
            # Neither glob match nor direct file — record as missing
            files.append(pattern)

    return files


# ============ Batch Summary ============

def generate_summary(results, min_words=DEFAULT_MIN_WORDS, max_words=DEFAULT_MAX_WORDS):
    """Generate a summary of batch results.

    Args:
        results: list of analyze_file result dicts
        min_words: minimum word threshold
        max_words: maximum word threshold

    Returns:
        str: formatted summary string
    """
    total = len(results)
    errors = [r for r in results if r.get("error")]
    valid = [r for r in results if not r.get("error")]

    if not valid:
        return f"  统计: {total} 个文件, {len(errors)} 个错误, 无有效结果"

    passed = 0
    under = 0
    over = 0
    total_chars = 0

    for r in valid:
        cn = r["chinese_chars"]
        total_chars += cn
        if cn < min_words:
            under += 1
        elif cn > max_words:
            over += 1
        else:
            passed += 1

    avg = total_chars // len(valid) if valid else 0

    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("批量统计汇总")
    lines.append("=" * 60)
    lines.append(f"  文件总数:   {total}")
    lines.append(f"  有效文件:   {len(valid)}")
    lines.append(f"  错误文件:   {len(errors)}")
    lines.append(f"  达标:       {passed}")
    lines.append(f"  字数不足:   {under}")
    lines.append(f"  字数超标:   {over}")
    lines.append(f"  总中文字数: {total_chars}")
    lines.append(f"  平均字数:   {avg}")
    lines.append(f"  标准:       {min_words}-{max_words} 字")

    # List files that need attention
    problem_files = []
    for r in valid:
        cn = r["chinese_chars"]
        if cn < min_words:
            problem_files.append((r["file"], cn, f"差 {min_words - cn} 字"))
        elif cn > max_words:
            problem_files.append((r["file"], cn, f"多 {cn - max_words} 字"))

    if problem_files:
        lines.append("")
        lines.append("  需处理的文件:")
        for filepath, cn, note in problem_files:
            filename = os.path.basename(filepath)
            lines.append(f"    - {filename}: {cn} 字 ({note})")

    if errors:
        lines.append("")
        lines.append("  读取失败的文件:")
        for r in errors:
            lines.append(f"    - {os.path.basename(r['file'])}: {r.get('error', '未知错误')}")

    lines.append("=" * 60)
    return "\n".join(lines)


# ============ JSON Output ============

def results_to_json(results, min_words=DEFAULT_MIN_WORDS, max_words=DEFAULT_MAX_WORDS):
    """Convert results to JSON format for programmatic use.

    Args:
        results: list of analyze_file result dicts
        min_words: minimum word threshold
        max_words: maximum word threshold

    Returns:
        str: JSON string
    """
    output = {
        "timestamp": datetime.now().isoformat(),
        "standard": {"min": min_words, "max": max_words},
        "summary": {
            "total_files": len(results),
            "errors": len([r for r in results if r.get("error")]),
            "passed": 0,
            "under_min": 0,
            "over_max": 0,
        },
        "files": [],
    }

    for r in results:
        if r.get("error"):
            output["files"].append({
                "file": r["file"],
                "error": r["error"],
                "status": "error",
            })
            continue

        cn = r["chinese_chars"]
        meets, status = check_standard(cn, min_words, max_words)

        if meets:
            output["summary"]["passed"] += 1
        elif cn < min_words:
            output["summary"]["under_min"] += 1
        else:
            output["summary"]["over_max"] += 1

        output["files"].append({
            "file": r["file"],
            "chinese_chars": cn,
            "visible_chars": r["visible_chars"],
            "total_chars": r["total_chars"],
            "line_count": r["line_count"],
            "meets_standard": meets,
            "status": status,
        })

    return json.dumps(output, ensure_ascii=False, indent=2)


# ============ Main Entry Point ============

def main():
    """主函数：解析命令行参数并执行字数统计。"""
    parser = argparse.ArgumentParser(
        description="章节字数统计工具 — 统计中文字符数并检查是否达标",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用法示例:
  %(prog)s chapters/ch001.md                    # 单章统计
  %(prog)s chapters/ch001.md chapters/ch002.md  # 多章统计
  %(prog)s "chapters/ch*.md"                    # 通配符批量统计
  %(prog)s chapters/ch001.md --json             # JSON 输出
  %(prog)s chapters/ch001.md --min 1000 --max 2000  # 自定义范围

质量标准: 单章 1200-1500 字 (中文字符, 不含标点和空白)
        """,
    )

    parser.add_argument(
        "files",
        nargs="+",
        help="章节文件路径 (支持 glob 通配符, 如 chapters/ch*.md)",
    )
    parser.add_argument(
        "--min",
        type=int,
        default=DEFAULT_MIN_WORDS,
        help=f"最低字数标准 (默认: {DEFAULT_MIN_WORDS})",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=DEFAULT_MAX_WORDS,
        help=f"最高字数标准 (默认: {DEFAULT_MAX_WORDS})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果 (便于其他工具调用)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="安静模式: 只输出不达标的文件",
    )

    args = parser.parse_args()

    # Expand glob patterns into actual file paths
    file_list = expand_files(args.files)

    if not file_list:
        print("错误: 未找到任何匹配的文件", file=sys.stderr)
        sys.exit(1)

    # Analyze all files
    results = [analyze_file(f) for f in file_list]

    # JSON output mode
    if args.json:
        print(results_to_json(results, args.min, args.max))
        return

    # Human-readable output mode
    print("")
    print(f"章节字数统计  (标准: {args.min}-{args.max} 字)")
    print("-" * 60)

    for result in results:
        formatted = format_result(result, args.min, args.max)

        # In quiet mode, only show files that fail or have errors
        if args.quiet:
            cn = result.get("chinese_chars", 0)
            if result.get("error") or cn < args.min or cn > args.max:
                print(formatted)
        else:
            print(formatted)

    # Batch summary (only when more than 1 file)
    if len(results) > 1:
        print(generate_summary(results, args.min, args.max))

    # Exit code: 0 if all pass, 1 if any fail
    all_pass = True
    for r in results:
        if r.get("error"):
            all_pass = False
            break
        cn = r["chinese_chars"]
        if cn < args.min or cn > args.max:
            all_pass = False
            break

    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
