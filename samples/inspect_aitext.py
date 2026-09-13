# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'novel-system', 'tools'))
from aitext_detector.detector import AITextDetector

det = AITextDetector(os.path.join(os.path.dirname(__file__), '..', 'novel-system', 'tools', 'aitext_detector', 'models.json'))

# 用AI对照样本看详细输出
text = open(os.path.join(os.path.dirname(__file__), 'ai_generated_control.txt'), encoding='utf-8').read()
r = det.detect(text)

print('=== AI对照样本 chunk详情 ===')
for i, c in enumerate(r['ai_models_per_chunk'][:8]):
    print('Chunk {}:'.format(i+1))
    print('  text: {}'.format(c['text']))
    print('  clean_len: {}'.format(c['clean_len']))
    print('  is_ai: {}'.format(c['is_ai']))
    print('  ai_model_count: {}'.format(c['ai_model_count']))
    print('  ai_models: {}'.format(c['ai_models']))
    print()

# 也看看人写样本被标记的chunk
print('\n=== 长安食话 被标记为AI的chunk详情(前3条) ===')
text2 = open(os.path.join(os.path.dirname(__file__), 'human_fanqie_changanshihua_ch1.txt'), encoding='utf-8').read()
r2 = det.detect(text2)
ai_chunks = [c for c in r2['ai_models_per_chunk'] if c['is_ai']]
for i, c in enumerate(ai_chunks[:3]):
    print('Chunk {}:'.format(i+1))
    print('  text: {}'.format(c['text']))
    print('  ai_models: {}'.format(c['ai_models']))
    print()
