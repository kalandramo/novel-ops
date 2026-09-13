# -*- coding: utf-8 -*-
"""
Synthetic test: generate text with known sentence/paragraph lengths
to verify theoretical bounds and find what's needed to hit thresholds.
"""
import math

def make_sentence(length):
    """Create a Chinese sentence of exactly N chars (plus a period)."""
    # Use repeated characters to reach exact length
    if length <= 2:
        return "她" * length
    return "她" + "走走停停看看想想说说笑笑" * ((length - 1) // 10 + 1)
    # We'll trim below

def make_text(sentence_lengths):
    """Create text where each sentence has the specified char length."""
    sentences = []
    for sl in sentence_lengths:
        # Create a sentence of exactly sl chars (without punctuation)
        if sl <= 2:
            s = "她" * sl
        else:
            base = "她走在街道上看着窗外的灯光和行人的影子"
            s = (base * (sl // len(base) + 1))[:sl]
        sentences.append(s + "。")
    return "".join(sentences)

def compute_sigma2(sentence_lengths):
    """Compute standard deviation of sentence lengths."""
    n = len(sentence_lengths)
    if n == 0:
        return 0
    mean = sum(sentence_lengths) / n
    var = sum((l - mean) ** 2 for l in sentence_lengths) / n
    return math.sqrt(var)

def compute_psigma2(para_lengths):
    """Compute standard deviation of paragraph lengths."""
    return compute_sigma2(para_lengths)  # same formula

print("=" * 70)
print("SYNTHETIC TEST: Known sentence/paragraph lengths")
print("=" * 70)

# Test 1: What sigma2 does a realistic varied chapter produce?
print("\n--- Test 1: Realistic varied sentence lengths ---")
# Simulating real novel: mix of short dialogue, medium narrative, long descriptive
realistic = [3, 4, 5, 5, 6, 7, 8, 8, 9, 10,  # 10 short
             12, 14, 15, 16, 18, 19, 20, 22, 24, 25,  # 10 medium
             28, 30, 35, 38, 40, 42, 45, 48, 50, 55,   # 10 long
             3, 5, 8, 12, 15, 18, 22, 28, 35, 40,     # 10 mixed
             3, 4, 6, 10, 14, 18, 25, 32, 40, 48,      # 10 mixed
             3, 5, 8, 12, 16, 20, 28, 35, 42, 50,      # 10 mixed
             3, 4, 6, 10, 15, 22, 30, 38, 45, 55,      # 10 mixed
             3, 5, 7, 12, 18, 25, 33, 40, 48, 52]      # 10 mixed
total_chars = sum(realistic)
print(f"  70 sentences, {total_chars} chars, mean={total_chars/70:.1f}")
print(f"  Range: {min(realistic)}-{max(realistic)} chars")
print(f"  sigma2 = {compute_sigma2(realistic):.1f}")
print(f"  Set A (>=25): {'PASS' if compute_sigma2(realistic) >= 25 else 'FAIL'}")
print(f"  Set B (>=120): {'PASS' if compute_sigma2(realistic) >= 120 else 'FAIL'}")

# Test 2: Push to sigma2=25
print("\n--- Test 2: Pushing to sigma2=25 ---")
# Need 65 short(3ch) + 15 long(67ch) = 195 + 1005 = 1200
test2 = [3] * 65 + [67] * 15
total2 = sum(test2)
print(f"  80 sentences: 65x(3ch) + 15x(67ch) = {total2} chars")
print(f"  sigma2 = {compute_sigma2(test2):.1f}")
print(f"  Set A (>=25): {'PASS' if compute_sigma2(test2) >= 25 else 'FAIL'}")

# Test 3: What's needed for sigma2=120?
print("\n--- Test 3: Pushing to sigma2=120 ---")
# Need nearly all text in one sentence
# 79 short(2ch) + 1 long(1042ch) = 158 + 1042 = 1200
test3 = [2] * 79 + [1042]
total3 = sum(test3)
print(f"  80 sentences: 79x(2ch) + 1x(1042ch) = {total3} chars")
print(f"  sigma2 = {compute_sigma2(test3):.1f}")
print(f"  Set B (>=120): {'PASS' if compute_sigma2(test3) >= 120 else 'FAIL'}")
print(f"  NOTE: The 1042-char 'sentence' = {1042/1200*100:.1f}% of the chapter!")

# Test 4: Realistic paragraph lengths
print("\n--- Test 4: Realistic varied paragraph lengths ---")
realistic_p = [20, 25, 30, 45, 55, 60, 70, 80, 85, 90,
               100, 110, 120, 130, 140, 150, 160, 170, 180, 200]
total_p = sum(realistic_p)
print(f"  20 paragraphs, {total_p} chars, mean={total_p/20:.1f}")
print(f"  Range: {min(realistic_p)}-{max(realistic_p)} chars")
print(f"  psigma2 = {compute_psigma2(realistic_p):.1f}")
print(f"  Set A (>=80): {'PASS' if compute_psigma2(realistic_p) >= 80 else 'FAIL'}")
print(f"  Set B (>=300): {'PASS' if compute_psigma2(realistic_p) >= 300 else 'FAIL'}")

# Test 5: Push to psigma2=80
print("\n--- Test 5: Pushing to psigma2=80 ---")
# 9 short(15ch) + 6 long(178ch) = 135 + 1068 = 1203 (close to 1200)
test5 = [15] * 9 + [178] * 6
total5 = sum(test5)
print(f"  15 paragraphs: 9x(15ch) + 6x(178ch) = {total5} chars")
print(f"  psigma2 = {compute_psigma2(test5):.1f}")
print(f"  Set A (>=80): {'PASS' if compute_psigma2(test5) >= 80 else 'FAIL'}")

# Test 6: What's needed for psigma2=300?
print("\n--- Test 6: Pushing to psigma2=300 ---")
# 14 short(1ch) + 1 long(1186ch) = 14 + 1186 = 1200
test6 = [1] * 14 + [1186]
total6 = sum(test6)
print(f"  15 paragraphs: 14x(1ch) + 1x(1186ch) = {total6} chars")
print(f"  psigma2 = {compute_psigma2(test6):.1f}")
print(f"  Set B (>=300): {'PASS' if compute_psigma2(test6) >= 300 else 'FAIL'}")
print(f"  NOTE: The 1186-char paragraph = {1186/1200*100:.1f}% of the chapter!")

# Test 7: Can we reach psigma2=300 with more paragraphs (20)?
print("\n--- Test 7: psigma2=300 with 20 paragraphs ---")
# Max sigma with 20 paras: 19x(1ch) + 1x(1181ch)
test7 = [1] * 19 + [1181]
total7 = sum(test7)
print(f"  20 paragraphs (max): 19x(1ch) + 1x(1181ch) = {total7} chars")
print(f"  psigma2 = {compute_psigma2(test7):.1f}")
print(f"  Set B (>=300): {'PASS' if compute_psigma2(test7) >= 300 else 'FAIL'}")

# Test 8: What if we use 10 paragraphs for psigma2=300?
print("\n--- Test 8: psigma2=300 with 10 paragraphs ---")
# Max sigma with 10 paras: 9x(1ch) + 1x(1191ch)
test8 = [1] * 9 + [1191]
total8 = sum(test8)
print(f"  10 paragraphs (max): 9x(1ch) + 1x(1191ch) = {total8} chars")
print(f"  psigma2 = {compute_psigma2(test8):.1f}")
print(f"  Set B (>=300): {'PASS' if compute_psigma2(test8) >= 300 else 'FAIL'}")

# Test 9: Realistic distribution that hits psigma2=80
print("\n--- Test 9: Realistic distribution hitting psigma2=80 ---")
# Try: 10 short(20ch) + 5 long(200ch) = 200 + 1000 = 1200
test9 = [20] * 10 + [200] * 5
total9 = sum(test9)
print(f"  15 paragraphs: 10x(20ch) + 5x(200ch) = {total9} chars")
print(f"  psigma2 = {compute_psigma2(test9):.1f}")
print(f"  Set A (>=80): {'PASS' if compute_psigma2(test9) >= 80 else 'FAIL'}")

# Test 10: More realistic - some short, some medium, some long
print("\n--- Test 10: Moderate variation ---")
test10 = [15, 20, 25, 30, 40, 50, 60, 80, 100, 120,
          150, 180, 200, 250, 300]
total10 = sum(test10)
print(f"  15 paragraphs: range 15-300 chars, total={total10}")
print(f"  psigma2 = {compute_psigma2(test10):.1f}")
print(f"  Set A (>=80): {'PASS' if compute_psigma2(test10) >= 80 else 'FAIL'}")
print(f"  Set B (>=300): {'PASS' if compute_psigma2(test10) >= 300 else 'FAIL'}")

# Summary table
print("\n" + "=" * 70)
print("FEASIBILITY SUMMARY")
print("=" * 70)
print(f"\n{'Metric':<12} {'Set A':>10} {'Feasible?':>12} {'Set B':>10} {'Feasible?':>12}")
print("-" * 60)

# sigma2
s_real = compute_sigma2(realistic)
s_25 = compute_sigma2([3]*65 + [67]*15)
s_120 = compute_sigma2([2]*79 + [1042])
print(f"{'sigma2':<12} {'>=25':>10} {'YES (extreme)':>12} {'>=120':>10} {'NEAR-IMPOSSIBLE':>12}")
print(f"  Realistic chapter: sigma2={s_real:.1f}")
print(f"  Max extreme (80 sent): sigma2={s_120:.1f} (needs 87% in one sentence)")

# psigma2
p_real = compute_psigma2(realistic_p)
p_80 = compute_psigma2([20]*10 + [200]*5)
p_300 = compute_psigma2([1]*14 + [1186])
print(f"{'psigma2':<12} {'>=80':>10} {'YES (extreme)':>12} {'>=300':>10} {'IMPOSSIBLE(15+)':>12}")
print(f"  Realistic chapter: psigma2={p_real:.1f}")
print(f"  Max extreme (15 para): psigma2={p_300:.1f} (needs 99% in one paragraph)")

# TTR
print(f"{'TTR':<12} {'>=0.25':>10} {'YES (trivial)':>12} {'>=0.48':>10} {'YES (normal)':>12}")
print(f"  Empirical test: TTR=0.543 (normal chapter), TTR=0.628 (varied)")

# EGR
print(f"{'EGR':<12} {'<=0.60':>10} {'YES (strict)':>12} {'<=2.0':>10} {'YES (lenient)':>12}")
print(f"  Empirical test: EGR=0.60 (normal), EGR=0.25 (sensory-rich)")
