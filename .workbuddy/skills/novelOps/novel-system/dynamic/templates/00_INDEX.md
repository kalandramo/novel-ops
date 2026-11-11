# 故事圣经索引 (00_INDEX)

> 本文件是动态轨文件系统的总索引，记录所有static和dynamic文件的状态。
> 步骤2.5（核心创意卡录入）后更新核心创意卡区域。

---

## 一、核心创意卡

> 步骤2.5完成后填写以下5项。在此之前保持"待定"状态。

| 项目 | 内容 | 状态 |
|------|------|------|
| 一句话概括 | 待定 | 待填 |
| 核心卖点 | 待定 | 待填 |
| 目标读者 | 待定 | 待填 |
| 差异化标签 | 待定 | 待填 |
| 爽点引擎 | 待定 | 待填 |

## 一-B、质检模式

> 步骤1.4完成后填写。用户选择后写入此处，后续每章循环按此模式执行。
> 选择后不再重复提示，除非用户明确要求切换。

| 项目 | 内容 |
|------|------|
| 质检模式 | 待选（QC_FULL / QC_CHECK / QC_SKIP） |
| 选择时间 | 待填 |

---

## 二、Static 文件索引

> Static文件为静态配置文件，写作过程中一般不修改。

| 文件名 | 用途 | 状态 |
|--------|------|------|
| ORCHESTRATOR.md | 全局编排器，定义写作流程 | 就绪 |
| static/topic-spec.md | 选题规格书 | 待创建 |
| static/outline.md | 大纲终稿 | 待创建 |
| static/characters.md | 人物档案 | 待创建 |
| static/pacing-plan.md | 节奏规划 | 待创建 |
| static/packaging.md | 运营包装方案 | 待创建 |

---

## 三、Dynamic 文件索引

> Dynamic文件为动态追踪文件，写作过程中持续更新。本目录下的模板复制到dynamic/即为实际使用文件。

| 文件名 | 用途 | 状态 |
|--------|------|------|
| progress.md | 写作进度追踪 | 已初始化 |
| summaries.md | 章节摘要 | 已初始化 |
| foreshadowing.md | 伏笔追踪（含类型/优先级/关联） | 已初始化 |
| decisions.md | 创意决策记录 | 已初始化 |
| character-state.md | 角色状态表（含年龄/外貌追踪） | 已初始化 |
| established-facts.md | 已确立事实表 | 已初始化 |
| used-tropes.md | 套路使用日志 | 已初始化 |
| next-hook.md | 钩子追踪 | 已初始化 |
| emotion-beat.md | 情感弧线表 | 已初始化 |
| subplot-tracker.md | 副线追踪 | 已初始化 |
| compliance-log.md | 平台合规日志 | 已初始化 |
| gate-log.md | 门禁日志 | 已初始化 |
| sample-library.md | 模仿样本库 | 已初始化 |
| fingerprint.json | 语言指纹 | 已初始化 |
| scene-plan.md | 场景规划（Goal/Conflict/Disaster/Sequel） | 已初始化 |
| timeline.md | 时间线追踪（含角色年龄/时间跳转） | 已初始化 |
| main-quest.md | 主线任务追踪 | 已初始化 |
| location-index.md | 地点索引（含空间关系/场景布局） | 已初始化 |

---

## 四、追踪表索引（11张核心追踪表）

> 以下追踪表在写作过程中由各门禁和步骤读取/写入，确保连续性和一致性。

| 序号 | 追踪表文件 | 核心职责 | 读取时机 | 写入时机 |
|------|-----------|---------|---------|---------|
| 1 | foreshadowing.md | 伏笔种植与回收（含类型/优先级） | G1/G3/G6加载 | 每章写后 |
| 2 | character-state.md | 角色状态一致性（含年龄/外貌） | G1加载 | 每章写后 |
| 3 | established-facts.md | 已确立事实库 | G1/G3加载 | 每章写后 |
| 4 | used-tropes.md | 套路冷却管理 | G1加载 | 每章写后 |
| 5 | next-hook.md | 钩子部署与回报 | G1/G3加载 | 每章写后 |
| 6 | emotion-beat.md | 情感弧线控制 | G1加载 | 每章写后 |
| 7 | subplot-tracker.md | 副线进度追踪 | G1加载 | 每章写后 |
| 8 | compliance-log.md | 平台合规检查 | G4门禁 | 每章写后 |
| 9 | timeline.md | 时间线追踪（含角色年龄/时间跳转） | G1/G6加载 | 每章写后 |
| 10 | main-quest.md | 主线任务追踪 | G1/G6加载 | 每章写后 |
| 11 | location-index.md | 地点索引（含空间关系/场景布局） | G1/G3加载 | 每章写后 |

---

## 五、门禁索引

> 与ORCHESTRATOR.md正文一致。

| 门禁 | 时机 | 检查内容 | 日志文件 |
|------|------|---------|---------|
| G0 | 新书阶段 | 选题+大纲终稿人类审核 | — |
| G1 | 写前加载 | 状态加载门：读取全部动态轨文件，检查连续性（伏笔/角色/事实/套路/钩子/情感/副线/时间线/主线/地点） | gate-log.md |
| G2 | 写前模仿 | 模仿学习门：提取样本特征卡，加载反AI约束和切片样本库 | gate-log.md |
| G3 | 写作 | 写作门：Scene-Sequel规划+草稿生成+R1-R5铁律+Humanizer去AI化+禁词扫描 | gate-log.md |
| G4 | 写后合规 | 平台规则门：字数/节奏/合规/钩子检查 | gate-log.md |
| G5 | 写后指标 | metrics指标门：σ²/TTR/Pσ²/BurstCV/ParaCV/Ngram + AIText参考 | gate-log.md |
| G6 | 写后一致性 | 动态轨一致性门（13项）：Soul Field/性格行为一致/角色性格区分度/人物声音/角色年龄外貌/角色知识/伏笔/时间线/世界观/副线/主线推进/地点/前后文衔接 | gate-log.md |
| G6.5 | 写后报告 | 质检报告生成：G4/G5/G6结果汇总为HTML报告，每章自动生成 | reports/chXXX_report.html |
| G7 | 章末落盘 | 状态落盘门：12项WRITE-CHECK | gate-log.md |
| G8 | 人类终审 | 用户阅读确认（可选，默认跳过） | — |
