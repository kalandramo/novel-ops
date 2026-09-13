# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'novel-system', 'tools'))
from aitext_detector.detector import AITextDetector, format_result

det = AITextDetector(os.path.join(os.path.dirname(__file__), '..', 'novel-system', 'tools', 'aitext_detector', 'models.json'))

samples = [
    ('攻玉(晋江)', 'samples/human_jjwxc_gongyu_ch1.txt'),
    ('长安食话(番茄)', 'samples/human_fanqie_changanshihua_ch1.txt'),
    ('太傅(晋江)', 'samples/human_jjwxc_taifu_ch1.txt'),
    ('AI对照', 'samples/ai_generated_control.txt'),
]

for name, path in samples:
    full = os.path.join(os.path.dirname(__file__), '..', path) if not os.path.isabs(path) else path
    text = open(full, encoding='utf-8').read()
    r = det.detect(text)
    print(f"\n{'='*60}")
    print(f"样本: {name}")
    print(f"判定: {r['verdict']}  AI占比: {r['ai_percent']}%  AI句: {r['ai_chunk_count']}/{r['chunk_count']}")
    ai_chunks = [c for c in r['ai_models_per_chunk'] if c['is_ai']]
    if ai_chunks:
        print(f"被标记为AI的句子(前3条):")
        for i, c in enumerate(ai_chunks[:3]):
            models = ', '.join(c['ai_models'])
            print(f"  {i+1}. [{models}] {c['text']}")
