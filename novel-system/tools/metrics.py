# -*- coding: utf-8 -*-
"""
novel-writer skill 度量工具
计算章级指标:σ²/TTR/Pσ²/BurstCV/ParaCV/NgramRep/NgramUniq + 参考指标EGR/Cσ²/Iσ²/对话占比/标点CV

用法:
  python metrics.py <章节文件.txt>
  python metrics.py <章节文件.txt> --json        # 输出 JSON
  python metrics.py <章节文件.txt> --aitext      # 启用AITextDetector第二层参考检测
  python metrics.py <章节文件.txt> --fingerprint 指纹库.json  # 计算 FP 语言指纹匹配度
  python metrics.py <本章.txt> --compare <样本.txt>  # 模仿评价:对比两段文本指标差异
  python metrics.py <本章.txt> --plagiarism <样本.txt>  # 查重自检:检测连续8字以上雷同
  python metrics.py <章1.txt> --stability <章2.txt> <章3.txt> ...  # 文风稳定性:跨章SC系数
  python metrics.py ch048.md ch049.md ch050.md --perturb  # 同质化检测+创意扰动建议

依赖:
  pip install jieba

=== 硬门禁指标(纯统计,不依赖词库) ===
  σ²        >= 8      (AI<5, 人写>10)    — 句长标准差
  TTR       >= 0.40   (AI<0.30, 人写>0.48) — 用词多样性
  Pσ²       >= 20     (AI<12, 人写>28)    — 段长标准差
  BurstCV   >= 0.40   (AI<0.30, 人写>0.50) — 句长变异系数(std/mean)
  ParaCV    >= 0.30   (AI<0.20, 人写>0.40) — 段长变异系数
  3gramRep  <= 0.08   (AI>0.10, 人写<0.06) — 3-gram重复率
  3gramUniq >= 0.85   (AI<0.70, 人写>0.90) — 3-gram唯一率

=== 参考指标(仅预警,不做硬门禁) ===
  EGR       <= 2.0    (AI>5.0, 人写<1.0)  — 情感颗粒度比(依赖词库,易误判)
  Cσ²       >= 0.15   (AI<0.05, 人写>0.25) — 过渡词密度方差(依赖词库)
  Iσ²       >= 1.8    (AI<1.0, 人写>2.5)  — 信息密度方差
  对话占比    5%-65%                      — 对话字符/总字符
  标点CV    >= 0.30                      — 标点间距变异系数

=== 其他指标 ===
  FP  >= 2次/章 (AI=0, 人写>3)
  SC  >= 0.75  (AI<0.6, 人写>0.85)

校准依据(2026-09-05 基于实测+文献+社区工程实践):
  1. 实测样本: 番茄《长安食话》/晋江《攻玉》/晋江《太傅给我当牛马》
     人写: σ²=17-21/TTR=0.52-0.66/Pσ²=20-25/BurstCV=0.53-0.59/ParaCV=0.44-0.59
           3gramRep=0.039-0.048/3gramUniq=0.917-0.922
     AI:   σ²=4.1/TTR=0.30/Pσ²=8.7/BurstCV=0.219/ParaCV=0.114
           3gramRep=0.136/3gramUniq=0.567
  2. 社区工程参考: 句长std 8-18(人写)/<6(AI); 段长CV 0.4-1.2(人写)/<0.3(AI)
  3. Burstiness CV: 人写0.60-0.85, AI 0.15-0.30 (GPTZero/第三方检测器参考值)
  4. 设计原则: 硬门禁指标不依赖词库,不受题材影响;参考指标依赖词库,易误判特定题材
"""

import sys
import re
import json
import math
import os
from collections import Counter

try:
    import jieba
    jieba.setLogLevel(20)  # 关闭 jieba 日志
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False
    print("警告: 未安装 jieba,TTR 将按字符计算(精度降低)。安装: pip install jieba", file=sys.stderr)

try:
    from aitext_detector.detector import AITextDetector as _AITextDetector
    _aitext_model_path = os.path.join(os.path.dirname(__file__), 'aitext_detector', 'models.json')
    _aitext_instance = None
    HAS_AITEXT = True
except ImportError:
    HAS_AITEXT = False
    _aitext_model_path = None
    _aitext_instance = None


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
# 2026-09-05: 基于番茄/晋江真实人写样本校准，补充常见身体反应短词
SENSORY_WORDS = {
    # 触觉(原有)
    "胃紧", "胃里发紧", "手凉", "手心发烫", "发抖", "颤抖", "发冷", "发热",
    "心跳加速", "心狂跳", "胸口发闷", "胸闷", "喘不过气", "呼吸困难",
    "嗓子发紧", "喉咙发紧", "声音发抖", "手心出汗", "出冷汗", "冒冷汗",
    "头皮发麻", "后背发凉", "脊背发凉", "膝盖发软", "腿软", "手脚冰凉",
    # 视觉(原有)
    "视野发白", "眼前发黑", "眼眶发热", "视线模糊", "眼睛发酸",
    # 听觉(原有)
    "耳鸣", "嗡嗡作响", "心脏狂跳",
    # 味觉(原有)
    "嘴里发苦", "嘴里发甜", "舌根发涩",
    # 综合(原有)
    "全身僵硬", "身体绷紧", "肌肉紧绷", "牙关紧咬", "嘴唇发干",
    # 川渝方言身体感受(原有)
    "脚杆打闪闪", "脑壳昏", "胃里翻", "手杆发软", "腿杆发酸",
    "眼皮跳", "脑壳痛", "太阳穴跳", "脸发烫", "耳朵发烫",
    # 美食/味觉感官(原有)
    "嘴巴发干", "舌头发麻", "嘴唇发烫", "喉咙发辣", "胃里发酸",
    "鼻子发酸", "脸颊发烫", "腮帮子发酸", "嗓子发辣", "舌根发苦",
    "胃里翻腾", "嘴里发涩", "喉咙发干", "嘴唇发白",
    # 程序员术语(身体反应比喻)(原有)
    "CPU烧了", "脑子宕机", "内存溢出", "思维卡顿", "系统崩溃",
    "某根弦断了", "死机", "蓝屏", "404", "报错",
    # === 2026-09-05 新增：常见身体反应短词（基于真实样本校准）===
    # 叹气类
    "叹了口气", "叹了一口气", "叹气", "轻叹",
    # 脸色变化
    "脸红", "脸一红", "脸涨红", "脸通红", "脸泛红", "脸红了",
    "脸白了", "脸色白", "脸色一白", "脸色苍白", "面色一白", "面白如纸",
    "脸青", "脸色发青",
    # 咬唇/咬牙
    "咬唇", "咬了咬唇", "咬嘴唇", "咬紧牙", "咬了咬",
    # 皱眉
    "皱眉", "蹙眉", "拧眉", "皱了皱眉",
    # 颤抖/颤动
    "颤动", "微颤", "发颤",
    # 攥紧/握拳
    "攥紧", "握紧", "攥拳", "握拳", "捏紧",
    # 吞咽
    "吞咽", "咽了口", "咽了咽",
    # 僵硬
    "一僵", "僵硬", "身体僵", "脊背一僵",
    # 呼吸
    "深呼吸", "深吸了", "吸了口气", "倒吸一口",
    # 嘴角
    "嘴角抽", "嘴角扬", "嘴角扯", "嘴角一", "唇角一",
    # 瞳孔
    "瞳孔缩", "瞳孔一缩", "瞳孔放大",
    # 手指
    "手指颤", "手指发颤", "指尖发凉", "指尖冰凉",
    # 眼部
    "红了眼", "红了眼眶", "眼皮重", "眼皮打", "眼皮都快",
    "眼底", "眼圈红", "眼尾",
    # 松气
    "松了口气", "松了一口气",
    # 胃部
    "胃袋", "胃里抽", "胃一紧",
    # 其他常见
    "脊背一", "后背一", "额角冒汗", "额头冒汗", "额头出汗",
    "喉结滚", "喉结上下", "喉头滚",
    "拳头攥", "双拳紧握",
    "倒退一步", "后退一步", "踉跄",
}

# 过渡词/连接词(C 组指标用)
# 2026-09-05: 补充网文常见过渡词(基于番茄/晋江样本校准)
TRANSITION_WORDS = {
    # 正式过渡词(原有)
    "然而", "因此", "于是", "不过", "所以", "但是", "虽然", "尽管",
    "与此同时", "换言之", "总而言之", "综上所述", "由此可见",
    "换句话说", "不仅如此", "在此基础上",
    # 网文常见过渡词(新增)
    "突然", "忽然", "猛地", "陡然", "骤然",
    "随后", "紧接着", "接着",
    "正当", "就在", "不料", "谁知", "哪知", "岂料",
    "果然", "果不其然", "原来",
    "此刻", "这一刻", "下一秒",
    "只不过", "岂知", "哪曾想",
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
    # 防除零:2026-09-05修复,不再×10极端惩罚
    # 3个笼统词+0感官词 → EGR=3(临界), 36个笼统词+0感官词 → EGR=36(AI区间)
    if sensory_count == 0:
        return vague_count if vague_count > 0 else 0
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
    keys = ["sigma2", "ttr", "burst_cv", "psigma2"]
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
    total = sum(counts)
    if total == 0:
        # 2026-09-05: 无过渡词时无法判断分布,设为最低通过值
        return 0.15
    mean = total / len(counts)
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


def calc_ngram_repetition(text, n=3):
    """N-gram重复率:重复n-gram数/总n-gram数
    不依赖词库,纯统计。AI文本倾向复用相同短语结构。
    返回:(重复率, 唯一率)
    """
    clean = re.sub(r'[\s\n]+', '', text)
    if len(clean) < n:
        return 0.0, 1.0
    ngrams = [clean[i:i+n] for i in range(len(clean)-n+1)]
    total = len(ngrams)
    if total == 0:
        return 0.0, 1.0
    counts = Counter(ngrams)
    unique = len(counts)
    repeated = sum(1 for c in counts.values() if c > 1)
    return repeated / total, unique / total


def calc_burstiness_cv(sentences):
    """Burstiness CV:句长变异系数 = std/mean
    GPTZero核心指标之一,衡量文本波动程度。
    人写0.5-0.85+, AI 0.15-0.30
    """
    if not sentences:
        return 0
    lengths = [len(s) for s in sentences]
    if len(lengths) < 2:
        return 0
    mean_l = sum(lengths) / len(lengths)
    if mean_l == 0:
        return 0
    var_l = sum((l - mean_l) ** 2 for l in lengths) / len(lengths)
    std_l = math.sqrt(var_l)
    return std_l / mean_l


def calc_paragraph_cv(paragraphs):
    """段落长度CV:段长变异系数 = std/mean
    社区参考:人写0.4-1.2, AI<0.3
    """
    if not paragraphs:
        return 0
    lengths = [len(p) for p in paragraphs]
    if len(lengths) < 2:
        return 0
    mean_l = sum(lengths) / len(lengths)
    if mean_l == 0:
        return 0
    var_l = sum((l - mean_l) ** 2 for l in lengths) / len(lengths)
    std_l = math.sqrt(var_l)
    return std_l / mean_l


def calc_punctuation_rhythm_cv(text):
    """标点节奏CV:标点间距的变异系数
    衡量标点分布的均匀程度。AI标点间距更均匀(低CV)。
    """
    clean = re.sub(r'[\s\n]+', '', text)
    # 找所有标点位置
    punct_positions = [i for i, c in enumerate(clean) if c in '，。！？；：、…—']
    if len(punct_positions) < 2:
        return 0
    # 计算相邻标点间距
    intervals = []
    prev = -1
    for pos in punct_positions:
        gap = pos - prev
        if gap > 0:
            intervals.append(gap)
        prev = pos
    if len(intervals) < 2:
        return 0
    mean_i = sum(intervals) / len(intervals)
    if mean_i == 0:
        return 0
    var_i = sum((g - mean_i) ** 2 for g in intervals) / len(intervals)
    std_i = math.sqrt(var_i)
    return std_i / mean_i


def calc_aitext_score(text, use_aitext=False):
    """AITextDetector参考检测:7模型投票AI占比
    需要 models.json (107MB) 和 aitext_detector 包
    仅在 --aitext 模式下加载,默认不加载
    """
    if not HAS_AITEXT or not use_aitext:
        return None
    global _aitext_instance
    if _aitext_instance is None:
        if not os.path.exists(_aitext_model_path):
            return None
        _aitext_instance = _AITextDetector(_aitext_model_path)
    return _aitext_instance.detect(text)


# ============ Show Don't Tell 检测 ============

# 情绪标签模式
EMOTION_LABEL_PATTERNS = [
    re.compile(r'她感到'),
    re.compile(r'他感到'),
    re.compile(r'心中涌起'),
    re.compile(r'心中一阵'),
    re.compile(r'感到一阵'),
    re.compile(r'突然觉得'),
    re.compile(r'觉得一阵'),
    re.compile(r'内心涌起'),
    re.compile(r'心头涌起'),
    re.compile(r'心头一阵'),
]

# 思维动词
THINK_VERB_PATTERNS = [
    re.compile(r'她想到'),
    re.compile(r'他想到'),
    re.compile(r'她想着'),
    re.compile(r'他想着'),
    re.compile(r'她认为'),
    re.compile(r'他认为'),
    re.compile(r'她知道'),
    re.compile(r'他知道'),
    re.compile(r'她意识到'),
    re.compile(r'他意识到'),
]

# 滤镜词
FILTER_WORD_PATTERNS = [
    re.compile(r'她看到'),
    re.compile(r'他看到'),
    re.compile(r'她听到'),
    re.compile(r'他听到'),
    re.compile(r'她感觉到'),
    re.compile(r'他感觉到'),
    re.compile(r'她注意到'),
    re.compile(r'他注意到'),
    re.compile(r'她发现'),
    re.compile(r'他发现'),
    re.compile(r'她看见'),
    re.compile(r'他看见'),
]

# 弱化词
WEAKENING_WORDS = {
    "突然", "忽然", "非常", "十分", "极其", "相当", "颇", "甚",
    "开始", "起来", "下去", "着了",
    "really", "quite", "somewhat", "rather", "very", "suddenly",
    "began to", "started to",
}

# 场景结尾总结模式
SCENE_SUMMARY_PATTERNS = [
    re.compile(r'她知道.*再一样'),
    re.compile(r'一切都不'),
    re.compile(r'从此.*不同'),
    re.compile(r'这个夜晚.*漫长'),
    re.compile(r'她明白.*改变'),
    re.compile(r'一切.*开始了'),
]


def calc_telling_density(text):
    """Show Don't Tell检测:5类Telling密度
    返回: (telling总数, 各类计数dict, 密度)
    """
    sentences = split_sentences(text)
    total_sentences = len(sentences)
    if total_sentences == 0:
        return 0, {}, 0.0

    all_text = text
    emotion_labels = sum(len(p.findall(all_text)) for p in EMOTION_LABEL_PATTERNS)
    think_verbs = sum(len(p.findall(all_text)) for p in THINK_VERB_PATTERNS)
    filter_words = sum(len(p.findall(all_text)) for p in FILTER_WORD_PATTERNS)
    scene_summaries = sum(len(p.findall(all_text)) for p in SCENE_SUMMARY_PATTERNS)

    clean = re.sub(r'[\s\n]+', '', text)
    tokens = jieba.cut(clean) if HAS_JIEBA else list(clean)
    weakening = sum(1 for w in tokens if w in WEAKENING_WORDS)

    counts = {
        "emotion_label": emotion_labels,
        "think_verb": think_verbs,
        "filter_word": filter_words,
        "weakening": weakening,
        "scene_summary": scene_summaries,
    }
    total = sum(counts.values())
    density = total / total_sentences if total_sentences > 0 else 0
    return total, counts, round(density, 3)


def calc_concreteness_score(text):
    """具体度评分:具体名词>抽象名词>通用词
    返回: 0-10分, 10=高度具体
    """
    if not HAS_JIEBA:
        return -1
    clean = re.sub(r'[\s\n]+', '', text)
    words = [w for w in jieba.cut(clean) if len(w) >= 2 and not re.match(r'^[\W_]+$', w)]
    if not words:
        return -1

    concrete = sum(1 for w in words if w in SENSORY_WORDS)
    abstract = sum(1 for w in words if w in VAGUE_EMOTION_WORDS)

    concrete_ratio = concrete / len(words) if words else 0
    abstract_ratio = abstract / len(words) if words else 0

    score = concrete_ratio * 100 - abstract_ratio * 50
    return round(max(0, min(10, score)), 1)


# ============ AI模式检测 (来源: web-novel-writing-skill MIT + writers-second-brain Apache 2.0) ============

# AI典型词汇(正则,用于子串匹配)
AI_PATTERN_REGEXES = [
    # 词汇层面:哲学废话
    re.compile(r'在这个世界上'),
    re.compile(r'不禁让人想起'),
    re.compile(r'仿佛在诉说着什么'),
    re.compile(r'这一刻，?时间仿佛静止'),
    re.compile(r'命运的齿轮开始转动'),
    re.compile(r'在历史的长河中'),
    # 词汇层面:过度总结
    re.compile(r'总而言之'),
    re.compile(r'综上所述'),
    re.compile(r'不得不说'),
    re.compile(r'值得一提的是'),
    re.compile(r'毫无疑问'),
    # 词汇层面:情感过度
    re.compile(r'内心深处涌起一股难以名状的感觉'),
    re.compile(r'复杂的情感在心中交织'),
    re.compile(r'百感交集'),
    re.compile(r'一种说不清道不明的情绪'),
    # 词汇层面:AI万能公式
    re.compile(r'一股.*?涌上心头'),
    re.compile(r'一股.*?涌遍全身'),
    re.compile(r'心中暗道'),
    re.compile(r'暗自想道'),
    re.compile(r'嘴角微微上扬'),
    re.compile(r'目光如炬'),
    re.compile(r'浑身一震'),
    re.compile(r'倒吸一口凉气'),
    # 词汇层面:限用词(每章>1次即标记)
    re.compile(r'不禁'),
    re.compile(r'竟然'),
    re.compile(r'居然'),
    # 句式层面:万能开头
    re.compile(r'随着.+?的.+?，.+?也'),
    re.compile(r'他不知道的是'),
    re.compile(r'如果.+?知道.+?的话，?一定'),
    re.compile(r'仿佛.+?一般'),
    re.compile(r'.+?的.+?，如同.+?一般'),
    # 叙事层面:总结式叙事
    re.compile(r'经过.+?的(苦修|努力|修炼|修炼).+?，.+?有了很大提升'),
    re.compile(r'时光飞逝'),
    re.compile(r'岁月如梭'),
    re.compile(r'这就是.+?的世界吗'),
    re.compile(r'果然，?强者的世界不同凡响'),
]

# AI典型叙事模式(正则)
AI_NARRATIVE_REGEXES = [
    re.compile(r'他感到(非常)?(愤怒|开心|悲伤|害怕|恐惧|高兴|难过|失望)'),
    re.compile(r'她感到(非常)?(愤怒|开心|悲伤|害怕|恐惧|高兴|难过|失望)'),
    re.compile(r'他(她)的(心|内心)(充满了|充斥着)(愤怒|悲伤|快乐|恐惧)'),
    re.compile(r'(不禁)让人(感到|觉得)(震撼|惊叹|唏嘘)'),
]


def calc_ai_pattern_density(text):
    """AI模式检测:基于反AI模式清单检测AI典型写作模式
    来源: web-novel-writing-skill (MIT) + writers-second-brain (Apache 2.0)

    返回: (总命中数, 各类命中dict, 密度, 命中详情列表)
    """
    sentences = split_sentences(text)
    total_sentences = len(sentences)
    if total_sentences == 0:
        return 0, {}, 0.0, []

    all_text = text
    hits = []

    # 检测AI典型词汇和句式
    vocab_hits = 0
    for pattern in AI_PATTERN_REGEXES:
        matches = pattern.findall(all_text)
        for m in matches:
            vocab_hits += 1
            hit_text = m if isinstance(m, str) else m[0] if isinstance(m, tuple) else str(m)
            hits.append(("词汇/句式", pattern.pattern[:30], hit_text[:40]))

    # 检测AI典型叙事
    narrative_hits = 0
    for pattern in AI_NARRATIVE_REGEXES:
        matches = pattern.findall(all_text)
        for m in matches:
            narrative_hits += 1
            hit_text = m if isinstance(m, str) else m[0] if isinstance(m, tuple) else str(m)
            hits.append(("叙事模式", pattern.pattern[:30], hit_text[:40]))

    # 检测连续代词开头(段落起手式雷同)
    paragraphs = split_paragraphs(text)
    pronoun_starts = 0
    for i in range(len(paragraphs) - 2):
        p1, p2, p3 = paragraphs[i], paragraphs[i+1], paragraphs[i+2]
        s1 = p1[:2] if len(p1) >= 2 else p1
        s2 = p2[:2] if len(p2) >= 2 else p2
        s3 = p3[:2] if len(p3) >= 2 else p3
        if s1 == s2 == s3 and s1 in ('他', '她', '我', '它'):
            pronoun_starts += 1
            hits.append(("段落起手雷同", "连续3段同代词开头", f"{s1}..."))

    # 检测形容词堆砌(连续3+形容词修饰同一名词)
    adj_stacking = len(re.findall(r'[大到小美丽动人令人心醉的]{2,}', all_text))
    if adj_stacking > 0:
        hits.append(("形容词堆砌", "3+形容词连续", f"命中{adj_stacking}处"))

    counts = {
        "vocab_sentence": vocab_hits,
        "narrative": narrative_hits,
        "pronoun_start": pronoun_starts,
        "adj_stacking": adj_stacking,
    }
    total = sum(counts.values())
    density = total / total_sentences if total_sentences > 0 else 0
    return total, counts, round(density, 3), hits


# ============ 门限判定 ============

THRESHOLDS = {
    # === 硬门禁指标(纯统计,不依赖词库) ===
    "sigma2":        {"min": 8,     "ai": "<5",     "human": ">10"},
    "ttr":           {"min": 0.40, "ai": "<0.30",  "human": ">0.48"},
    "psigma2":       {"min": 20,   "ai": "<12",    "human": ">28"},
    "burst_cv":      {"min": 0.40, "ai": "<0.30",  "human": ">0.50"},
    "para_cv":       {"min": 0.30, "ai": "<0.20",  "human": ">0.40"},
    "ngram3_rep":    {"max": 0.08, "ai": ">0.10",  "human": "<0.06"},
    "ngram3_uniq":   {"min": 0.85, "ai": "<0.70",  "human": ">0.90"},
    # === 参考指标(不做硬门禁,仅预警) ===
    "egr":           {"max": 2.0,  "ai": ">5.0",   "human": "<1.0",  "reference": True},
    "csigma2":       {"min": 0.15, "ai": "<0.05",  "human": ">0.25", "reference": True},
    "isigma2":       {"min": 1.8,  "ai": "<1.0",   "human": ">2.5",  "reference": True},
    "dialog_ratio":  {"min": 0.05, "max": 0.65, "reference": True},
    "punct_cv":      {"min": 0.30, "reference": True},
    "telling_total": {"max": 5,    "ai": ">10",    "human": "<3",    "reference": True},
    "telling_density": {"max": 0.15, "ai": ">0.25", "human": "<0.08", "reference": True},
    "concreteness":  {"min": 1.0, "ai": "<0.5",   "human": ">2.0",  "reference": True},
    "ai_pattern_total":   {"max": 3,    "ai": ">8",     "human": "<2",  "reference": True},
    "ai_pattern_density": {"max": 0.05, "ai": ">0.15",  "human": "<0.03", "reference": True},
    # === 其他指标 ===
    "fp":            {"min": 2,    "ai": "=0",     "human": ">3"},
    "sc":            {"min": 0.75, "ai": "<0.6",   "human": ">0.85"},
}


def check_threshold(name, value):
    """检查指标是否达标,返回 (通过, 状态)
    参考指标(reference)始终通过,仅显示状态
    范围型指标(min+max)需同时满足上下限
    """
    t = THRESHOLDS.get(name)
    if not t:
        return True, "未知指标"

    is_reference = t.get("reference", False)

    # 范围型指标(如dialog_ratio: 5%-65%)
    if "min" in t and "max" in t:
        if t["min"] <= value <= t["max"]:
            return True, "✅ 正常区间" if not is_reference else "ℹ️ 正常"
        elif value < t["min"]:
            return not is_reference, "⚠️ 偏低" if not is_reference else "ℹ️ 偏低"
        else:
            return not is_reference, "⚠️ 偏高" if not is_reference else "ℹ️ 偏高"

    # min 型指标
    if "min" in t:
        if value >= t["min"]:
            if "human" in t and value >= float(t["human"].lstrip(">")):
                return True, "✅ 人写区间"
            return True, "✅ 达标"
        elif "ai" in t and value < float(t["ai"].lstrip("<").lstrip("=")):
            return False if not is_reference else True, "❌ AI区间" if not is_reference else "⚠️ AI区间(参考)"
        else:
            return False if not is_reference else True, "⚠️ 临界" if not is_reference else "⚠️ 临界(参考)"

    # max 型指标(如egr, ngram3_rep)
    if "max" in t:
        if value <= t["max"]:
            if "human" in t and value <= float(t["human"].lstrip("<")):
                return True, "✅ 人写区间"
            return True, "✅ 达标"
        elif "ai" in t and value > float(t["ai"].lstrip(">")):
            return False if not is_reference else True, "❌ AI区间" if not is_reference else "⚠️ AI区间(参考)"
        else:
            return False if not is_reference else True, "⚠️ 临界" if not is_reference else "⚠️ 临界(参考)"

    return True, "未知"


# ============ 纠正建议 ============

CORRECTIONS = {
    "sigma2":      "σ²<8 → 句式过于单调:插入短句(3-5字)打断节奏,或将长句拆为两句,制造长短句交替",
    "ttr":         "TTR<0.40 → 用词过于集中:替换高频词的30%为同义词,加入个人习惯用语",
    "psigma2":     "Pσ²<20 → 段落过于均匀:合并或拆分段落,制造长短段交替,优化手机阅读体验",
    "burst_cv":    "BurstCV<0.40 → 句式波动不足:AI文本句长过于均匀,插入极短句(2-4字)和长句交替",
    "para_cv":     "ParaCV<0.30 → 段落节奏均匀:AI文本段长过于统一,制造长短段差异(1行段+5行段交替)",
    "ngram3_rep":  "3gramRep>8% → 短语重复过多:AI倾向复用相同结构,替换重复短语的表达方式",
    "ngram3_uniq": "3gramUniq<85% → 3-gram唯一率低:AI文本短语多样性不足,增加句式和用词变化",
    "egr":         "EGR>2.0 → 情感笼统(参考):将笼统词替换为具体感官描写,此指标仅供参考不做硬门禁",
    "csigma2":     "Cσ²<0.15 → 过渡词分布均匀(参考):此指标仅供参考,不做硬门禁",
    "isigma2":     "Iσ²<1.8 → 信息密度均匀(参考):此指标仅供参考,不做硬门禁",
    "dialog_ratio":"对话占比异常(参考):正常范围5%-65%,过高或过低都需检查叙事结构",
    "punct_cv":    "标点节奏CV低(参考):AI标点间距过于均匀,变化标点使用节奏",
    "telling_total": "Telling总数>5(参考):Show Don't Tell违规过多,将情绪标签改为身体反应,删除滤镜词",
    "telling_density": "Telling密度>15%(参考):AI典型写法密度过高,参考R1-R5约束改写",
    "concreteness": "具体度<1.0(参考):抽象词过多,增加具体名词和感官细节",
    "ai_pattern_total":   "AI模式总数>3(参考):检测到AI典型写法,参考anti-ai-patterns.md改写",
    "ai_pattern_density": "AI模式密度>5%(参考):AI写法密度过高,参考Humanizer管道3-Pass去AI化",

    "fp":          "FP<2 → 缺个人指纹:植入口头禅/标志性动作,每章至少2次",
    "sc":          "SC<0.75 → 文风漂移:识别漂移最大的章节,以稳定章节为基准重写",
}


# ============ 主函数 ============

def analyze(text, fingerprint=None, use_aitext=False):
    """分析文本,返回完整报告"""
    sentences = split_sentences(text)
    paragraphs = split_paragraphs(text)

    sigma2 = calc_sentence_length_variance(sentences)
    ttr = calc_ttr(text)
    egr = calc_egr(text)
    psigma2 = calc_paragraph_length_variance(paragraphs)
    csigma2 = calc_transition_density_variance(paragraphs)
    isigma2 = calc_info_density_variance(paragraphs)

    burst_cv = calc_burstiness_cv(sentences)
    para_cv = calc_paragraph_cv(paragraphs)
    ngram3_rep, ngram3_uniq = calc_ngram_repetition(text, n=3)
    dialog_ratio = calc_dialogue_ratio(text)
    punct_cv = calc_punctuation_rhythm_cv(text)
    telling_total, telling_counts, telling_density = calc_telling_density(text)
    concreteness = calc_concreteness_score(text)
    ai_pattern_total, ai_pattern_counts, ai_pattern_density, ai_pattern_hits = calc_ai_pattern_density(text)

    result = {
        "char_count": len(text),
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
        "metrics": {
            "sigma2":      round(sigma2, 1),
            "ttr":         round(ttr, 3),
            "psigma2":     round(psigma2, 1),
            "burst_cv":    round(burst_cv, 3),
            "para_cv":     round(para_cv, 3),
            "ngram3_rep":  round(ngram3_rep, 4),
            "ngram3_uniq": round(ngram3_uniq, 4),
            "egr":         round(egr, 2),
            "csigma2":     round(csigma2, 2),
            "isigma2":     round(isigma2, 2),
            "dialog_ratio": round(dialog_ratio, 3),
            "punct_cv":    round(punct_cv, 3),
            "telling_total": telling_total,
            "telling_density": telling_density,
            "telling_breakdown": telling_counts,
            "concreteness": concreteness,
            "ai_pattern_total": ai_pattern_total,
            "ai_pattern_density": ai_pattern_density,
            "ai_pattern_breakdown": ai_pattern_counts,
            "ai_pattern_hits": ai_pattern_hits,
        },
        "thresholds": THRESHOLDS,
        "checks": {},
        "corrections": [],
    }

    # 硬门禁指标(不通过则拒绝)
    hard_gates = ["sigma2", "ttr", "psigma2", "burst_cv", "para_cv", "ngram3_rep", "ngram3_uniq"]
    for name in hard_gates:
        value = result["metrics"][name]
        passed, status = check_threshold(name, value)
        result["checks"][name] = {"value": value, "status": status, "passed": passed}
        if not passed:
            result["corrections"].append(CORRECTIONS.get(name, ""))

    # 参考指标(仅预警,不拒绝)
    reference_metrics = ["egr", "csigma2", "isigma2", "dialog_ratio", "punct_cv", "telling_total", "telling_density", "concreteness", "ai_pattern_total", "ai_pattern_density"]
    for name in reference_metrics:
        value = result["metrics"][name]
        passed, status = check_threshold(name, value)
        result["checks"][name] = {"value": value, "status": status, "passed": passed, "reference": True}
        if not passed and "ai" in THRESHOLDS.get(name, {}):
            result["corrections"].append(CORRECTIONS.get(name, ""))

    # AITextDetector参考检测(可选,需要--aitext模式)
    if use_aitext:
        aitext_result = calc_aitext_score(text, use_aitext=True)
        if aitext_result:
            result["checks"]["aitext"] = {
                "value": aitext_result.get("ai_percent", 0),
                "status": "✅ 人写" if aitext_result["verdict"] == "human" else ("⚠️ 可能AI(参考)" if "maybe" in aitext_result["verdict"] else "❌ AI(参考)"),
                "passed": aitext_result["verdict"] == "human",
                "reference": True,
                "detail": f"{aitext_result['ai_chunk_count']}/{aitext_result['chunk_count']}句被标记",
            }
            result["metrics"]["aitext_ai_percent"] = aitext_result.get("ai_percent", 0)
            result["metrics"]["aitext_verdict"] = aitext_result["verdict"]

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
    lines.append("=" * 60)
    lines.append("人写特征度量报告")
    lines.append("=" * 60)
    lines.append(f"字数: {result['char_count']}  句数: {result['sentence_count']}  段数: {result['paragraph_count']}")
    lines.append("")

    lines.append("【硬门禁指标】(不通过则拒绝入库)")
    hard_gates = ["sigma2", "ttr", "psigma2", "burst_cv", "para_cv", "ngram3_rep", "ngram3_uniq"]
    labels = {
        "sigma2": "σ²(句长方差)", "ttr": "TTR(用词多样性)", "psigma2": "Pσ²(段长方差)",
        "burst_cv": "BurstCV(句长变异系数)", "para_cv": "ParaCV(段长变异系数)",
        "ngram3_rep": "3gramRep(重复率)", "ngram3_uniq": "3gramUniq(唯一率)",
    }
    for name in hard_gates:
        if name in result["checks"]:
            c = result["checks"][name]
            label = labels.get(name, name)
            lines.append(f"  {c['status']}  {label:24s} = {c['value']}")
    lines.append("")

    lines.append("【参考指标】(仅预警,不做硬门禁)")
    ref_metrics = ["egr", "csigma2", "isigma2", "dialog_ratio", "punct_cv", "telling_total", "telling_density", "concreteness", "ai_pattern_total", "ai_pattern_density"]
    ref_labels = {
        "egr": "EGR(情感颗粒度)", "csigma2": "Cσ²(过渡词方差)",
        "isigma2": "Iσ²(信息密度方差)", "dialog_ratio": "对话占比",
        "punct_cv": "标点节奏CV",
        "telling_total": "Telling总数(Show&Tell)", "telling_density": "Telling密度",
        "concreteness": "具体度评分",
        "ai_pattern_total": "AI模式总数(反AI检测)", "ai_pattern_density": "AI模式密度",
    }
    for name in ref_metrics:
        if name in result["checks"]:
            c = result["checks"][name]
            label = ref_labels.get(name, name)
            lines.append(f"  {c['status']}  {label:24s} = {c['value']}")
    if "aitext" in result["checks"]:
        c = result["checks"]["aitext"]
        lines.append(f"  {c['status']}  {'AITextDetector(AI占比)':24s} = {c['value']}%  {c.get('detail','')}")
    lines.append("")

    # AI模式命中详情
    if "ai_pattern_total" in result.get("checks", {}) and result["checks"]["ai_pattern_total"]["value"] > 0:
        lines.append("【AI模式命中详情】(参考anti-ai-patterns.md)")
        hits = result["metrics"].get("ai_pattern_hits", [])
        for h_type, h_pattern, h_text in hits[:10]:
            lines.append(f"  • [{h_type}] {h_text}")
        if len(hits) > 10:
            lines.append(f"  ... 还有{len(hits)-10}处")
        lines.append("")

    if "fp" in result["checks"]:
        c = result["checks"]["fp"]
        lines.append("【语言指纹】")
        lines.append(f"  {c['status']}  FP(指纹匹配)              = {c['value']}次")
        if c.get("hits"):
            for phrase, cnt in c["hits"].items():
                lines.append(f"           命中: \"{phrase}\" x{cnt}")
        lines.append("")

    # 统计硬门禁通过情况
    hard_pass = sum(1 for n in hard_gates if n in result["checks"] and result["checks"][n]["passed"])
    hard_total = sum(1 for n in hard_gates if n in result["checks"])

    if result["corrections"]:
        lines.append("【纠正建议】")
        for i, corr in enumerate(result["corrections"], 1):
            if corr:
                lines.append(f"  {i}. {corr}")
        lines.append("")
        lines.append(f"硬门禁通过: {hard_pass}/{hard_total}")
        if hard_pass < hard_total:
            lines.append(f"❌ {hard_total - hard_pass}项硬门禁未通过,需重写")
        else:
            lines.append("✅ 硬门禁全部通过(参考指标有预警)")
    else:
        lines.append(f"【结论】硬门禁 {hard_pass}/{hard_total} 全部通过,可以入库。")

    lines.append("=" * 60)
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

    # BurstCV 对比:差值<0.2 达标
    diff_burst = abs(ma["burst_cv"] - mb["burst_cv"])
    comparison["diff"]["burst_cv"] = round(diff_burst, 3)
    if diff_burst < 0.2:
        comparison["evaluation"]["burst_cv"] = "✅ 达标"
    elif diff_burst < 0.3:
        comparison["evaluation"]["burst_cv"] = "⚠️ 临界"
        comparison["score"] -= 10
    else:
        comparison["evaluation"]["burst_cv"] = "❌ 句式波动差异大"
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
        ("BurstCV","burst_cv","abs_diff"),
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
            diff_val = comparison["diff"].get(key, 0)
            if key in ("burst_cv",):
                diff_str = f"{diff_val:.3f}"
            else:
                diff_str = f"{diff_val:.1f}"
        eval_str = comparison["evaluation"].get(key, "")
        lines.append(f"{label:8s}  {va:10.3f}  {vb:10.3f}  {diff_str:>10s}  {eval_str}")

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
    for key in ["sigma2", "ttr", "burst_cv", "psigma2"]:
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
            if key == "burst_cv" and slope < -0.02:
                issues.append({
                    "type": "burst_cv_declining",
                    "detail": f"BurstCV 持续下降(斜率{slope:.2f}),句式波动减弱,趋于AI化",
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
        ("长短交替", "刻意制造3字短句和30字长句交替,提升BurstCV"),
        ("段落重组", "合并短段或拆分长段,制造长短段交替,提升P\u03c3\u00b2"),
    ],
    "burst_cv_declining": [
        ("短句穿插", "在长段中插入2-4字极短句,提升句式波动"),
        ("长短交替", "刻意制造3字短句和30字长句的交替节奏"),
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
    use_aitext = "--aitext" in sys.argv

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
        result = analyze(text_a, fingerprint, use_aitext=use_aitext)
        if output_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_report(result))


if __name__ == "__main__":
    main()
