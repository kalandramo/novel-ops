# -*- coding: utf-8 -*-
"""
Mathematical feasibility analysis for metrics thresholds.
Computes theoretical bounds for sigma2 and psigma2 given chapter constraints.
"""
import math

print("=" * 70)
print("THEORETICAL BOUNDS ANALYSIS FOR 1200-1500 CHAR CHINESE CHAPTERS")
print("=" * 70)

# ============================================================
# 1. SIGMA2 (Sentence Length Standard Deviation)
# ============================================================
print("\n" + "=" * 70)
print("1. SIGMA2: Sentence Length Standard Deviation")
print("   Code computes: sqrt(variance) = standard deviation of sentence char-lengths")
print("   Set A (code): sigma2 >= 25")
print("   Set B (docs): sigma2 >= 120")
print("=" * 70)

# Parameters
for total_chars in [1200, 1500]:
    print(f"\n--- Chapter size: {total_chars} chars ---")
    print(f"{'N_sentences':>12} {'Mean_len':>10} {'Max_sigma':>12} {'Sigma_120?':>12} {'Sigma_25?':>12}")
    print("-" * 60)

    for n_sent in [60, 70, 80, 90, 100]:
        mean_len = total_chars / n_sent

        # Maximum possible sigma: (n-1) sentences of length 2 (minimum per code),
        # 1 sentence with all remaining chars
        min_sent_len = 2  # code filters sentences with len < 2
        remaining = total_chars - (n_sent - 1) * min_sent_len
        big_sent = remaining  # one giant sentence

        # Compute sigma for this extreme distribution
        lengths = [min_sent_len] * (n_sent - 1) + [big_sent]
        mean = sum(lengths) / len(lengths)
        variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
        max_sigma = math.sqrt(variance)

        can_120 = "YES" if max_sigma >= 120 else "NO"
        can_25 = "YES" if max_sigma >= 25 else "NO"

        print(f"{n_sent:>12} {mean_len:>10.1f} {max_sigma:>12.1f} {can_120:>12} {can_25:>12}")

    # What distribution gives sigma=25? (bimodal: k short sentences + (n-k) long)
    print(f"\n   Distribution needed for sigma=25 (80 sentences, {total_chars} chars):")
    n = 80
    mean = total_chars / n
    # Try: x short sentences of length a, (n-x) long sentences of length b
    # x*a + (n-x)*b = total_chars
    # variance = [x*(a-mean)^2 + (n-x)*(b-mean)^2] / n
    # We want sqrt(variance) = 25, so variance = 625
    target_var = 625
    for n_short in range(10, 80, 5):
        a = 3  # short sentence length
        n_long = n - n_short
        b = (total_chars - n_short * a) / n_long
        if b < 2:
            continue
        mean_calc = (n_short * a + n_long * b) / n
        var = (n_short * (a - mean_calc) ** 2 + n_long * (b - mean_calc) ** 2) / n
        sigma = math.sqrt(var)
        if 23 <= sigma <= 27:
            print(f"   -> {n_short} short({a}ch) + {n_long} long({b:.0f}ch) => sigma={sigma:.1f}")

    # What distribution gives sigma=120?
    print(f"\n   Distribution needed for sigma=120 (80 sentences, {total_chars} chars):")
    target_var = 120 ** 2  # = 14400
    found = False
    for n_short in range(70, 80):
        a = 2
        n_long = n - n_short
        if n_long < 1:
            continue
        b = (total_chars - n_short * a) / n_long
        if b < 2:
            continue
        mean_calc = (n_short * a + n_long * b) / n
        var = (n_short * (a - mean_calc) ** 2 + n_long * (b - mean_calc) ** 2) / n
        sigma = math.sqrt(var)
        if 115 <= sigma <= 125:
            pct = b / total_chars * 100
            print(f"   -> {n_short} short({a}ch) + {n_long} long({b:.0f}ch) => sigma={sigma:.1f}")
            print(f"      The long sentence is {b:.0f} chars = {pct:.1f}% of entire chapter!")
            found = True
    if not found:
        print(f"   -> NO bimodal distribution with 80 sentences can reach sigma=120")

# ============================================================
# 2. PSIGMA2 (Paragraph Length Standard Deviation)
# ============================================================
print("\n\n" + "=" * 70)
print("2. PSIGMA2: Paragraph Length Standard Deviation")
print("   Code computes: sqrt(variance) = standard deviation of paragraph char-lengths")
print("   Set A (code): psigma2 >= 80")
print("   Set B (docs): psigma2 >= 300")
print("=" * 70)

for total_chars in [1200, 1500]:
    print(f"\n--- Chapter size: {total_chars} chars ---")
    print(f"{'N_paras':>10} {'Mean_len':>10} {'Max_sigma':>12} {'Sig_300?':>10} {'Sig_80?':>10}")
    print("-" * 55)

    for n_para in [10, 12, 15, 18, 20]:
        mean_len = total_chars / n_para
        # Max sigma: (n-1) paragraphs of 1 char, 1 with all remaining
        min_para_len = 1
        remaining = total_chars - (n_para - 1) * min_para_len
        big_para = remaining
        lengths = [min_para_len] * (n_para - 1) + [big_para]
        mean = sum(lengths) / len(lengths)
        variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
        max_sigma = math.sqrt(variance)

        can_300 = "YES" if max_sigma >= 300 else "NO"
        can_80 = "YES" if max_sigma >= 80 else "NO"
        print(f"{n_para:>10} {mean_len:>10.1f} {max_sigma:>12.1f} {can_300:>10} {can_80:>10}")

    # Distribution for sigma=80 (15 paragraphs)
    print(f"\n   Distribution for psigma2=80 (15 paragraphs, {total_chars} chars):")
    n = 15
    for n_short in range(3, 13, 2):
        a = 15  # short paragraph
        n_long = n - n_short
        b = (total_chars - n_short * a) / n_long
        if b < 2:
            continue
        mean_calc = (n_short * a + n_long * b) / n
        var = (n_short * (a - mean_calc) ** 2 + n_long * (b - mean_calc) ** 2) / n
        sigma = math.sqrt(var)
        if 75 <= sigma <= 85:
            print(f"   -> {n_short} short({a}ch) + {n_long} long({b:.0f}ch) => psigma2={sigma:.1f}")

    # Distribution for sigma=300
    print(f"\n   Distribution for psigma2=300 (15 paragraphs, {total_chars} chars):")
    found = False
    for n_short in range(10, 15):
        a = 1
        n_long = n - n_short
        if n_long < 1:
            continue
        b = (total_chars - n_short * a) / n_long
        if b < 2:
            continue
        mean_calc = (n_short * a + n_long * b) / n
        var = (n_short * (a - mean_calc) ** 2 + n_long * (b - mean_calc) ** 2) / n
        sigma = math.sqrt(var)
        if sigma >= 290:
            pct = b / total_chars * 100
            print(f"   -> {n_short} short({a}ch) + {n_long} long({b:.0f}ch) => psigma2={sigma:.1f}")
            print(f"      The long paragraph is {b:.0f} chars = {pct:.1f}% of entire chapter!")
            found = True
    if not found:
        print(f"   -> NO distribution with 15 paragraphs can reach psigma2=300")

# ============================================================
# 3. TTR Theoretical Analysis
# ============================================================
print("\n\n" + "=" * 70)
print("3. TTR: Type-Token Ratio")
print("   Code computes: unique_words / total_words (jieba tokenization)")
print("   Set A (code): TTR >= 0.25")
print("   Set B (docs): TTR >= 0.48")
print("=" * 70)

print("\n   Chinese text of 1200-1500 chars -> ~600-800 jieba tokens")
print("   (average Chinese word = 1.5-2 chars)")
print()
print("   TTR naturally decreases with length (Heaps' Law: V = K*N^beta)")
print("   For Chinese: beta ~= 0.5-0.7, K ~= 10-25")
print()
print(f"   {'N_tokens':>10} {'Heaps_V(K=15,b=0.6)':>22} {'TTR':>10} {'Pass_0.25':>12} {'Pass_0.48':>12}")
print("-" * 68)

for n_tokens in [400, 500, 600, 700, 800, 900, 1000]:
    for K, beta in [(15, 0.6), (20, 0.55), (10, 0.7)]:
        V = int(K * (n_tokens ** beta))
        V = min(V, n_tokens)  # can't exceed total
        ttr = V / n_tokens
        pass25 = "YES" if ttr >= 0.25 else "NO"
        pass48 = "YES" if ttr >= 0.48 else "NO"
        if K == 15 and beta == 0.6:
            print(f"   {n_tokens:>10} {V:>22} {ttr:>10.3f} {pass25:>12} {pass48:>12}")

print("\n   Empirical TTR ranges for Chinese text (jieba):")
print("   - 100-200 tokens (short paragraph): TTR ~ 0.60-0.75")
print("   - 500-800 tokens (chapter length):  TTR ~ 0.38-0.55")
print("   - 1000+ tokens (long text):         TTR ~ 0.30-0.45")
print()
print("   CONCLUSION:")
print("   - TTR=0.25: Technically possible but extremely low (near-repetitive text)")
print("     Only ~175 unique words in 700 tokens = massive repetition")
print("   - TTR=0.48: Within natural range for 700-token Chinese text")
print("     ~336 unique words in 700 tokens = healthy diversity")

# ============================================================
# 4. EGR Analysis
# ============================================================
print("\n\n" + "=" * 70)
print("4. EGR: Emotion Granularity Ratio")
print("   Code computes: vague_emotion_count / sensory_count (substring match)")
print("   Set A (code): EGR <= 0.60  (need 1.67x more sensory than vague)")
print("   Set B (docs): EGR <= 2.0   (need 0.5x as many sensory as vague)")
print("=" * 70)

print("\n   Word lists in code: ~80 vague emotion words, ~80 sensory words")
print("\n   For a 1200-1500 char chapter, typical word counts:")
print(f"   {'Vague':>8} {'Sensory':>10} {'EGR':>8} {'Pass_0.60':>12} {'Pass_2.0':>10}")
print("-" * 52)

for vague in range(0, 15):
    for sensory in range(0, 15):
        if sensory == 0:
            egr = vague * 10 if vague > 0 else 0
        else:
            egr = vague / sensory
        # Only print interesting cases
        if (vague in [2, 4, 6, 8, 10]) and (sensory in [0, 1, 2, 3, 4, 6, 8, 10, 12]):
            p60 = "YES" if egr <= 0.60 else "NO"
            p20 = "YES" if egr <= 2.0 else "NO"
            print(f"   {vague:>8} {sensory:>10} {egr:>8.2f} {p60:>12} {p20:>10}")

print("\n   Typical Chinese novel chapter:")
print("   - AI-like text:    5-10 vague, 0-1 sensory  -> EGR = 5.0 to INF  (fails both)")
print("   - Mediocre human:  3-6 vague, 1-3 sensory   -> EGR = 1.0 to 6.0  (passes B, fails A)")
print("   - Good human:      2-4 vague, 3-6 sensory   -> EGR = 0.3 to 1.3  (passes both)")
print("   - Excellent craft: 1-3 vague, 5-10 sensory  -> EGR = 0.1 to 0.6  (passes both)")

# ============================================================
# 5. REALISTIC EXAMPLE
# ============================================================
print("\n\n" + "=" * 70)
print("5. REALISTIC CHAPTER SIMULATION")
print("   Simulating a well-written 1350-char chapter with deliberate")
print("   long-short sentence and paragraph variation")
print("=" * 70)

# Simulate a realistic sentence length distribution
# 75 sentences, some short (3-8), some medium (12-25), some long (30-50)
import random
random.seed(42)

# Deliberately varied sentence lengths
sentence_lengths = (
    [3, 4, 5, 5, 6, 7, 7, 8] * 3 +       # 24 short sentences
    [12, 14, 15, 16, 18, 20, 22, 25] * 3 +  # 24 medium sentences
    [30, 35, 40, 45, 50, 55, 58, 62] * 3     # 24 long sentences
)
# 72 sentences, total = 24*(3+4+5+5+6+7+7+8) + 24*(12+14+15+16+18+20+22+25) + 24*(30+35+40+45+50+55+58+62)
total = sum(sentence_lengths)
n = len(sentence_lengths)
mean = total / n
variance = sum((l - mean) ** 2 for l in sentence_lengths) / n
sigma = math.sqrt(variance)

print(f"\n   Simulated sentence distribution: 72 sentences, {total} chars")
print(f"   Short: 24x (3-8 chars), Medium: 24x (12-25), Long: 24x (30-62)")
print(f"   Mean sentence length: {mean:.1f}")
print(f"   SIGMA2 (std dev): {sigma:.1f}")
print(f"   Set A (>=25): {'PASS' if sigma >= 25 else 'FAIL'}")
print(f"   Set B (>=120): {'PASS' if sigma >= 120 else 'FAIL'}")

# Simulate paragraph distribution
# 15 paragraphs with variation
para_lengths = [20, 30, 45, 80, 90, 100, 110, 120, 130, 140, 150, 160, 180, 200, 250]
# Scale to ~1350
scale = 1350 / sum(para_lengths)
para_lengths = [int(l * scale) for l in para_lengths]
total_p = sum(para_lengths)
n_p = len(para_lengths)
mean_p = total_p / n_p
var_p = sum((l - mean_p) ** 2 for l in para_lengths) / n_p
sigma_p = math.sqrt(var_p)

print(f"\n   Simulated paragraph distribution: {n_p} paragraphs, {total_p} chars")
print(f"   Range: {min(para_lengths)}-{max(para_lengths)} chars")
print(f"   Mean paragraph length: {mean_p:.1f}")
print(f"   PSIGMA2 (std dev): {sigma_p:.1f}")
print(f"   Set A (>=80): {'PASS' if sigma_p >= 80 else 'FAIL'}")
print(f"   Set B (>=300): {'PASS' if sigma_p >= 300 else 'FAIL'}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
