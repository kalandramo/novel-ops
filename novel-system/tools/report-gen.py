# -*- coding: utf-8 -*-
"""
质检报告生成器 — 将metrics.py JSON输出+门禁结果转为HTML报告
每章自动生成，保存到 reports/chXXX_report.html

用法:
  python report-gen.py --chapter 001 --metrics metrics.json --gates gate-results.json --output reports/ch001_report.html
  python report-gen.py --chapter 001 --metrics metrics.json --output reports/ch001_report.html  # 仅指标报告
  python report-gen.py --chapter 001 --metrics metrics.json --gates gate-results.json --mode QC_FULL  # 指定质检模式

依赖: 无（纯Python，自包含HTML生成）
"""

import sys
import json
import os
import argparse
from datetime import datetime


def load_json(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def fmt_val(val, threshold, fmt_type='num'):
    """格式化数值，返回HTML span带颜色"""
    if val is None:
        return '<span class="val-na">N/A</span>'
    if isinstance(val, float):
        s = f"{val:.3f}"
    else:
        s = str(val)

    if threshold is None:
        return f'<span class="val-pass">{s}</span>'

    return s


def check_pass(metric_name, value, thresholds):
    """检查指标是否通过"""
    if value is None or thresholds is None:
        return None

    t = thresholds.get(metric_name)
    if t is None:
        return None

    if isinstance(t, dict):
        min_val = t.get('min')
        max_val = t.get('max')
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True
    return None


def build_metrics_section(metrics_data, thresholds):
    """构建指标表格HTML"""
    if not metrics_data:
        return "<p>无指标数据</p>"

    hard_gates = [
        ("sigma2", "σ² 句长方差", "≥8"),
        ("ttr", "TTR 用词多样性", "≥0.40"),
        ("psigma2", "Pσ² 段长方差", "≥20"),
        ("burst_cv", "BurstCV 句长变异系数", "≥0.40"),
        ("para_cv", "ParaCV 段长变异系数", "≥0.30"),
        ("ngram3_rep", "3gramRep 3-gram重复率", "≤0.08"),
        ("ngram3_uniq", "3gramUniq 3-gram唯一率", "≥0.85"),
    ]

    ref_metrics = [
        ("egr", "EGR 情感颗粒度比", "≤2.0"),
        ("csigma2", "Cσ² 过渡词密度方差", "≥0.15"),
        ("isigma2", "Iσ² 信息密度方差", "≥1.8"),
        ("dialog_ratio", "对话占比", "5%-65%"),
        ("punct_cv", "标点CV", "≥0.30"),
        ("ai_pattern_density", "AI模式密度", "≤0.05"),
        ("ai_pattern_total", "AI模式总数", "≤3"),
    ]

    ratio_metrics = {"dialog_ratio", "ai_pattern_density"}

    html = '<div class="section">\n'
    html += '  <h3>硬门禁指标（7项）</h3>\n'
    html += '  <table class="metrics-table">\n'
    html += '    <tr><th>指标</th><th>名称</th><th>当前值</th><th>阈值</th><th>结果</th></tr>\n'

    for key, name, thresh_label in hard_gates:
        val = metrics_data.get(key)
        passed = check_pass(key, val, thresholds)
        if passed is True:
            status = '<span class="badge badge-pass">PASS</span>'
            val_class = 'val-pass'
        elif passed is False:
            status = '<span class="badge badge-fail">FAIL</span>'
            val_class = 'val-fail'
        else:
            status = '<span class="badge badge-na">N/A</span>'
            val_class = 'val-na'

        val_str = f"{val:.3f}" if isinstance(val, float) else (str(val) if val is not None else "N/A")
        html += f'    <tr><td>{key}</td><td>{name}</td><td class="{val_class}">{val_str}</td><td>{thresh_label}</td><td>{status}</td></tr>\n'

    html += '  </table>\n'
    html += '</div>\n'

    html += '<div class="section">\n'
    html += '  <h3>参考指标（仅预警）</h3>\n'
    html += '  <table class="metrics-table">\n'
    html += '    <tr><th>指标</th><th>名称</th><th>当前值</th><th>阈值</th><th>结果</th></tr>\n'

    for key, name, thresh_label in ref_metrics:
        val = metrics_data.get(key)
        if val is not None:
            if key in ratio_metrics and isinstance(val, (int, float)):
                val_str = f"{val:.1%}"
            elif isinstance(val, float):
                val_str = f"{val:.3f}"
            else:
                val_str = str(val)
            status = '<span class="badge badge-warn">参考</span>'
        else:
            val_str = "N/A"
            status = '<span class="badge badge-na">N/A</span>'
        html += f'    <tr><td>{key}</td><td>{name}</td><td>{val_str}</td><td>{thresh_label}</td><td>{status}</td></tr>\n'

    html += '  </table>\n'
    html += '</div>\n'

    aitext = metrics_data.get('aitext_ai_percent')
    if aitext is not None:
        html += '<div class="section">\n'
        html += '  <h3>AITextDetector 报告</h3>\n'
        at_cls = "val-fail" if aitext > 30 else "val-pass"
        html += f'  <p>AI句占比: <span class="{at_cls}">{aitext:.1f}%</span>'
        html += f'  （阈值 ≤30%）</p>\n'
        html += '</div>\n'

    return html


def build_gates_section(gates_data):
    """构建门禁检查HTML"""
    if not gates_data:
        return ""

    gates_list = gates_data.get('gates', [])
    if not gates_list:
        return '<div class="section">\n  <h3>门禁检查结果</h3>\n  <p>无门禁数据</p>\n</div>\n'

    html = '<div class="section">\n'
    html += '  <h3>门禁检查结果</h3>\n'
    html += '  <table class="gate-table">\n'
    html += '    <tr><th>门禁</th><th>检查项</th><th>结果</th><th>详情</th></tr>\n'

    for gate in gates_list:
        name = gate.get('name', '')
        for item in gate.get('items', []):
            check_name = item.get('check', '')
            passed = item.get('passed')
            detail = item.get('detail', '')
            level = item.get('level', 'hard')  # hard / warning

            if passed is True:
                status = '<span class="badge badge-pass">PASS</span>'
            elif passed is False:
                if level == 'warning':
                    status = '<span class="badge badge-warn">⚠️ WARN</span>'
                else:
                    status = '<span class="badge badge-fail">FAIL</span>'
            else:
                status = '<span class="badge badge-skip">SKIP</span>'

            html += f'    <tr><td>{name}</td><td>{check_name}</td><td>{status}</td><td>{detail}</td></tr>\n'

    html += '  </table>\n'
    html += '</div>\n'
    return html


def build_summary(metrics_data, gates_data, thresholds, qc_mode):
    """构建总览"""
    hard_pass = 0
    hard_fail = 0
    hard_total = 7

    hard_keys = ["sigma2", "ttr", "psigma2", "burst_cv", "para_cv", "ngram3_rep", "ngram3_uniq"]
    for key in hard_keys:
        val = metrics_data.get(key) if metrics_data else None
        result = check_pass(key, val, thresholds)
        if result is True:
            hard_pass += 1
        elif result is False:
            hard_fail += 1

    gate_pass = 0
    gate_fail = 0
    gate_warn = 0
    gate_skip = 0
    if gates_data:
        for gate in gates_data.get('gates', []):
            for item in gate.get('items', []):
                if item.get('passed') is True:
                    gate_pass += 1
                elif item.get('passed') is False:
                    if item.get('level') == 'warning':
                        gate_warn += 1
                    else:
                        gate_fail += 1
                else:
                    gate_skip += 1

    overall = "通过" if hard_fail == 0 and gate_fail == 0 else "未通过"

    has_data = (metrics_data and any(metrics_data.get(k) is not None for k in hard_keys))
    if not has_data and gate_fail == 0:
        overall = "无数据"
        overall_class = "fail"
    else:
        overall_class = "pass" if hard_fail == 0 and gate_fail == 0 else "fail"

    html = '<div class="summary">\n'
    html += f'  <div class="summary-card {overall_class}">\n'
    html += f'    <div class="summary-title">总体结果</div>\n'
    html += f'    <div class="summary-value">{overall}</div>\n'
    html += f'  </div>\n'
    html += f'  <div class="summary-card">\n'
    html += f'    <div class="summary-title">硬门禁</div>\n'
    html += f'    <div class="summary-value">{hard_pass}/{hard_total} 通过</div>\n'
    html += f'    <div class="summary-sub">{hard_fail} 项未通过</div>\n'
    html += f'  </div>\n'

    if gates_data:
        html += f'  <div class="summary-card">\n'
        html += f'    <div class="summary-title">门禁检查</div>\n'
        html += f'    <div class="summary-value">{gate_pass} 通过</div>\n'
        html += f'    <div class="summary-sub">{gate_fail} 失败 / {gate_warn} 警告 / {gate_skip} 跳过</div>'
        html += f'  </div>\n'

    html += f'  <div class="summary-card">\n'
    html += f'    <div class="summary-title">质检模式</div>\n'
    html += f'    <div class="summary-value">{qc_mode}</div>\n'
    html += f'  </div>\n'
    html += '</div>\n'

    return html


def generate_html(chapter_num, metrics_data, gates_data, thresholds, qc_mode, chapter_title=""):
    """生成完整HTML报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ch_id = f"ch{chapter_num.zfill(3)}" if isinstance(chapter_num, str) else f"ch{chapter_num:03d}"

    html = f"""<!-- Generated by Trae Work -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>第{chapter_num}章 质检报告</title>
<style>
:root {{
  --bg: #0f1117;
  --bg2: #1a1d27;
  --bg3: #222530;
  --ink: #e8e8e8;
  --muted: #8b8b9a;
  --rule: #2a2d3a;
  --accent: #4fc3f7;
  --accent2: #ff8a65;
  --green: #66bb6a;
  --red: #ef5350;
  --yellow: #ffc107;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  background: var(--bg);
  color: var(--ink);
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
  font-size: 14px;
  line-height: 1.7;
  padding: 1.5rem 1rem;
}}
.container {{ max-width: 860px; margin: 0 auto; }}
header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 0;
  border-bottom: 1px solid var(--rule);
  margin-bottom: 1.5rem;
}}
header .ch-info h1 {{ font-size: 1.4rem; font-weight: 700; }}
header .ch-info .subtitle {{ color: var(--muted); font-size: 0.85rem; margin-top: 0.2rem; }}
header .timestamp {{ color: var(--muted); font-size: 0.8rem; text-align: right; }}
.section {{ margin: 1.5rem 0; }}
.section h3 {{
  font-size: 1.05rem;
  color: var(--accent);
  margin-bottom: 0.75rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--rule);
}}
table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}}
th {{
  background: var(--bg2);
  color: var(--accent);
  font-weight: 600;
  text-align: left;
  padding: 0.5rem 0.7rem;
  border-bottom: 1px solid var(--rule);
}}
td {{
  padding: 0.5rem 0.7rem;
  border-bottom: 1px solid var(--rule);
}}
tr:hover td {{ background: var(--bg2); }}
.val-pass {{ color: var(--green); font-weight: 600; }}
.val-fail {{ color: var(--red); font-weight: 600; }}
.val-na {{ color: var(--muted); }}
.badge {{
  display: inline-block;
  padding: 0.1rem 0.5rem;
  border-radius: 3px;
  font-size: 0.72rem;
  font-weight: 600;
}}
.badge-pass {{ background: rgba(102,187,106,0.15); color: var(--green); }}
.badge-fail {{ background: rgba(239,83,80,0.15); color: var(--red); }}
.badge-warn {{ background: rgba(255,193,7,0.15); color: var(--yellow); }}
.badge-na {{ background: rgba(139,139,154,0.15); color: var(--muted); }}
.badge-skip {{ background: rgba(139,139,154,0.1); color: var(--muted); }}
.summary {{
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 1.5rem;
}}
.summary-card {{
  flex: 1;
  min-width: 130px;
  background: var(--bg2);
  border-radius: 6px;
  padding: 1rem;
  text-align: center;
}}
.summary-card.pass {{ border-top: 3px solid var(--green); }}
.summary-card.fail {{ border-top: 3px solid var(--red); }}
.summary-title {{ font-size: 0.75rem; color: var(--muted); margin-bottom: 0.3rem; }}
.summary-value {{ font-size: 1.4rem; font-weight: 700; color: var(--accent); }}
.summary-card.pass .summary-value {{ color: var(--green); }}
.summary-card.fail .summary-value {{ color: var(--red); }}
.summary-sub {{ font-size: 0.72rem; color: var(--muted); margin-top: 0.2rem; }}
.gate-table th, .gate-table td {{ text-align: left; }}
.word-count {{
  display: inline-block;
  padding: 0.3rem 0.8rem;
  background: var(--bg2);
  border-radius: 4px;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}}
.word-count.pass {{ color: var(--green); }}
.word-count.fail {{ color: var(--red); }}
footer {{
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid var(--rule);
  text-align: center;
  color: var(--muted);
  font-size: 0.75rem;
}}
@media (max-width: 600px) {{
  .summary {{ flex-direction: column; }}
  header {{ flex-direction: column; gap: 0.5rem; }}
}}
</style>
</head>
<body>
<div class="container">

<header>
  <div class="ch-info">
    <h1>第 {chapter_num} 章 质检报告</h1>
    <div class="subtitle">{chapter_title}</div>
  </div>
  <div class="timestamp">{now}</div>
</header>

{build_summary(metrics_data, gates_data, thresholds, qc_mode)}

{build_metrics_section(metrics_data, thresholds)}

{build_gates_section(gates_data)}

<footer>
  自动生成 — 小说写作系统 v2.1 — {ch_id}
</footer>

</div>
</body>
</html>"""
    return html


def main():
    parser = argparse.ArgumentParser(description="质检报告生成器")
    parser.add_argument("--chapter", required=True, help="章节号，如 001")
    parser.add_argument("--metrics", help="metrics.py --json 输出的JSON文件路径")
    parser.add_argument("--gates", help="门禁检查结果JSON文件路径")
    parser.add_argument("--output", help="输出HTML路径（默认 reports/chXXX_report.html）")
    parser.add_argument("--mode", default="QC_FULL", help="质检模式 QC_FULL/QC_CHECK/QC_SKIP")
    parser.add_argument("--title", default="", help="章节标题")
    args = parser.parse_args()

    metrics_data = load_json(args.metrics)
    gates_data = load_json(args.gates)

    thresholds = {
        "sigma2": {"min": 8},
        "ttr": {"min": 0.40},
        "psigma2": {"min": 20},
        "burst_cv": {"min": 0.40},
        "para_cv": {"min": 0.30},
        "ngram3_rep": {"max": 0.08},
        "ngram3_uniq": {"min": 0.85},
    }

    if metrics_data and "metrics" in metrics_data:
        metrics_data = metrics_data["metrics"]

    html = generate_html(args.chapter, metrics_data, gates_data, thresholds, args.mode, args.title)

    if args.output:
        output_path = args.output
    else:
        report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
        os.makedirs(report_dir, exist_ok=True)
        ch_id = f"ch{args.chapter.zfill(3)}" if isinstance(args.chapter, str) else f"ch{args.chapter:03d}"
        output_path = os.path.join(report_dir, f"{ch_id}_report.html")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"报告已生成: {output_path}")


if __name__ == "__main__":
    main()
