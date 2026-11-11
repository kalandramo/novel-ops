# Humanizer 去AI化Prompt

> 来源：writers-second-brain (Apache 2.0 License)
> 用途：G3草稿生成后的去AI化处理、G5参考指标
> 集成位置：metrics.py calc_ai_pattern_density + G3写作约束

---

## 概述

Humanizer是一个3-Pass去AI化管道：
1. **Detection** — 检测AI典型模式
2. **Rewrite** — 重写标记内容，保留作者voice
3. **Audit** — 最终审计，确保无遗漏

---

## Pass 1: Detection 检测规则

### 1. AI Vocabulary（AI词汇）

标记并替换以下词汇：

**中文AI高频词**：
- 不禁、竟然、居然
- 一股XX涌上心头
- 心中暗道、暗自想道
- 嘴角微微上扬
- 目光如炬、浑身一震
- 倒吸一口凉气
- 在这个世界上
- 仿佛在诉说着什么
- 命运的齿轮开始转动
- 在历史的长河中
- 总而言之、综上所述
- 不得不说、值得一提的是
- 毫无疑问
- 复杂的情感在心中交织
- 百感交集
- 一种说不清道不明的情绪

**英文AI高频词**（参考）：
- additionally, furthermore, moreover, notably
- testament, tapestry, landscape, delve, embark, foster
- pivotal, profound, nuanced, multifaceted, intricate
- resonate, underscore, encompass, facilitate

### 2. Significance Inflation（夸张抬高）

- "a pivotal moment" → 直接描述时刻本身
- "deeply meaningful" → 通过动作展示意义
- "a testament to" → 删除或改写成具体表达
- "巨大的、恐怖的、令人窒息的" → 选一个

### 3. Synonym Cycling（同义词循环）

- 同一段落内用2-3种说法重复同一意思
- 选择最强版本，删除其余重复

### 4. Hedging in Narrative Voice（叙事犹豫）

- "seemed to" → 删除，改为直接陈述
- "appeared to" → 删除
- "could potentially" → 删除"potentially"
- 例外：对话或不可靠叙述者的犹豫是可以的

### 5. Mechanical Rule of Three（机械排比）

- "X, Y, and Z"三词结构，且三项并不真正不同
- 改为更自然的结构：pair + single，或四项列表

### 6. Generic Descriptions（泛化描述）

- "The sun dipped below the horizon" → 说明颜色、照亮了什么
- "A chill ran down her spine" → 说明具体身体感受
- "His heart raced" → 说明肾上腺素具体是什么感觉

### 7. Dialogue Tag Abuse（对话标签滥用）

- 避免：exclaimed, mused, retorted, quipped, declared, proclaimed
- 替换为：said（80%情况）或删除标签，改用动作节拍

### 8. Emotional Labeling（情感标签）

- "He felt sad" → 通过动作展示悲伤
- "She was angry" → 通过身体反应展示愤怒
- "They were happy" → 通过行为展示快乐

### 9. Purple Prose Inflation（华丽堆砌）

- 每个名词带2+形容词
- 过度隐喻叠加
- 不推进人物或情节的描述

### 10. Copula Avoidance（系动词回避）

- "serves as" → "is"或"was"
- "features" → "has"或"had"
- "boasts" → 直接描述

---

## Pass 2: Rewrite 重写规则

重写时需保留：
- 作者已建立的voice
- 角色特定的对话模式
- 有意的文学手法（如deliberate tricolon、unreliable narrator hedging）
- 作者对em dash的偏好（如果规则启用）

### 通用改写原则

| AI模式 | 改写方向 |
|--------|---------|
| "不禁皱眉" | "眉头拧在一起" |
| "一股暖流涌上心头" | "眼眶微热" |
| "嘴角微微上扬" | "挑了挑眉" |
| "他感到非常愤怒" | "手指陷进掌心的肉里，指节发白" |
| "她不禁想起了" | "她皱起眉头，回想起" |
| "随着修炼的深入" | "又一个月过去了。当他再次凝聚灵力时" |
| "他不知道的是" | 直接切换视角或用环境暗示 |
| "仿佛...一般" | 直接描写结果或用暗喻 |

---

## Pass 3: Audit 审计

最终扫描重写文本，确保没有遗漏的AI-isms。

---

## 输出格式

```markdown
## Humanizer Report
### Patterns Found: [count]
| Pattern | Count | Severity |
|---------|-------|----------|
| [pattern type] | [N] | [High/Medium/Low] |

### Changes Made
- **[Pattern]**: "[original text]" → "[rewritten text]"

### Humanized Text
[Full rewritten passage]

### Notes
[Any patterns that were intentionally preserved and why]
```

---

## Prose Mechanics 量化指标

| 指标 | 目标 | 说明 |
|------|------|------|
| -ly 副词 | 0 | 排除only/early/family等非副词 |
| 被动语态 | 0 | was/were/is/are + 过去分词 |
| felt/realized/knew | 0 | 统计10个Tell动词 |
| 隐喻过载 | 0 | 每段超过1个隐喻即标记 |
| 否定结构 | 报告 | wasn't/didn't/couldn't等 |
| 句长标准差 | >3.0 | 低于3.0标记为MONOTONOUS |

---

## 集成到metrics.py的规则

以下规则可直接用正则实现自动检测：

```python
AI_PATTERN_WORDS = {
    # 词汇层面
    "不禁", "竟然", "居然",  # 限用词
    "一股.*涌上心头",  # 情感过度
    "心中暗道", "暗自想道",  # 心理旁白
    "嘴角微微上扬",  # AI万能公式
    "目光如炬", "浑身一震", "倒吸一口凉气",  # 早年网文滥用
    "在这个世界上", "命运的齿轮", "在历史的长河中",  # 哲学废话
    "总而言之", "综上所述", "不得不说", "值得一提的是",  # 过度总结
    "百感交集", "复杂的情感在心中交织",  # 情感标签
}

AI_SENTENCE_PATTERNS = {
    r"随着.+的.+,.+也",  # 万能开头
    r"他不知道的是",  # 上帝视角插话
    r"如果.+知道.+的话",  # 假设句式
    r".+看着.+,嘴角微微上扬",  # AI最爱
    r"仿佛.+一般",  # 模板比喻
    r".+的.+，如同.+一般",  # 过度比喻
}

AI_NARRATIVE_PATTERNS = {
    r"经过.+的(苦修|努力|修炼).+,有了很大提升",  # 总结式叙事
    r"他感到(非常)?(愤怒|开心|悲伤|害怕)",  # 情感宣告
    r"这就是.+的世界吗",  # 万能感叹
    r"时光飞逝",  # 总结性时间过渡
}
```
