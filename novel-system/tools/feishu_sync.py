#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书文档同步工具（降级 Stub）

将章节内容同步到飞书文档，用于存稿和协作审阅。
本脚本是降级 stub：实际飞书 API 调用留空，仅记录同步状态和打印日志。
同步失败不阻塞创作流程，仅打印警告。

用法示例:
    # 初始化同步状态
    python feishu_sync.py --init

    # 同步指定章节
    python feishu_sync.py --sync --chapter 1

    # 指定触发类型（G4质检通过 / G7落盘完成）
    python feishu_sync.py --sync --chapter 1 --trigger g7

    # 强制全量同步（重新同步所有已写章节）
    python feishu_sync.py --sync --force

    # 查看同步状态
    python feishu_sync.py --status

依赖:
    无第三方依赖，仅使用 Python 标准库。
    实际飞书 API 集成需要安装 lark-oapi 包并配置应用凭证。
"""

import sys
import os
import json
import argparse
import glob
from datetime import datetime


# ============ Constants ============

# State file path (relative to novel-system root)
# The script resolves this relative to its own location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NOVEL_SYSTEM_DIR = os.path.dirname(SCRIPT_DIR)
STATE_FILE = os.path.join(NOVEL_SYSTEM_DIR, "dynamic", "feishu_sync_state.json")

# Chapter file directory
CHAPTERS_DIR = os.path.join(NOVEL_SYSTEM_DIR, "chapters")

# Valid trigger types
VALID_TRIGGERS = {"g4", "g7", "gate4", "gate7", "manual"}

# Default state structure
DEFAULT_STATE = {
    "initialized": False,
    "initialized_at": None,
    "feishu_doc_id": None,
    "feishu_doc_url": None,
    "app_id": None,
    "app_secret": None,
    "last_sync_chapter": 0,
    "last_sync_time": None,
    "last_sync_status": "none",
    "last_sync_trigger": None,
    "last_error": None,
    "synced_chapters": {},
    "total_sync_count": 0,
    "total_sync_failures": 0,
}


# ============ State Management ============

def load_state():
    """加载同步状态文件。如果文件不存在则返回默认状态。

    Returns:
        dict: 同步状态字典
    """
    if not os.path.exists(STATE_FILE):
        return DEFAULT_STATE.copy()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        # Merge with defaults to ensure all keys exist
        merged = DEFAULT_STATE.copy()
        merged.update(state)
        return merged
    except json.JSONDecodeError:
        print(f"[WARN] 同步状态文件格式错误，使用默认状态: {STATE_FILE}", file=sys.stderr)
        return DEFAULT_STATE.copy()
    except Exception as e:
        print(f"[WARN] 加载同步状态失败: {e}", file=sys.stderr)
        return DEFAULT_STATE.copy()


def save_state(state):
    """保存同步状态到文件。

    Args:
        state: 同步状态字典

    Returns:
        bool: 保存是否成功
    """
    # Ensure the dynamic directory exists
    state_dir = os.path.dirname(STATE_FILE)
    try:
        os.makedirs(state_dir, exist_ok=True)
    except Exception as e:
        print(f"[WARN] 创建状态目录失败: {e}", file=sys.stderr)
        return False

    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[WARN] 保存同步状态失败: {e}", file=sys.stderr)
        return False


# ============ Initialization ============

def init_sync():
    """初始化飞书同步状态。

    清空之前的同步记录，创建全新的状态文件。
    如果需要配置飞书 API 凭证，请在初始化后手动编辑状态文件。

    Returns:
        bool: 初始化是否成功
    """
    print("=" * 50)
    print("飞书文档同步 - 初始化")
    print("=" * 50)

    # Create fresh state
    state = DEFAULT_STATE.copy()
    state["initialized"] = True
    state["initialized_at"] = datetime.now().isoformat()

    # Save state
    if save_state(state):
        print(f"  [OK] 同步状态已初始化")
        print(f"       状态文件: {STATE_FILE}")
        print(f"       初始化时间: {state['initialized_at']}")
        print("")
        print("  提示: 如需启用实际飞书同步，请编辑状态文件配置以下字段:")
        print("    - feishu_doc_id: 飞书文档 ID")
        print("    - feishu_doc_url: 飞书文档链接")
        print("    - app_id: 飞书应用 App ID")
        print("    - app_secret: 飞书应用 App Secret")
        print("")
        print("  当前模式: 降级 Stub（仅记录状态，不实际调用飞书 API）")
        print("=" * 50)
        return True
    else:
        print("  [FAIL] 初始化失败：无法写入状态文件")
        print("=" * 50)
        return False


# ============ Chapter Discovery ============

def find_chapter_file(chapter_num):
    """根据章号查找章节文件。

    Args:
        chapter_num: 章节编号（整数）

    Returns:
        str or None: 章节文件路径，如果找不到则返回 None
    """
    # Try zero-padded 3-digit format: ch001.md
    padded = f"ch{chapter_num:03d}.md"
    filepath = os.path.join(CHAPTERS_DIR, padded)

    if os.path.isfile(filepath):
        return filepath

    # Try alternative formats
    alternatives = [
        f"ch{chapter_num:02d}.md",
        f"ch{chapter_num}.md",
        f"chapter_{chapter_num:03d}.md",
        f"chapter_{chapter_num:02d}.md",
        f"chapter_{chapter_num}.md",
    ]

    for alt in alternatives:
        filepath = os.path.join(CHAPTERS_DIR, alt)
        if os.path.isfile(filepath):
            return filepath

    return None


def find_all_chapters():
    """查找所有已写的章节文件。

    Returns:
        list: 排序后的章节文件路径列表
    """
    pattern = os.path.join(CHAPTERS_DIR, "ch*.md")
    files = glob.glob(pattern)
    # Sort by chapter number extracted from filename
    def extract_num(filepath):
        import re
        match = re.search(r'ch(\d+)', os.path.basename(filepath))
        return int(match.group(1)) if match else 0
    files.sort(key=extract_num)
    return files


def extract_chapter_number(filepath):
    """从文件路径中提取章号。

    Args:
        filepath: 章节文件路径

    Returns:
        int or None: 章号，如果无法提取则返回 None
    """
    import re
    match = re.search(r'ch(\d+)', os.path.basename(filepath))
    return int(match.group(1)) if match else None


# ============ Sync Logic (Stub) ============

def sync_chapter_to_feishu(chapter_num, content, state):
    """将章节内容同步到飞书文档（Stub 实现）。

    这是一个降级 stub：实际飞书 API 调用留空。
    在实际集成时，此函数应调用飞书 OpenAPI 将内容写入飞书文档。

    Args:
        chapter_num: 章节编号
        content: 章节文本内容
        state: 当前同步状态

    Returns:
        tuple: (success bool, error_message str or None)
    """
    # --- STUB: Log the sync attempt ---
    # In a real implementation, this would:
    # 1. Authenticate with Feishu API using app_id / app_secret
    # 2. Open or create the target Feishu document
    # 3. Append or update the chapter content as a document block
    # 4. Return the document revision ID

    char_count = len(content)
    print(f"  [STUB] 模拟同步第 {chapter_num} 章到飞书文档")
    print(f"         内容长度: {char_count} 字符")
    print(f"         目标文档: {state.get('feishu_doc_id', '(未配置)')}")

    # Check if Feishu credentials are configured
    if not state.get("feishu_doc_id"):
        print(f"  [STUB] 飞书文档 ID 未配置，跳过实际同步")
        print(f"  [WARN] 飞书同步未执行（降级模式），不阻塞创作流程")
        # Return True because this is a stub — we don't want to block the workflow
        return True, None

    # If credentials are configured, simulate a successful sync
    print(f"  [STUB] 飞书 API 调用已跳过（Stub 模式）")
    print(f"  [OK] 第 {chapter_num} 章同步完成（模拟）")
    return True, None


def sync_single_chapter(chapter_num, trigger="manual", state=None):
    """同步单个章节到飞书。

    Args:
        chapter_num: 章节编号
        trigger: 触发类型 (g4/g7/gate4/manual)
        state: 可选的同步状态（如未提供则从文件加载）

    Returns:
        bool: 同步是否成功（stub 模式下总是返回 True）
    """
    if state is None:
        state = load_state()

    if not state.get("initialized"):
        print(f"[WARN] 同步状态未初始化，请先运行: python feishu_sync.py --init", file=sys.stderr)
        # Auto-initialize to avoid blocking
        state = DEFAULT_STATE.copy()
        state["initialized"] = True
        state["initialized_at"] = datetime.now().isoformat()
        save_state(state)
        print(f"[INFO] 已自动初始化同步状态", file=sys.stderr)

    # Validate trigger type
    if trigger not in VALID_TRIGGERS:
        print(f"[WARN] 未知触发类型 '{trigger}'，使用默认 'manual'", file=sys.stderr)
        trigger = "manual"

    # Find chapter file
    filepath = find_chapter_file(chapter_num)
    if filepath is None:
        print(f"[WARN] 未找到第 {chapter_num} 章的文件", file=sys.stderr)
        print(f"       搜索目录: {CHAPTERS_DIR}", file=sys.stderr)
        # Record the failure but don't block
        state["last_sync_chapter"] = chapter_num
        state["last_sync_time"] = datetime.now().isoformat()
        state["last_sync_status"] = "failed"
        state["last_sync_trigger"] = trigger
        state["last_error"] = f"Chapter file not found for chapter {chapter_num}"
        state["total_sync_failures"] += 1
        save_state(state)
        print(f"[WARN] 同步失败但不阻塞创作流程", file=sys.stderr)
        return False

    # Read chapter content
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"[WARN] 读取章节文件失败: {e}", file=sys.stderr)
        state["last_sync_chapter"] = chapter_num
        state["last_sync_time"] = datetime.now().isoformat()
        state["last_sync_status"] = "failed"
        state["last_sync_trigger"] = trigger
        state["last_error"] = str(e)
        state["total_sync_failures"] += 1
        save_state(state)
        print(f"[WARN] 同步失败但不阻塞创作流程", file=sys.stderr)
        return False

    # Perform sync (stub)
    print("")
    print("=" * 50)
    print(f"飞书文档同步 - 第 {chapter_num} 章")
    print(f"触发类型: {trigger}")
    print(f"章节文件: {filepath}")
    print("=" * 50)

    success, error = sync_chapter_to_feishu(chapter_num, content, state)

    # Update state
    now = datetime.now().isoformat()
    state["last_sync_chapter"] = chapter_num
    state["last_sync_time"] = now
    state["last_sync_trigger"] = trigger
    state["total_sync_count"] += 1

    if success:
        state["last_sync_status"] = "success"
        state["last_error"] = None
        state["synced_chapters"][str(chapter_num)] = {
            "synced_at": now,
            "trigger": trigger,
            "char_count": len(content),
            "file": filepath,
            "status": "success",
        }
        print(f"  [OK] 第 {chapter_num} 章同步状态已记录")
    else:
        state["last_sync_status"] = "failed"
        state["last_error"] = error or "Unknown error"
        state["total_sync_failures"] += 1
        state["synced_chapters"][str(chapter_num)] = {
            "synced_at": now,
            "trigger": trigger,
            "char_count": len(content),
            "file": filepath,
            "status": "failed",
            "error": error,
        }
        print(f"  [WARN] 同步失败但不阻塞创作流程")

    save_state(state)
    print("=" * 50)
    return success


def sync_all_chapters(state=None):
    """全量同步所有已写章节到飞书。

    Args:
        state: 可选的同步状态

    Returns:
        tuple: (成功数, 失败数)
    """
    if state is None:
        state = load_state()

    if not state.get("initialized"):
        print(f"[WARN] 同步状态未初始化，请先运行: python feishu_sync.py --init", file=sys.stderr)
        state = DEFAULT_STATE.copy()
        state["initialized"] = True
        state["initialized_at"] = datetime.now().isoformat()
        save_state(state)

    chapters = find_all_chapters()

    if not chapters:
        print(f"[INFO] 未找到任何章节文件")
        print(f"       搜索目录: {CHAPTERS_DIR}")
        return 0, 0

    print("")
    print("=" * 50)
    print(f"飞书文档同步 - 全量同步")
    print(f"找到 {len(chapters)} 个章节文件")
    print("=" * 50)

    success_count = 0
    fail_count = 0

    for filepath in chapters:
        chapter_num = extract_chapter_number(filepath)
        if chapter_num is None:
            print(f"  [SKIP] 无法解析章号: {filepath}")
            continue

        print(f"\n  正在同步第 {chapter_num} 章...")

        success = sync_single_chapter(chapter_num, trigger="force", state=state)
        if success:
            success_count += 1
        else:
            fail_count += 1

    print("")
    print("=" * 50)
    print(f"全量同步完成")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  总计: {len(chapters)}")
    print("=" * 50)

    return success_count, fail_count


# ============ Status Display ============

def show_status():
    """显示当前同步状态。"""
    state = load_state()

    print("")
    print("=" * 50)
    print("飞书文档同步状态")
    print("=" * 50)

    if not state.get("initialized"):
        print("  状态: 未初始化")
        print("  请先运行: python feishu_sync.py --init")
        print("=" * 50)
        return

    print(f"  初始化时间:     {state.get('initialized_at', 'N/A')}")
    print(f"  飞书文档 ID:    {state.get('feishu_doc_id', '(未配置)')}")
    print(f"  飞书文档链接:   {state.get('feishu_doc_url', '(未配置)')}")
    print(f"  应用 App ID:    {state.get('app_id', '(未配置)')}")
    print(f"  最后同步章号:   {state.get('last_sync_chapter', 0)}")
    print(f"  最后同步时间:   {state.get('last_sync_time', 'N/A')}")
    print(f"  最后同步状态:   {state.get('last_sync_status', 'none')}")
    print(f"  最后触发类型:   {state.get('last_sync_trigger', 'N/A')}")
    print(f"  同步总次数:     {state.get('total_sync_count', 0)}")
    print(f"  同步失败次数:   {state.get('total_sync_failures', 0)}")

    if state.get("last_error"):
        print(f"  最后错误信息:   {state.get('last_error')}")

    synced = state.get("synced_chapters", {})
    if synced:
        print(f"  已同步章节数:   {len(synced)}")
        print("")
        print("  已同步章节列表:")
        for ch_num, info in sorted(synced.items(), key=lambda x: int(x[0])):
            status_mark = "[OK]  " if info.get("status") == "success" else "[FAIL]"
            print(f"    {status_mark} 第 {ch_num} 章 - {info.get('synced_at', 'N/A')} ({info.get('trigger', 'N/A')})")
    else:
        print(f"  已同步章节数:   0")

    # Check for chapters not yet synced
    all_chapters = find_all_chapters()
    if all_chapters:
        all_nums = set()
        for fp in all_chapters:
            num = extract_chapter_number(fp)
            if num is not None:
                all_nums.add(num)

        synced_nums = set(int(k) for k in synced.keys())
        unsynced = all_nums - synced_nums

        if unsynced:
            print("")
            print(f"  未同步章节 ({len(unsynced)}):")
            for num in sorted(unsynced):
                print(f"    - 第 {num} 章")

    print("=" * 50)


# ============ Main Entry Point ============

def main():
    """主函数：解析命令行参数并执行对应的飞书同步操作。"""
    parser = argparse.ArgumentParser(
        description="飞书文档同步工具 — 将章节内容同步到飞书文档（降级 Stub）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用法示例:
  %(prog)s --init                                # 初始化同步状态
  %(prog)s --sync --chapter 1                    # 同步第1章
  %(prog)s --sync --chapter 1 --trigger g7       # G7落盘后同步第1章
  %(prog)s --sync --chapter 1 --trigger g4       # G4质检后同步第1章
  %(prog)s --sync --force                        # 强制全量同步
  %(prog)s --status                              # 查看同步状态

触发类型:
  g4      G4平台规则门通过后触发
  g7      G7状态落盘门通过后触发
  gate4   同 g4
  gate7   同 g7
  manual  手动触发（默认）

说明:
  本脚本是降级 stub，实际飞书 API 调用留空。
  同步失败不阻塞创作流程，仅打印警告。
  实际飞书集成需安装 lark-oapi 并配置应用凭证。
        """,
    )

    parser.add_argument(
        "--init",
        action="store_true",
        help="初始化同步状态（清空之前的记录）",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="同步章节内容到飞书",
    )
    parser.add_argument(
        "--chapter",
        type=int,
        default=None,
        help="指定要同步的章号（如: 1, 2, 3...）",
    )
    parser.add_argument(
        "--trigger",
        type=str,
        default="manual",
        choices=list(VALID_TRIGGERS),
        help="触发类型 (g4/g7/gate4/gate7/manual，默认: manual)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制全量同步（重新同步所有已写章节）",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="查看当前同步状态",
    )

    args = parser.parse_args()

    # No arguments — show help
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # --init: Initialize sync state
    if args.init:
        success = init_sync()
        sys.exit(0 if success else 1)

    # --status: Show sync status
    if args.status:
        show_status()
        sys.exit(0)

    # --sync: Perform sync
    if args.sync:
        if args.force:
            # Force full sync
            success_count, fail_count = sync_all_chapters()
            # Always exit 0 — sync failure should not block the creation flow
            sys.exit(0)
        elif args.chapter is not None:
            # Sync specific chapter
            success = sync_single_chapter(args.chapter, trigger=args.trigger)
            # Always exit 0 — sync failure should not block the creation flow
            sys.exit(0)
        else:
            print("[ERROR] 使用 --sync 时必须指定 --chapter N 或 --force", file=sys.stderr)
            print("        示例: python feishu_sync.py --sync --chapter 1", file=sys.stderr)
            print("        示例: python feishu_sync.py --sync --force", file=sys.stderr)
            sys.exit(1)

    # If no action specified
    print("[INFO] 未指定操作。使用 --help 查看用法。", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
