# -*- coding: utf-8 -*-
"""
AITextDetector 本地推理引擎
基于 lyc8503/AITextDetector 的 models.json 格式,纯Python实现,无需scikit-learn

用法:
  from aitext_detector.detector import AITextDetector
  det = AITextDetector()
  det.load("models.json")
  result = det.detect("要检测的中文文本...")
  print(result)

  # 或直接命令行:
  python detector.py 文章.txt
  python detector.py 文章.txt --json

依赖:
  无第三方依赖,纯标准库

原理:
  1. 按句号/问号/感叹号/分号分句
  2. 清洗:只保留中文+英文+基本标点
  3. 对每句计算 char 2-5gram
  4. 用7个LinearSVC模型投票(≥2个模型判定→该句为AI)
  5. 统计全文AI句占比

模型信息:
  - 训练数据: 8536篇中文网文(2022年前人写) + 7个LLM生成文本
  - 准确率: ~85% (句级)
  - 模型大小: 107MB (JSON格式)
  - License: Apache-2.0
  - 项目: https://github.com/lyc8503/AITextDetector
"""

import json
import re
import math
import os
import sys

MODEL_NAMES = ['gemini', 'qwen', 'pony', 'kimi25', 'glm47', 'doubao', 'deepseekv32']

# 清洗正则:只保留中文+英文+基本标点
CLEAN_PATTERN = re.compile(r'[^a-zA-Z0-9\n,.;?!\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]')
# 分句正则
SPLIT_PATTERN = re.compile(r'([。！？；?!\n])')


class AITextDetector:
    def __init__(self, model_path=None):
        self.models = {}
        self.loaded = False
        if model_path:
            self.load(model_path)

    def load(self, model_path=None):
        if model_path is None:
            model_path = os.path.join(os.path.dirname(__file__), 'models.json')
        with open(model_path, encoding='utf-8') as f:
            data = json.load(f)
        self.models = data
        self.loaded = True
        return self

    def _split_text(self, text):
        parts = SPLIT_PATTERN.split(text)
        chunks = []
        for i in range(0, len(parts) - 1, 2):
            chunk = parts[i]
            if i + 1 < len(parts):
                chunk += parts[i + 1]
            if chunk:
                chunks.append(chunk)
        if len(parts) % 2 == 1 and parts[-1]:
            chunks.append(parts[-1])
        return chunks

    def _clean_chunk(self, chunk):
        return CLEAN_PATTERN.sub('', chunk).strip()

    def _compute_ngram_counts(self, text):
        counts = {}
        length = len(text)
        for n in range(2, 6):
            stop = length - n + 1
            for i in range(stop):
                gram = text[i:i + n]
                counts[gram] = counts.get(gram, 0) + 1
        return counts

    def _classify_chunk(self, text, counts=None):
        if counts is None:
            counts = self._compute_ngram_counts(text)
        ai_models = []
        model_scores = {}
        for name in MODEL_NAMES:
            model = self.models.get(name)
            if not model:
                continue
            weights = model['weights']
            intercept = model['intercept']
            raw_score = 0.0
            norm_sq = 0.0
            for gram, count in counts.items():
                w = weights.get(gram)
                if w is not None:
                    tf = 1.0 + math.log(count)
                    combined = w[0]
                    idf = w[1]
                    raw_score += tf * combined
                    norm_sq += (tf * idf) ** 2
            if norm_sq < 1e-30:
                if intercept > 0:
                    ai_models.append(name)
                model_scores[name] = intercept
                continue
            decision = raw_score / math.sqrt(norm_sq) + intercept
            model_scores[name] = decision
            if decision > 0:
                ai_models.append(name)
        return ai_models, model_scores

    def detect(self, text, min_chars=5):
        if not self.loaded:
            raise RuntimeError("模型未加载,请先调用 load()")
        if len(text) < 10:
            return {
                "verdict": "too_short",
                "ai_ratio": 0,
                "ai_models_per_chunk": [],
                "chunk_count": 0,
                "ai_chunk_count": 0,
            }

        chunks = self._split_text(text)
        results = []
        ai_chunk_count = 0
        ai_char_count = 0
        total_char_count = 0

        for chunk in chunks:
            clean = self._clean_chunk(chunk)
            if len(clean) < min_chars:
                continue
            counts = self._compute_ngram_counts(clean)
            ai_models, model_scores = self._classify_chunk(clean, counts)
            is_ai = len(ai_models) >= 2
            results.append({
                "text": chunk[:50] + "..." if len(chunk) > 50 else chunk,
                "clean_len": len(clean),
                "is_ai": is_ai,
                "ai_model_count": len(ai_models),
                "ai_models": ai_models,
            })
            if is_ai:
                ai_chunk_count += 1
                ai_char_count += len(clean)
            total_char_count += len(clean)

        ai_ratio = ai_char_count / total_char_count if total_char_count > 0 else 0
        if ai_ratio < 0.5:
            verdict = "human"
        elif ai_ratio <= 0.7:
            verdict = "maybe_human"
        else:
            verdict = "maybe_ai"

        return {
            "verdict": verdict,
            "ai_ratio": round(ai_ratio, 4),
            "ai_percent": round(ai_ratio * 100, 1),
            "chunk_count": len(results),
            "ai_chunk_count": ai_chunk_count,
            "ai_models_per_chunk": results,
            "model_names": MODEL_NAMES,
        }


def format_result(result):
    lines = []
    lines.append("=" * 60)
    lines.append("AITextDetector 检测报告")
    lines.append("=" * 60)
    verdict_map = {
        "human": "✅ 人写",
        "maybe_human": "⚠️ 可能人写",
        "maybe_ai": "❌ 可能AI生成",
        "too_short": "⚠️ 文本太短",
    }
    lines.append(f"判定: {verdict_map.get(result['verdict'], result['verdict'])}")
    lines.append(f"AI占比: {result.get('ai_percent', 0)}%")
    lines.append(f"句子数: {result.get('chunk_count', 0)}  AI句: {result.get('ai_chunk_count', 0)}")
    lines.append("")

    if result.get("ai_models_per_chunk"):
        ai_chunks = [c for c in result["ai_models_per_chunk"] if c["is_ai"]]
        if ai_chunks:
            lines.append("【AI标记的句子】")
            for i, c in enumerate(ai_chunks[:10]):
                lines.append(f"  {i+1}. [{','.join(c['ai_models'])}] {c['text']}")
            if len(ai_chunks) > 10:
                lines.append(f"  ...还有{len(ai_chunks)-10}条")
        else:
            lines.append("【无AI标记的句子】")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("用法: python detector.py <文件.txt> [--json]")
        print("      python detector.py <文件.txt>  # 可读报告")
        print("      python detector.py <文件.txt> --json  # JSON输出")
        sys.exit(1)
    filepath = sys.argv[1]
    output_json = "--json" in sys.argv
    text = open(filepath, encoding='utf-8').read()
    model_path = os.path.join(os.path.dirname(__file__), 'models.json')
    det = AITextDetector(model_path)
    result = det.detect(text)
    if output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_result(result))


if __name__ == "__main__":
    main()
