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
| foreshadowing.md | 伏笔追踪 | 已初始化 |
| decisions.md | 创意决策记录 | 已初始化 |
| character-state.md | 角色状态表 | 已初始化 |
| established-facts.md | 已确立事实表 | 已初始化 |
| used-tropes.md | 套路使用日志 | 已初始化 |
| next-hook.md | 钩子追踪 | 已初始化 |
| emotion-beat.md | 情感弧线表 | 已初始化 |
| subplot-tracker.md | 副线追踪 | 已初始化 |
| compliance-log.md | 平台合规日志 | 已初始化 |
| gate-log.md | 门禁日志 | 已初始化 |
| sample-library.md | 模仿样本库 | 已初始化 |
| fingerprint.json | 语言指纹 | 已初始化 |
| feishu_sync_state.json | 飞书同步状态 | 已初始化 |

---

## 四、追踪表索引（8张核心追踪表）

> 以下8张表在写作过程中由各门禁和步骤读取/写入，确保连续性和一致性。

| 序号 | 追踪表文件 | 核心职责 | 读取时机 | 写入时机 |
|------|-----------|---------|---------|---------|
| 1 | foreshadowing.md | 伏笔种植与回收 | G1/G3加载 | 每章写后 |
| 2 | character-state.md | 角色状态一致性 | G1加载 | 每章写后 |
| 3 | established-facts.md | 已确立事实库 | G1/G3加载 | 每章写后 |
| 4 | used-tropes.md | 套路冷却管理 | G1加载 | 每章写后 |
| 5 | next-hook.md | 钩子部署与回报 | G1/G3加载 | 每章写后 |
| 6 | emotion-beat.md | 情感弧线控制 | G1加载 | 每章写后 |
| 7 | subplot-tracker.md | 副线进度追踪 | G1加载 | 每章写后 |
| 8 | compliance-log.md | 平台合规检查 | G2门禁 | 每章写后 |

---

## 五、门禁索引

| 门禁 | 时机 | 检查内容 | 日志文件 |
|------|------|---------|---------|
| G1 | 写前加载 | 连续性检查（伏笔/角色/事实/套路/钩子/情感/副线） | gate-log.md |
| G2 | 写后合规 | 平台合规检查（字数/爽点/爆点/钩子/AI比例/意识形态） | gate-log.md |
| G3 | 风险预警 | 伏笔超期/套路冷却/钩子逾期 | gate-log.md |
| G4 | 语言指纹 | AI味检测（σ²/TTR/EGR/Pσ²） | gate-log.md |
| G5 | 情感弧线 | 情感连续性与代偿 | gate-log.md |
| G6 | 副线健康 | 副线出场频率与进度 | gate-log.md |
| G7 | 章末检查 | 钩子部署与节奏控制 | gate-log.md |
