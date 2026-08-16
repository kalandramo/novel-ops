# -*- coding: utf-8 -*-
"""
novel-writer skill 度量工具
计算 L1 循环 B 组指标:σ²(句长方差) / TTR(用词多样性) / EGR(情感颗粒度比) / Pσ²(段落长度方差)

用法:
  python metrics.py <章节文件.txt>
  python metrics.py <章节文件.txt> --json        # 输出 JSON
  python metrics.py <章节文件.txt> --fingerprint 指纹库.json  # 计算 FP 语言指纹匹配度
  python metrics.py <本章.txt> --compare <样本.txt>  # 模仿评价:对比两段文本指标差异
  python metrics.py <本章.txt> --plagiarism <样本.txt>  # 查重自检:检测连续8字以上雷同
  python metrics.py <章1.txt> --stability <章2.txt> <章3.txt> ...  # 文风稳定性:跨章SC系数
  python metrics.py ch048.md ch049.md ch050.md --perturb  # 同质化检测+创意扰动建议

依赖:
  pip install jieba

门限阈值(skill 中定义,2026-08-01 调整):
  σ²  >= 25    (AI<15, 人写>15)
  TTR >= 0.25  (AI<0.15, 人写>0.15)
  EGR <= 0.60  (AI>0.60, 人写<0.50)
  Pσ² >= 80    (AI<50, 人写>50)
  FP  >= 2次/章 (AI=0, 人写>3)
"""

import sys
import re
import json
import math
from collections import Counter

try:
    import jieba
    jieba.setLogLevel(20)  # 关闭 jieba 日志
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False
    print("警告: 未安装 jieba,TTR 将按字符计算(精度降低)。安装: pip install jieba", file=sys.stderr)


# ============ 词库 ============

# 笼统情感词(AI 常用,人写应少用)
# 扩展至80+词,含川渝方言情感词汇
VAGUE_EMOTION_WORDS = {
    "难过", "开心", "高兴", "悲伤", "生气", "愤怒", "害怕", "恐惧", "紧张",
    "焦虑", "兴奋", "激动", "失望", "绝望", "痛苦", "快乐", "幸福", "孤独",
    "寂寞", "尴尬", "无奈", "心酸", "心碎", "心痛", "心疼", "感动", "震撼",
    "震惊", "惊讶", "意外", "释然", "平静", "烦躁", "郁闷", "压抑", "委屈",
    "不甘", "愤怒", "愤恨", "怨恨", "嫉恨", "嫉妒", "羡慕", "崇拜", "敬仰",
    "喜欢", "讨厌", "厌恶", "憎恶", "热爱", "痛恨",
    # 川渝方言情感
    "冒火", "鬼火冒", "心头慌", "焦心", "不安逸", "心欠欠", "巴适", "安逸",
    # 更细腻的情感
    "惆怅", "忐忑", "恍惚", "煎熬", "挣扎", "懊恼", "羞愧", "惶恐",
    "烦闷", "苦闷", "憋屈", "心塞", "心累", "崩溃", "麻木", "期盼",
    "向往", "憧憬", "失落", "空虚", "愧疚", "懊悔", "悔恨", "不甘心",
    "安心", "踏实", "笃定", "茫然", "困惑", "迷茫", "厌倦", "厌恶",
}

# 具体感官词(人写常用,有身体反应)
# 扩展至80+词,含川渝方言身体感受/美食感官/程序员术语
SENSORY_WORDS = {
    # 触觉
    "胃紧", "胃里发紧", "手凉", "手心发烫", "发抖", "颤抖", "发冷", "发热",
    "心跳加速", "心狂跳", "胸口发闷", "胸闷", "喘不过气", "呼吸困难",
    "嗓子发紧", "喉咙发紧", "声音发抖", "手心出汗", "出冷汗", "冒冷汗",
    "头皮发麻", "后背发凉", "脊背发凉", "膝盖发软", "腿软", "手脚冰凉",
    # 视觉
    "视野发白", "眼前发黑", "眼眶发热", "视线模糊", "眼睛发酸",
    # 听觉
    "耳鸣", "嗡嗡作响", "心脏狂跳",
    # 味觉
    "嘴里发苦", "嘴里发甜", "舌根发涩",
    # 综合
    "全身僵硬", "身体绷紧", "肌肉紧绷", "牙关紧咬", "嘴唇发干",
    # 川渝方言身体感受
    "脚杆打闪闪", "脑壳昏", "胃里翻", "手杆发软", "腿杆发酸",
    "眼皮跳", "脑壳痛", "太阳穴跳", "脸发烫", "耳朵发烫",
    # 美食/味觉感官
    "嘴巴发干", "舌头发麻", "嘴唇发烫", "喉咙发辣", "胃里发酸",
    "鼻子发酸", "脸颊发烫", "腮帮子发酸", "嗓子发辣", "舌根发苦",
    "胃里翻腾", "嘴里发涩", "喉咙发干", "嘴唇发白",
    # 程序员术语(身体反应比喻)
    "CPU烧了", "脑子宕机", "内存溢出", "思维卡顿", "系统崩溃",
    "某根弦断了", "死机", "蓝屏", "404", "报错",
}

# 过渡词/连接词(C 组指标用)
TRANSITION_WORDS = {
    "然而", "因此", "于是", "不过", "所以", "但是", "虽然", "尽管",
    "与此同时", "换言之", "总而言之", "综上所述", "由此可见",
    "换句话说", "不仅如此", "与此同时", "在此基础上",
}


# ============ 指标计算 ============

def split_sentences(text):
    """按句号/问号/感叹号/省略号分句"""
    # 去除多余空白
    text = re.sub(r'\s+', '', text)
    # 按标点分句
    sentences = re.split(r'[。！？!?…]+', text)
    # 过滤空句和过短句(少于2字)
    sentences = [s for s in sentences if len(s) >= 2]
    return sentences


def split_paragraphs(text):
    """按换行分段"""
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    return paragraphs


def tokenize(text):
    """中文分词"""
    if HAS_JIEBA:
        words = list(jieba.cut(text))
        # 过滤标点和空白
        words = [w for w in words if w.strip() and not re.match(r'^[\W_]+$', w)]
        return words
    else:
        # 退化方案:按字符
        return [c for c in text if c.strip() and not re.match(r'\W', c)]


def calc_sentence_length_variance(sentences):
    """σ² 句长方差:每句字数的标准差"""
    if not sentences:
        return 0
    lengths = [len(s) for s in sentences]
    mean = sum(lengths) / len(lengths)
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    return math.sqrt(variance)


def calc_ttr(text):
    """TTR 用词多样性:独特词数 / 总词数"""
    words = tokenize(text)
    if not words:
        return 0
    unique = len(set(words))
    total = len(words)
    return unique / total


def calc_egr(text):
    """EGR 情感颗粒度比:笼统情感词数 / 具体感官词数
    修复R7:改用子串匹配,不依赖jieba分词(避免"胃里发紧"被切成单字)
    """
    # 子串计数:在原文中直接搜索,不受分词影响
    vague_count = 0
    for word in VAGUE_EMOTION_WORDS:
        vague_count += text.count(word)
    sensory_count = 0
    for word in SENSORY_WORDS:
        sensory_count += text.count(word)
    # 防除零
    if sensory_count == 0:
        # 没有感官词,如果有笼统词则 EGR 极高
        return vague_count * 10 if vague_count > 0 else 0
    return vague_count / sensory_count


def calc_info_density_variance(paragraphs):
    """Iσ² 信息密度方差:每段实体信息量(名词+动词数)的方差
    修复R2:补齐L2卷级C组指标
    """
    if not paragraphs:
        return 0
    densities = []
    for p in paragraphs:
        words = tokenize(p)
        # 实体信息量:长度>1的词(近似名词+动词)
        info_words = [w for w in words if len(w) >= 2]
        density = len(info_words) / max(len(p), 1) * 100
        densities.append(density)
    if len(densities) < 2:
        return 0
    mean = sum(densities) / len(densities)
    variance = sum((d - mean) ** 2 for d in densities) / len(densities)
    return math.sqrt(variance)


def calc_plagiarism_check(text_a, text_b, min_ngram=8):
    """查重自检:检测两段文本中连续N字以上雷同的句子数
    修复R2:补齐模块十一查重自检
    返回:雷同片段列表
    """
    matches = []
    # 滑动窗口:在text_b中搜索text_a的所有min_ngram字子串
    for i in range(len(text_a) - min_ngram + 1):
        ngram = text_a[i:i + min_ngram]
        # 跳过纯标点和空白
        if ngram.strip() and not re.match(r'^[\W_]+$', ngram):
            if ngram in text_b:
                # 扩展匹配范围
                start = i
                end = i + min_ngram
                while end < len(text_a) and text_a[start:end+1] in text_b:
                    end += 1
                match_text = text_a[start:end]
                if match_text not in [m[2] for m in matches]:
                    matches.append((start, end - start, match_text))
    # 去重重叠
    unique = []
    seen_positions = set()
    for pos, length, text in matches:
        if not any(abs(pos - p) < length for p in seen_positions):
            unique.append(text)
            seen_positions.add(pos)
    return unique


def calc_style_stability(chapter_metrics_list):
    """SC 文风稳定性系数:多章指标相对均值的偏差
    修复R2:补齐L3全书D组指标
    输入:多章的metrics字典列表 [{sigma2, ttr, egr, psigma2}, ...]
    返回:SC值(0-1,越高越稳定)
    """
    if len(chapter_metrics_list) < 3:
        return 1.0  # 章节太少无法判断,默认稳定
    keys = ["sigma2", "ttr", "egr", "psigma2"]
    deviations = []
    for key in keys:
        values = [cm[key] for cm in chapter_metrics_list if key in cm]
        if len(values) < 3:
            continue
        mean = sum(values) / len(values)
        if mean == 0:
            continue
        avg_dev = sum(abs(v - mean) / mean for v in values) / len(values)
        deviations.append(avg_dev)
    if not deviations:
        return 1.0
    sc = 1.0 - (sum(deviations) / len(deviations))
    return max(0.0, min(1.0, sc))


def calc_paragraph_length_variance(paragraphs):
    """Pσ² 段落长度方差:每段字数的标准差"""
    if not paragraphs:
        return 0
    lengths = [len(p) for p in paragraphs]
    mean = sum(lengths) / len(lengths)
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    return math.sqrt(variance)


def calc_transition_density_variance(paragraphs):
    """Cσ² 连接词密度方差:每段过渡词数量的方差"""
    if not paragraphs:
        return 0
    counts = []
    for p in paragraphs:
        words = tokenize(p)
        count = sum(1 for w in words if w in TRANSITION_WORDS)
        counts.append(count)
    if len(counts) < 2:
        return 0
    mean = sum(counts) / len(counts)
    variance = sum((c - mean) ** 2 for c in counts) / len(counts)
    return math.sqrt(variance)


def calc_fingerprint_match(text, fingerprint):
    """FP 语言指纹匹配度:个人习惯用语在文中出现次数"""
    count = 0
    hits = {}
    for phrase in fingerprint.get("phrases", []):
        c = text.count(phrase)
        if c > 0:
            count += c
            hits[phrase] = c
    for action in fingerprint.get("actions", []):
        c = text.count(action)
        if c > 0:
            count += c
            hits[action] = c
    return count, hits


# ============ 门限判定 ============

THRESHOLDS = {
    "sigma2":      {"min": 25,   "ai": "<15",   "human": ">15"},
    "ttr":         {"min": 0.25, "ai": "<0.15",  "human": ">0.15"},
    "egr":         {"max": 0.60, "ai": ">0.60",  "human": "<0.50"},
    "psigma2":     {"min": 80,   "ai": "<50",   "human": ">50"},
    "csigma2":     {"min": 1.0,  "ai": "<0.5",  "human": ">1.5"},
    "isigma2":     {"min": 1.8,  "ai": "<1.0",  "human": ">2.5"},
    "fp":          {"min": 2,    "ai": "=0",    "human": ">3"},
    "sc":          {"min": 0.75, "ai": "<0.6",  "human": ">0.85"},
}


def check_threshold(name, value):
    """检查指标是否达标,返回 (通过, 状态)"""
    t = THRESHOLDS.get(name)
    if not t:
        return True, "未知指标"
    if "min" in t:
        if value >= t["min"]:
            if value >= float(t["human"].lstrip(">")):
                return True, "✅ 人写区间"
            return True, "✅ 达标"
        elif value < float(t["ai"].lstrip("<").lstrip("=")):
            return False, "❌ AI区间"
        else:
            return False, "⚠️ 临界"
    else:  # max 类型(egr)
        if value <= t["max"]:
            if value <= float(t["human"].lstrip("<")):
                return True, "✅ 人写区间"
            return True, "✅ 达标"
        elif value > float(t["ai"].lstrip(">")):
            return False, "❌ AI区间"
        else:
            return False, "⚠️ 临界"


# ============ 纠正建议 ============

CORRECTIONS = {
    "sigma2":  "σ²<25 → 句式过于单调:插入短句(3-5字)打断节奏,或将长句拆为两句,制造长短句交替",
    "ttr":     "TTR<0.25 → 用词过于集中:替换高频词的30%为同义词,加入个人习惯用语",
    "egr":     "EGR>0.60 → 情感笼统:将笼统词替换为具体感官描写(胃紧/手凉/视野发白),使用川渝方言/美食/程序员术语增强细腻度",
    "psigma2": "Pσ²<80 → 段落过于均匀:合并或拆分段落,制造长短段交替,优化手机阅读体验",
    "csigma2": "Cσ²<1.0 → 过渡词均匀:删除30%过渡词,改为直接跳转",
    "isigma2": "Iσ²<1.8 → 信息均匀:识别信息最稀疏的段加细节,信息最密集的段拆分留白",
    "fp":      "FP<2 → 缺个人指纹:植入口头禅/标志性动作,每章至少2次",
    "sc":      "SC<0.75 → 文风漂移:识别漂移最大的章节,以稳定章节为基准重写",
}


# ============ 主函数 ============

def analyze(text, fingerprint=None):
    """分析文本,返回完整报告"""
    sentences = split_sentences(text)
    paragraphs = split_paragraphs(text)

    sigma2 = calc_sentence_length_variance(sentences)
    ttr = calc_ttr(text)
    egr = calc_egr(text)
    psigma2 = calc_paragraph_length_variance(paragraphs)
    csigma2 = calc_transition_density_variance(paragraphs)
    isigma2 = calc_info_density_variance(paragraphs)

    result = {
        "char_count": len(text),
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
        "metrics": {
            "sigma2":  round(sigma2, 1),
            "ttr":     round(ttr, 3),
            "egr":     round(egr, 2),
            "psigma2": round(psigma2, 1),
            "csigma2": round(csigma2, 2),
            "isigma2": round(isigma2, 2),
        },
        "thresholds": THRESHOLDS,
        "checks": {},
        "corrections": [],
    }

    # 检查 B 组指标
    for name in ["sigma2", "ttr", "egr", "psigma2"]:
        value = result["metrics"][name]
        passed, status = check_threshold(name, value)
        result["checks"][name] = {"value": value, "status": status, "passed": passed}
        if not passed:
            result["corrections"].append(CORRECTIONS[name])

    # 检查 C 组指标(卷级)
    for name in ["csigma2", "isigma2"]:
        value = result["metrics"][name]
        passed, status = check_threshold(name, value)
        result["checks"][name] = {"value": round(value, 2), "status": status, "passed": passed}
        if not passed:
            result["corrections"].append(CORRECTIONS[name])

    # 语言指纹(FP)
    if fingerprint:
        fp_count, fp_hits = calc_fingerprint_match(text, fingerprint)
        passed, status = check_threshold("fp", fp_count)
        result["checks"]["fp"] = {"value": fp_count, "status": status, "passed": passed, "hits": fp_hits}
        if not passed:
            result["corrections"].append(CORRECTIONS["fp"])

    return result


def format_report(result):
    """格式化为可读报告"""
    lines = []
    lines.append("=" * 50)
    lines.append("人写特征度量报告")
    lines.append("=" * 50)
    lines.append(f"字数: {result['char_count']}  句数: {result['sentence_count']}  段数: {result['paragraph_count']}")
    lines.append("")

    lines.append("【B组 章级指标】")
    for name in ["sigma2", "ttr", "egr", "psigma2"]:
        c = result["checks"][name]
        lines.append(f"  {c['status']}  {name:8s} = {c['value']}")
    lines.append("")

    lines.append("【C组 卷级指标】")
    for name in ["csigma2", "isigma2"]:
        c = result["checks"][name]
        lines.append(f"  {c['status']}  {name:8s} = {c['value']}")
    lines.append("")

    if "fp" in result["checks"]:
        c = result["checks"]["fp"]
        lines.append("【语言指纹】")
        lines.append(f"  {c['status']}  fp       = {c['value']}次")
        if c.get("hits"):
            for phrase, cnt in c["hits"].items():
                lines.append(f"           命中: \"{phrase}\" x{cnt}")
        lines.append("")

    if result["corrections"]:
        lines.append("【纠正建议】")
        for i, corr in enumerate(result["corrections"], 1):
            lines.append(f"  {i}. {corr}")
    else:
        lines.append("【结论】全部指标达标,可以入库。")

    lines.append("=" * 50)
    return "\n".join(lines)


# ============ 模仿评价(对比模式) ============

def compare_texts(text_a, text_b, label_a="本章", label_b="样本"):
    """对比两段文本的指标差异,返回模仿相似度评分"""
    result_a = analyze(text_a)
    result_b = analyze(text_b)

    ma = result_a["metrics"]
    mb = result_b["metrics"]

    comparison = {
        label_a: ma,
        label_b: mb,
        "diff": {},
        "evaluation": {},
        "score": 100,
    }

    # σ² 对比:差值<50 达标
    diff_sigma2 = abs(ma["sigma2"] - mb["sigma2"])
    comparison["diff"]["sigma2"] = round(diff_sigma2, 1)
    if diff_sigma2 < 50:
        comparison["evaluation"]["sigma2"] = "✅ 达标"
    elif diff_sigma2 < 80:
        comparison["evaluation"]["sigma2"] = "⚠️ 临界"
        comparison["score"] -= 10
    else:
        comparison["evaluation"]["sigma2"] = "❌ 差距过大"
        comparison["score"] -= 25

    # TTR 对比:比值>0.85 达标
    ratio_ttr = ma["ttr"] / mb["ttr"] if mb["ttr"] > 0 else 0
    comparison["diff"]["ttr_ratio"] = round(ratio_ttr, 3)
    if ratio_ttr > 0.85:
        comparison["evaluation"]["ttr"] = "✅ 达标"
    elif ratio_ttr > 0.70:
        comparison["evaluation"]["ttr"] = "⚠️ 临界"
        comparison["score"] -= 10
    else:
        comparison["evaluation"]["ttr"] = "❌ 用词多样性不足"
        comparison["score"] -= 25

    # EGR 对比:本章≤样本 达标
    comparison["diff"]["egr_diff"] = round(ma["egr"] - mb["egr"], 2)
    if ma["egr"] <= mb["egr"]:
        comparison["evaluation"]["egr"] = "✅ 达标"
    elif ma["egr"] <= mb["egr"] + 0.5:
        comparison["evaluation"]["egr"] = "⚠️ 临界"
        comparison["score"] -= 10
    else:
        comparison["evaluation"]["egr"] = "❌ 情感过于笼统"
        comparison["score"] -= 25

    # Pσ² 对比:差值<100 达标
    diff_psigma2 = abs(ma["psigma2"] - mb["psigma2"])
    comparison["diff"]["psigma2"] = round(diff_psigma2, 1)
    if diff_psigma2 < 100:
        comparison["evaluation"]["psigma2"] = "✅ 达标"
    elif diff_psigma2 < 150:
        comparison["evaluation"]["psigma2"] = "⚠️ 临界"
        comparison["score"] -= 10
    else:
        comparison["evaluation"]["psigma2"] = "❌ 段落节奏差异大"
        comparison["score"] -= 25

    comparison["score"] = max(0, comparison["score"])
    return comparison


def format_compare_report(comparison, label_a="本章", label_b="样本"):
    """格式化模仿评价报告"""
    lines = []
    lines.append("=" * 55)
    lines.append("模仿评价报告")
    lines.append("=" * 55)
    lines.append("")

    # 指标对比表
    header = f"{'指标':8s}  {label_a:10s}  {label_b:10s}  {'差值/比值':>10s}  评价"
    lines.append(header)
    lines.append("-" * 55)

    rows = [
        ("σ²",     "sigma2",  "abs_diff"),
        ("TTR",    "ttr",     "ratio"),
        ("EGR",    "egr",     "signed_diff"),
        ("Pσ²",    "psigma2", "abs_diff"),
    ]

    for label, key, diff_type in rows:
        va = comparison[label_a][key]
        vb = comparison[label_b][key]
        if diff_type == "ratio":
            diff_val = comparison["diff"].get("ttr_ratio", 0)
            diff_str = f"{diff_val:.3f}"
        elif diff_type == "signed_diff":
            diff_val = comparison["diff"].get("egr_diff", 0)
            diff_str = f"{diff_val:+.2f}"
        else:
            diff_key = key if key != "sigma2" else "sigma2"
            diff_val = comparison["diff"].get(diff_key, 0)
            diff_str = f"{diff_val:.1f}"
        eval_str = comparison["evaluation"].get(key, "")
        lines.append(f"{label:8s}  {va:10.2f}  {vb:10.2f}  {diff_str:>10s}  {eval_str}")

    lines.append("")
    lines.append(f"模仿相似度评分: {comparison['score']}/100")
    lines.append("")

    if comparison["score"] >= 75:
        lines.append("✅ 模仿成功,可入库")
    elif comparison["score"] >= 50:
        lines.append("⚠️ 部分模仿,按不达标项调整后重写")
        # 列出不达标项
        for key, ev in comparison["evaluation"].items():
            if "❌" in ev:
                lines.append(f"   → {key}: {ev}")
    else:
        lines.append("❌ 模仿失败,重新提取特征卡或换样本")
        for key, ev in comparison["evaluation"].items():
            if "❌" in ev or "⚠️" in ev:
                lines.append(f"   → {key}: {ev}")

    lines.append("=" * 55)
    return "\n".join(lines)


# ============ 同质化检测与创意扰动 ============

def detect_opening_method(text):
    """检测章节开头方式:dialogue/scene/action/sensory/psychological/narrative"""
    lines = text.strip().split('\n')
    first_content = ""
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            first_content = line
            break
    if not first_content:
        return "unknown"
    first_50 = first_content[:50]

    if any(q in first_50 for q in ['\u201c', '\u201d', '\u300c', '\u300d', '\u2018', '\u2019']):
        return "dialogue"
    scene_words = ['聚光灯', '会议室', '办公室', '地铁', '街道', '咖啡', '走廊', '出租屋',
                   '下午', '晚上', '清晨', '夜里', '三天后', '一周后', '第二天', '傍晚']
    if any(w in first_50 for w in scene_words):
        return "scene"
    action_chars = ['走', '站', '坐', '推', '拉', '打开', '拿起', '放下', '转身', '甩', '抓']
    if any(first_50.startswith(w) for w in action_chars):
        return "action"
    sensory_words = ['风', '光', '声音', '味道', '气味', '冷', '热', '安静', '沉默', '潮湿', '干涩']
    if any(w in first_50 for w in sensory_words):
        return "sensory"
    psych_words = ['她想', '他想', '心里', '脑海', '记得', '不知道', '忽然想起', '突然想起']
    if any(w in first_50 for w in psych_words):
        return "psychological"
    return "narrative"


def calc_dialogue_ratio(text):
    """计算对话占比:引号内字符 / 总字符"""
    total = len(text)
    if total == 0:
        return 0
    in_quote = False
    quote_chars = 0
    quote_marks = {'\u201c', '\u201d', '\u300c', '\u300d'}
    for ch in text:
        if ch in quote_marks:
            in_quote = not in_quote
        elif in_quote:
            quote_chars += 1
    return quote_chars / total


def detect_homogenization(chapter_files):
    """同质化检测:分析多章文本,检测模式化写作

    输入:章节文件路径列表(按章序,最近N章)
    返回: {
        "chapter_count": int,
        "per_chapter": [{opening, structure, dialogue_ratio, metrics}, ...],
        "opening_monotony": bool,
        "structure_monotony": bool,
        "metric_trend": {sigma2: slope, ttr: slope, egr: slope, psigma2: slope},
        "mid_stagnation": bool,
        "issues": [{type, detail, severity}, ...]
    }
    """
    results = []
    for cf in chapter_files:
        try:
            with open(cf, "r", encoding="utf-8") as f:
                text = f.read()
            r = analyze(text)
            opening = detect_opening_method(text)
            dialogue_ratio = calc_dialogue_ratio(text)
            # 结构指纹:段数_句数_对话档_σ²档
            structure_fp = (
                f"p{r['paragraph_count']}_s{r['sentence_count']}"
                f"_d{int(dialogue_ratio * 10)}_o{int(r['metrics']['sigma2'] // 50)}"
            )
            results.append({
                "file": cf,
                "opening": opening,
                "structure": structure_fp,
                "dialogue_ratio": round(dialogue_ratio, 2),
                "metrics": r["metrics"],
            })
        except Exception as e:
            results.append({"file": cf, "error": str(e)})

    issues = []

    # 1. 开头方式单调性(连续3章同开头)
    openings = [r.get("opening", "?") for r in results if "opening" in r]
    opening_monotony = False
    for i in range(len(openings) - 2):
        if openings[i] == openings[i + 1] == openings[i + 2] and openings[i] != "unknown":
            opening_monotony = True
            issues.append({
                "type": "opening_monotony",
                "detail": f"连续3章(第{i+1}-{i+3}章)使用同一种开头方式: {openings[i]}",
                "severity": "medium",
            })
            break

    # 2. 结构指纹单调性(连续3章同结构)
    structures = [r.get("structure", "?") for r in results if "structure" in r]
    structure_monotony = False
    for i in range(len(structures) - 2):
        if structures[i] == structures[i + 1] == structures[i + 2]:
            structure_monotony = True
            issues.append({
                "type": "structure_monotony",
                "detail": f"连续3章(第{i+1}-{i+3}章)结构指纹相同: {structures[i]}",
                "severity": "high",
            })
            break

    # 3. 指标趋势(线性回归斜率)
    metric_trend = {}
    for key in ["sigma2", "ttr", "egr", "psigma2"]:
        values = [r["metrics"][key] for r in results if "metrics" in r]
        if len(values) >= 3:
            n_vals = len(values)
            x_mean = (n_vals - 1) / 2
            y_mean = sum(values) / n_vals
            num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
            den = sum((i - x_mean) ** 2 for i in range(n_vals))
            slope = num / den if den != 0 else 0
            metric_trend[key] = round(slope, 2)
            if key in ("sigma2", "psigma2") and slope < -2:
                issues.append({
                    "type": "metric_decline",
                    "detail": f"{key} 持续下降(斜率{slope:.2f}),警惕文风退化",
                    "severity": "high",
                })
            if key == "egr" and slope > 0.1:
                issues.append({
                    "type": "egr_rising",
                    "detail": f"EGR 持续上升(斜率{slope:.2f}),情感描写趋于笼统",
                    "severity": "medium",
                })

    # 4. 中段停滞(中段σ²波动过小)
    mid_stagnation = False
    if len(results) >= 10:
        mid_values = [r["metrics"]["sigma2"] for r in results[5:10] if "metrics" in r]
        if len(mid_values) >= 3:
            mid_range = max(mid_values) - min(mid_values)
            if mid_range < 20:
                mid_stagnation = True
                issues.append({
                    "type": "mid_stagnation",
                    "detail": f"中段\u03c3\u00b2波动范围仅{mid_range:.1f},章节间缺乏节奏变化",
                    "severity": "medium",
                })

    return {
        "chapter_count": len(results),
        "per_chapter": results,
        "opening_monotony": opening_monotony,
        "structure_monotony": structure_monotony,
        "metric_trend": metric_trend,
        "mid_stagnation": mid_stagnation,
        "issues": issues,
    }


# 扰动动作库
PERTURB_ACTIONS = {
    "opening_monotony": [
        ("视角偏移", "用配角视角开场,再切回主角"),
        ("对话开场", "直接用一句对话作为第一句,无铺垫"),
        ("时间错位", "开头是N天后,再闪回交代"),
        ("静默开场", "用'声音的消失'而非声音开场"),
    ],
    "structure_monotony": [
        ("留白章", "信息量减半,用氛围推进,全章只有1个场景"),
        ("物件叙事", "用一个物件串起全章,出现3次以上"),
        ("揭秘章结构", "用发现\u2192求证\u2192揭露\u2192反应结构替代打脸结构"),
        ("日常章结构", "表层日常+暗层推进副线,章末打破平静"),
    ],
    "metric_decline": [
        ("短句穿插", "在长段中插入3-5字短句,提升\u03c3\u00b2"),
        ("感官词注入", "在情绪段加入触觉/听觉描写,降低EGR"),
        ("段落重组", "合并短段或拆分长段,制造长短段交替,提升P\u03c3\u00b2"),
    ],
    "egr_rising": [
        ("感官替换", "搜索笼统情感词,替换为身体反应描写"),
        ("触觉优先", "本章情绪段优先用触觉(胃紧/手凉/心跳)"),
    ],
    "mid_stagnation": [
        ("主线扰动", "注入一个改变主线走向的小事件"),
        ("副线激活", "让一条沉寂的副线突然推进"),
        ("反派行动", "给反派一个意料之外但合理的行动"),
    ],
}


def generate_perturbation_suggestions(homogenization_report):
    """根据同质化检测结果生成扰动建议"""
    suggestions = []
    for issue in homogenization_report.get("issues", []):
        actions = PERTURB_ACTIONS.get(issue["type"], [])
        if actions:
            suggestions.append({
                "trigger": issue["detail"],
                "severity": issue["severity"],
                "options": actions,
            })
    if not suggestions:
        suggestions.append({
            "trigger": "未检测到明显同质化,建议保持创意警觉",
            "severity": "low",
            "options": [
                ("反预期反应", "本章某角色做出意料之外但合理的反应"),
                ("物件叙事", "用一个物件串起全章"),
            ],
        })
    return suggestions


def format_perturb_report(report, suggestions):
    """格式化同质化检测+扰动建议报告"""
    lines = []
    lines.append("=" * 55)
    lines.append("同质化检测 + 创意扰动报告")
    lines.append("=" * 55)
    lines.append(f"检测章数: {report['chapter_count']}")
    lines.append("")

    lines.append("【各章概览】")
    for i, ch in enumerate(report.get("per_chapter", []), 1):
        if "error" in ch:
            lines.append(f"  第{i}章: 读取失败 ({ch['error']})")
            continue
        m = ch.get("metrics", {})
        lines.append(
            f"  第{i}章: 开头={ch.get('opening', '?'):14s} "
            f"\u03c3\u00b2={m.get('sigma2', 0):.0f} "
            f"P\u03c3\u00b2={m.get('psigma2', 0):.0f} "
            f"\u5bf9\u8bdd={ch.get('dialogue_ratio', 0):.0%}"
        )
    lines.append("")

    if report.get("metric_trend"):
        lines.append("【指标趋势(斜率)】")
        for k, v in report["metric_trend"].items():
            arrow = "\u2192" if abs(v) < 0.5 else ("\u2193" if v < 0 else "\u2191")
            lines.append(f"  {k:8s}: {v:+.2f} {arrow}")
        lines.append("")

    if report.get("issues"):
        lines.append("【检测到的问题】")
        for i, issue in enumerate(report["issues"], 1):
            lines.append(f"  {i}. [{issue['severity']}] {issue['detail']}")
        lines.append("")
    else:
        lines.append("【检测结果】未检测到明显同质化问题")
        lines.append("")

    lines.append("【创意扰动建议】")
    for i, sugg in enumerate(suggestions, 1):
        lines.append(f"  \u89e6\u53d1: {sugg['trigger']}")
        lines.append(f"  \u7ea7\u522b: {sugg['severity']}")
        for j, (name, desc) in enumerate(sugg["options"], 1):
            lines.append(f"    \u9009\u9879{j}: {name} \u2014 {desc}")
        lines.append("")

    lines.append("\u6ce8: \u6270\u52a8\u662f'\u7ed9\u9009\u9879\u4e0d\u66ff\u51b3\u5b9a',\u4f5c\u8005\u53ef\u9009\u4e00\u4e2a\u6216\u5168\u90e8\u62d2\u7edd\u3002")
    lines.append("=" * 55)
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    filepath = sys.argv[1]
    output_json = "--json" in sys.argv

    # 对比模式:--compare <样本文件>
    compare_path = None
    if "--compare" in sys.argv:
        idx = sys.argv.index("--compare")
        if idx + 1 < len(sys.argv):
            compare_path = sys.argv[idx + 1]

    # 查重模式:--plagiarism <对比文件>
    plagiarism_path = None
    if "--plagiarism" in sys.argv:
        idx = sys.argv.index("--plagiarism")
        if idx + 1 < len(sys.argv):
            plagiarism_path = sys.argv[idx + 1]

    # 文风稳定性模式:--stability <多章文件1> <多章文件2> ...
    stability_mode = "--stability" in sys.argv

    # 扰动检测模式:--perturb <章1.txt> <章2.txt> <章3.txt> ...
    perturb_mode = "--perturb" in sys.argv

    # 读取指纹库
    fingerprint = None
    if "--fingerprint" in sys.argv:
        idx = sys.argv.index("--fingerprint")
        if idx + 1 < len(sys.argv):
            with open(sys.argv[idx + 1], "r", encoding="utf-8") as f:
                fingerprint = json.load(f)

    with open(filepath, "r", encoding="utf-8") as f:
        text_a = f.read()

    if compare_path:
        with open(compare_path, "r", encoding="utf-8") as f:
            text_b = f.read()
        comparison = compare_texts(text_a, text_b)
        if output_json:
            print(json.dumps(comparison, ensure_ascii=False, indent=2))
        else:
            print(format_compare_report(comparison))
    elif plagiarism_path:
        with open(plagiarism_path, "r", encoding="utf-8") as f:
            text_b = f.read()
        matches = calc_plagiarism_check(text_a, text_b, min_ngram=8)
        plag_result = {
            "match_count": len(matches),
            "threshold": 2,
            "passed": len(matches) <= 2,
            "matches": matches,
        }
        if output_json:
            print(json.dumps(plag_result, ensure_ascii=False, indent=2))
        else:
            lines = ["=" * 50, "查重自检报告", "=" * 50]
            lines.append(f"雷同片段数(连续8字+): {len(matches)}")
            lines.append(f"达标标准: ≤2处")
            if len(matches) <= 2:
                lines.append("✅ 达标,可入库")
            else:
                lines.append("❌ 超标,需改写雷同句式:")
                for i, m in enumerate(matches, 1):
                    lines.append(f"  {i}. \"{m}\"")
            lines.append("=" * 50)
            print("\n".join(lines))
    elif stability_mode:
        # 收集所有章节文件的指标
        chapter_files = [a for a in sys.argv[2:] if not a.startswith("--")]
        chapter_files = [f for f in chapter_files if f != filepath]
        chapter_files.insert(0, filepath)
        metrics_list = []
        for cf in chapter_files:
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    ct = f.read()
                r = analyze(ct)
                metrics_list.append(r["metrics"])
            except Exception as e:
                print(f"警告: 无法读取 {cf}: {e}", file=sys.stderr)
        sc = calc_style_stability(metrics_list)
        sc_result = {
            "chapter_count": len(metrics_list),
            "sc": round(sc, 3),
            "threshold": 0.75,
            "passed": sc >= 0.75,
            "per_chapter": metrics_list,
        }
        if output_json:
            print(json.dumps(sc_result, ensure_ascii=False, indent=2))
        else:
            lines = ["=" * 50, "文风稳定性报告", "=" * 50]
            lines.append(f"统计章数: {len(metrics_list)}")
            lines.append(f"SC(文风稳定性系数): {sc:.3f}")
            lines.append(f"达标标准: ≥0.75")
            if sc >= 0.85:
                lines.append("✅ 人写区间,文风稳定")
            elif sc >= 0.75:
                lines.append("✅ 达标")
            elif sc >= 0.6:
                lines.append("⚠️ 临界,部分章节有漂移")
            else:
                lines.append("❌ 文风漂移,识别漂移最大的章节重写")
            lines.append("=" * 50)
            print("\n".join(lines))
    elif perturb_mode:
        # 收集所有章节文件(排除flag参数)
        chapter_files = [a for a in sys.argv[1:] if not a.startswith("--")]
        if len(chapter_files) < 3:
            print("扰动检测需要至少3章文件用于模式比对")
            print("用法: python metrics.py ch048.md ch049.md ch050.md --perturb")
            sys.exit(1)
        report = detect_homogenization(chapter_files)
        suggestions = generate_perturbation_suggestions(report)
        if output_json:
            output = {
                "homogenization": report,
                "perturbation_suggestions": suggestions,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(format_perturb_report(report, suggestions))
    else:
        result = analyze(text_a, fingerprint)
        if output_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_report(result))


if __name__ == "__main__":
    main()
