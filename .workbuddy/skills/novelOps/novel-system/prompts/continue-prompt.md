# 续写流程指令

> **触发条件**：用户说"续写""接着写""继续往下写"时执行
> **输入**：已有章节目录路径 + 续写章数（默认1章）+ 是否走门禁（默认否）
> **输出**：续写章节 + 更新的动态轨文件
> **核心原则**：续写默认不走G1-G7门禁循环，直接生成章节。用户明确要求时才走门禁。

---

## 流程概览

```
已有章节输入 → 动态轨重建 → 续写规划 → 生成下一章 → 输出
                                                    ↓（可选）
                                              门禁检查（用户要求时）
```

---

## 步骤1：动态轨重建

扫描已有章节，自动生成/更新15个动态轨文件。

### 1.1 progress.md — 进度追踪

扫描已有章节文件，提取：
- 当前章号（最后一个章节文件的章号）
- 已完成章数
- 总字数
- 当前卷号（如文件名含卷号）

写入 `dynamic/progress.md`

### 1.2 summaries.md — 章节摘要

对每章生成200-300字摘要，包含：
- 本章核心事件（1-2句）
- 关键冲突和转折
- 新出场角色
- 章末钩子内容
- 情绪基调

**最近5章**生成详细摘要（500字），早期章节生成简摘要（200字）。

写入 `dynamic/summaries.md`

### 1.3 character-state.md — 角色状态

从已有章节提取每个角色的当前状态：
- 物理状态（位置、健康、装备）
- 心理状态（情绪、目标、内心冲突）
- 关系状态（与其他角色的关系变化）
- 语言指纹（口头禅、标志性动作、说话习惯）

**提取方式**：扫描每章中该角色的对话和描写，记录最后出现的状态。

写入 `dynamic/character-state.md`

### 1.4 foreshadowing.md — 伏笔追踪

扫描已有章节，提取：
- 已种植伏笔（标记种植章号、内容、预期回收位置）
- 已回收伏笔（标记回收章号）
- 未回收伏笔（按章号排序，标记逾期程度）

**识别信号**：异常物品、未解释现象、角色隐瞒的信息、预言/梦境、神秘人物

写入 `dynamic/foreshadowing.md`

### 1.5 established-facts.md — 已确立事实

提取已确立的世界观和情节事实：
- 世界规则（力量体系、社会结构、地理）
- 已发生关键事件（时间线）
- 已揭示的角色背景
- 已确立的人物关系

写入 `dynamic/established-facts.md`

### 1.6 next-hook.md — 钩子台账

从最近章节提取：
- 章末钩子类型（参考 `knowledge/suspense-hooks.md` 的10种类型）
- 待回报钩子列表
- 逾期钩子（超过5章未回报）

写入 `dynamic/next-hook.md`

### 1.7 其他动态轨文件

| 文件 | 提取内容 |
|------|---------|
| `used-tropes.md` | 已使用的套路/桥段及使用章号 |
| `emotion-beat.md` | 情感弧线记录（每章情绪强度、波峰波谷） |
| `subplot-tracker.md` | 副线进度（每条副线的起始、当前状态、下一步预期） |
| `decisions.md` | 关键决策记录（角色做出的重要选择及后果） |
| `compliance-log.md` | 合规日志（字数/节奏统计） |
| `gate-log.md` | 门禁日志（初始化为"续写模式-未走门禁"） |
| `00_INDEX.md` | 更新索引，标记续写起点和模式 |

### 1.8 fingerprint.json — 语言指纹

从最近5章提取角色语言指纹：
- phrases：角色高频口头禅
- actions：角色标志性动作
- style：句长分布、感官偏好、对话风格

写入 `dynamic/fingerprint.json`

### 1.9 timeline.md — 时间线追踪

从已有章节提取时间线：
- 故事开始时间和当前故事时间
- 每章对应的故事内时间节点
- 时间跳转记录（章间时间跨度）
- 角色年龄变化（出场年龄→当前年龄）

写入 `dynamic/timeline.md`

### 1.10 main-quest.md — 主线任务追踪

从已有章节推断主线任务：
- 主角终极目标
- 阶段任务列表（已领取/进行中/已完成）
- 每章主线推进记录
- 当前主线停滞检查

写入 `dynamic/main-quest.md`

### 1.11 location-index.md — 地点索引

从已有章节提取地点信息：
- 地点注册表（名称/类型/出场章节）
- 空间关系表（地点间距离和通勤时间）
- 场景布局记录（重要场景内部描写）

写入 `dynamic/location-index.md`

---

## 步骤2：续写规划

### 2.1 大纲推断

基于已有章节，AI分析以下要素：
- 主线进展（当前处于什么阶段：开局/发展/高潮/收尾）
- 未解决的冲突
- 待回收的伏笔
- 角色弧线走向

生成后续3-5章大纲，每章包含：
- 核心事件
- 冲突类型
- 爽点设计（参考 `knowledge/genre-guides.md`）
- 钩子安排

写入 `static/outline-continued.md`

### 2.2 节奏规划

基于已有章节的节奏模式，推断后续节奏：
- 统计已有章节的爽点分布
- 判断当前是否需要"张"（蓄势）还是"弛"（释放）
- 规划下一个爽点的位置

参考 `knowledge/genre-guides.md` 中的节奏要求。

---

## 步骤3：生成下一章

### 3.1 加载上下文

读取以下动态轨文件作为写作上下文：
1. `dynamic/summaries.md` — 最近5章摘要（必须）
2. `dynamic/character-state.md` — 角色当前状态含年龄/外貌（必须）
3. `dynamic/foreshadowing.md` — 待回收伏笔含类型/优先级（必须）
4. `dynamic/next-hook.md` — 待回报钩子（必须）
5. `dynamic/established-facts.md` — 已确立事实（必须）
6. `dynamic/used-tropes.md` — 已用套路（避免重复）
7. `dynamic/emotion-beat.md` — 情感弧线
8. `dynamic/subplot-tracker.md` — 副线进度
9. `dynamic/timeline.md` — 时间线和角色年龄（必须）
10. `dynamic/main-quest.md` — 主线任务进度（必须）
11. `dynamic/location-index.md` — 地点和空间关系（必须）
12. `static/outline-continued.md` — 续写大纲

### 3.2 加载写作约束

依次读取：
1. `prompts/writer-prompt.md` — 草稿生成系统prompt
2. `knowledge/genre-guides.md` — 题材参数（对话占比/爽点密度/铺垫容忍）
3. `knowledge/anti-ai-patterns.md` — 4层反AI约束
4. `knowledge/suspense-hooks.md` — 钩子系统
5. `knowledge/character-templates.md` — 角色语言档案

### 3.3 Scene-Sequel场景规划

读取 `dynamic/scene-plan.md` 模板，规划本章场景结构：
- 每个场景填写 Goal→Conflict(3层)→Disaster 或 Reaction→Dilemma→Decision
- 禁止"干净成功"结尾
- 场景数量2-4个

### 3.4 生成草稿

- 字数：1200-1500字
- **R1-R5铁律必须执行**：
  - R1：禁止情绪标签化
  - R2：强制内心过程≥20%
  - R3：每200字内必须有短句(≤5字)+长句(≥20字)
  - R4：禁止场景结尾总结
  - R5：对话必须携带潜台词
- 承接上一章章末钩子
- 部署本章章末钩子
- 对话占比按场景类型动态调整（冲突60-80%/日常40-60%/过渡20-40%）

### 3.5 Humanizer去AI化

加载 `prompts/humanizer-prompt.md`，执行3-Pass：
1. Detection：扫描10类AI模式
2. Rewrite：重写AI痕迹段落
3. Audit：验证去AI化效果

---

## 步骤4：质检模式执行

> **首次续写前询问用户质检模式**，选择后写入 `dynamic/00_INDEX.md`，后续不再重复提示。
> 三种模式：`QC_FULL`（质检+自动重写）/ `QC_CHECK`（仅质检不重写）/ `QC_SKIP`（跳过质检）。

### 4.1 按模式执行门禁

| 门禁 | QC_FULL | QC_CHECK | QC_SKIP |
|------|---------|----------|---------|
| G4 平台规则 | ✅ 执行+自动修复 | ✅ 执行+报告 | ⏭️ 跳过 |
| G5 指标门禁 | ✅ 执行+自动修复 | ✅ 执行+报告 | ⏭️ 跳过 |
| G6 一致性门禁 | ✅ 执行+自动修复 | ✅ 执行+报告 | ⏭️ 跳过 |

### 4.2 G4 平台规则门
- 字数：1200-1500字
- 节奏：不连续2章无进展
- 钩子：章末必须有钩子

### 4.3 G5 metrics指标门
```bash
python tools/metrics.py <续写章节> --aitext
```
- 7项硬门禁全部通过
- AIText比例≤30%

### 4.4 G6 一致性门
- 本章开头是否与上章结尾衔接
- 角色状态是否连续（含年龄/外貌/知识状态）
- 伏笔是否有新种植或回收（按scope预警）
- 时间线是否一致
- 主线任务是否推进

---

## 步骤5：输出

### 5.1 续写章节

保存到用户指定路径或默认 `chapters/` 目录。

### 5.2 更新动态轨

续写完成后，更新以下动态轨文件：
- `progress.md` — 章号+1
- `summaries.md` — 添加本章摘要
- `character-state.md` — 更新角色状态（含年龄/外貌变化）
- `foreshadowing.md` — 新种植/回收的伏笔（含类型/优先级）
- `next-hook.md` — 新部署/回报的钩子
- `used-tropes.md` — 本章使用的套路
- `emotion-beat.md` — 本章情绪强度
- `gate-log.md` — 门禁结果（如走了门禁）
- `timeline.md` — 本章时间节点/时间跳转/年龄变化
- `main-quest.md` — 本章主线推进记录
- `location-index.md` — 新出现的地点/场景布局

### 5.3 下一章建议

输出后续续写建议：
- 下章核心事件
- 待回收伏笔提醒
- 节奏建议（张/弛）

---

## 与现有系统的关系

| 复用组件 | 续写流程中的角色 |
|---------|----------------|
| 15个动态轨文件 | 步骤1自动重建 + 步骤5更新 |
| writer-prompt.md | 步骤3.2草稿生成系统prompt |
| humanizer-prompt.md | 步骤3.5去AI化 |
| genre-guides.md | 步骤3.2题材参数 |
| anti-ai-patterns.md | 步骤3.2反AI约束 |
| suspense-hooks.md | 步骤3.2钩子系统 |
| character-templates.md | 步骤3.2角色语言档案 |
| scene-plan.md | 步骤3.3场景规划模板 |
| metrics.py | 步骤4可选门禁检查 |
| R1-R5铁律 | 步骤3.4写作约束 |

> **与标准章节循环的区别**：
> - 标准循环（ORCHESTRATOR.md）：G1→G2→G3→G4→G5→G6→G7 全部门禁
> - 续写流程：动态轨重建→生成→输出（默认跳过门禁）
> - 续写流程复用G3写作门的核心能力（writer-prompt + R1-R5 + Humanizer），但不强制走G1-G7循环
> - 用户可通过"走门禁"指令切换到完整门禁模式
