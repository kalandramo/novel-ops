# -*- coding: utf-8 -*-
"""测试: 从AITextDetector模型中提取句子级特征贡献度"""
import sys, os, json, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'novel-system', 'tools'))
from aitext_detector.detector import AITextDetector

det = AITextDetector(os.path.join(os.path.dirname(__file__), '..', 'novel-system', 'tools', 'aitext_detector', 'models.json'))

# 对AI句做特征贡献度分析
test_sentences = [
    "她看着眼前的熟悉景象，心中涌起一阵复杂的情绪。",
    "她想起了前世发生的一切，心中充满了悲伤和痛苦。",
    "她感到非常难过，同时也感到非常愤怒。",
    "她感到非常绝望和痛苦，同时也很愤怒和怨恨。",
]

for sent in test_sentences:
    clean = det._clean_chunk(sent)
    counts = det._compute_ngram_counts(clean)

    # 对每个模型,找出贡献最大的n-gram
    print('=' * 60)
    print('句子: {}'.format(sent))
    print('清洗后: {} ({})'.format(clean[:40], len(clean)))

    ai_models, model_scores = det._classify_chunk(clean, counts)
    print('AI模型: {}  票数: {}'.format(ai_models, len(ai_models)))
    print()

    # 分析7个模型的top贡献n-gram
    all_top_grams = {}
    for name in ['gemini', 'qwen', 'pony', 'kimi25', 'glm47', 'doubao', 'deepseekv32']:
        model = det.models[name]
        weights = model['weights']
        intercept = model['intercept']

        contributions = []
        for gram, count in counts.items():
            w = weights.get(gram)
            if w is not None:
                tf = 1.0 + math.log(count)
                combined = w[0]
                idf = w[1]
                contrib = tf * combined  # 正=推向AI, 负=推向人写
                contributions.append((gram, contrib, tf * idf))

        # 按绝对值排序,看top贡献
        contributions.sort(key=lambda x: abs(x[1]), reverse=True)
        top5 = contributions[:5]

        if name in ai_models:
            print('  [{}] 判定AI (score={:.3f})'.format(name, model_scores[name]))
            for gram, contrib, norm in top5:
                direction = 'AI++' if contrib > 0 else '人写++'
                print('    {} {:>8s}  contrib={:+.3f}  ({})'.format(direction, gram, contrib, ' '.join(gram)))
        else:
            if model_scores.get(name, 0) < 0:
                print('  [{}] 判定人写 (score={:.3f})'.format(name, model_scores[name]))
    print()
