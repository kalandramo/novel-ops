# NovelOps v2 Code Wiki

> **版本**: v1.0.0\
> **最后更新**: 2026-08-16\
> **项目类型**: AI Agent Skill（小说连载流水线执行器）

***

## 目录

1. [项目概述](#1-项目概述)
2. [整体架构](#2-整体架构)
3. [目录结构详解](#3-目录结构详解)
4. [核心模块职责](#4-核心模块职责)
5. [8级门禁系统](#5-8级门禁系统)
6. [15条动态轨说明](#6-15条动态轨说明)
7. [10个角色Agent提示词](#7-10个角色agent提示词)
8. [工具脚本详解](#8-工具脚本详解)
9. [数据流与状态管理](#9-数据流与状态管理)
10. [依赖关系](#10-依赖关系)
11. [项目运行方式](#11-项目运行方式)
12. [故障恢复机制](#12-故障恢复机制)
13. [设计原则与约束优先级](#13-设计原则与约束优先级)

***

## 1. 项目概述

### 1.1 项目定位

NovelOps v2 是一个 **Agent Skill 协议**，它把软件工程的 CI/CD 纪律搬进了网络小说连载。装进支持 Skill 的 AI Agent（TRAE、Claude Code 等）后，对 Agent 说「写下一章」，它会自包含地跑完一章的完整生产循环——写作、质检、打回重写、状态落盘——只在 4 个关键决策点停下来等人类确认。

### 1.2 解决的三大核心问题

| 问题       | 解决方案                                                                     |
| -------- | ------------------------------------------------------------------------ |
| **长跑崩坏** | 15条动态轨逐章追踪：伏笔超20章标黄、超40章标红；套路有冷却期；情感连续3章同方向强制调整；每条副线每8章必须出场              |
| **AI味**  | `metrics.py` 实测 σ²/TTR/EGR/Pσ² 与角色语言指纹；每10章做同质化检测与文风稳定性检查（SC<0.6时重写漂移章节） |
| **平台合规** | 质检门内置 AI占比≤30%、原创度≥70%、查重≤2处、红线词扫描，终审后三级敏感词检测再导出                         |

### 1.3 关键技术特征

* **8级质量门禁**: G1-G7 全自动 + G8 人工确认（仅4个决策点）

* **15条连载状态轨**: 纯 Markdown 格式，git 可 diff、人可直接改

* **3个量化工具脚本**: metrics.py / chapter-word-counter.py / report-gen.py

* **10个角色Agent**: 选题市场、选题、素材、大纲、人物、节奏、运营、创意扰动、写作、质检

* **断点续跑**: 状态全部落盘，会话断开后从断点恢复

***

## 2. 整体架构

### 2.1 五层架构模型

```
┌─────────────────────────────────────────────────────────┐
│  Layer 5: 交互入口层 (Entry Point)                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │  SKILL.md (novelOps-v2 Skill 定义)                    │  │
│  │  - 触发词匹配: 启动新书/写下一章/继续写作/推进章节  │  │
│  │  - 模式判断: 新书模式 vs 章节循环模式               │  │
│  └───────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  Layer 4: 主编调度层 (Orchestrator)                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │  ORCHESTRATOR.md (主编调度指令)                     │  │
│  │  - 新书模式: 阶段0全局规划 (7步骤+门禁1)           │  │
│  │  - 章节循环: THINK→DRAFT→VERIFY→REVISE (G1-G7)    │  │
│  │  - 4个人工决策点: 门禁1/2/3/4 (G8)                │  │
│  │  - 10章阶段质检 + 全书终审流程                     │  │
│  └───────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  Layer 3: 角色Agent层 (Role Prompts)                     │
│  ┌────────────┬────────────┬────────────┬────────────┐  │
│  │ 选题市场   │ 选题确认   │ 素材准备   │ 大纲设计   │  │
│  ├────────────┼────────────┼────────────┼────────────┤  │
│  │ 人物档案   │ 节奏规划   │ 运营包装   │ 创意扰动   │  │
│  ├────────────┼────────────┴────────────┴────────────┤  │
│  │ 写作Agent  │         质检Agent (QC)               │  │
│  └────────────┴──────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  Layer 2: 状态持久层 (State Tracking)                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Static 静态轨 (阶段0产出, 全书锁定)               │  │
│  │  - market_research / topic / outline / characters │  │
│  │  - pacing / packaging / core_creative_card        │  │
│  ├───────────────────────────────────────────────────┤  │
│  │  Dynamic 动态轨 (每章读写, 15文件)                 │  │
│  │  - progress / summaries / foreshadowing / ...     │  │
│  │  - 8张核心追踪表 + 合规日志 + 门禁日志 + 指纹     │  │
│  └───────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  Layer 1: 工具执行层 (Tool Scripts)                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │  metrics.py            人写特征度量工具            │  │
│  │    · B组章级指标: σ²/TTR/EGR/Pσ²                  │  │
│  │    · C组卷级指标: Cσ²/Iσ²/SC                      │  │
│  │    · 同质化检测 + 创意扰动建议                     │  │
│  │    · 查重自检 + 模仿评价                           │  │
│  ├───────────────────────────────────────────────────┤  │
│  │  chapter-word-counter.py  章节字数统计工具         │  │
│  │    · CJK字符统计 (排除标点空白)                   │  │
│  │    · 批量统计 + 进度条可视化                       │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 2.2 核心工作流

```
用户说"启动新书"
    │
    ▼
┌─────────────────────────────────────────────┐
│  阶段0: 全局规划 (新书模式)                  │
│  10个Agent接力: 选题→创意卡→素材→大纲→人物  │
│              →节奏→运营→创意扰动             │
│                                              │
│  ── 门禁1 (G8人类审核) ──停在这等用户通过──  │
└─────────────────────────────────────────────┘
    │ 通过
    ▼
┌─────────────────────────────────────────────┐
│  前3章特殊流程                               │
│  · 双重G5指标检查 (人写区间)                 │
│  · 300字冲突密度审查                         │
│  · 最多允许5次重写                           │
│                                              │
│  ── 门禁2 (G8强制人类审核) ──停在这等确认──  │
└─────────────────────────────────────────────┘
    │ 通过
    ▼
┌─────────────────────────────────────────────┐
│  章节循环模式 (每章一次)                      │
│  ┌─────────────────────────────────────┐    │
│  │ G1 状态加载门 — 读15条动态轨         │    │
│  │ G2 模仿学习门 — 样本特征卡+指纹      │    │
│  │ G3 写作门     — 草稿+禁词扫描        │    │
│  │ G4 平台规则门 — 字数/节奏/合规       │    │
│  │ G5 量化指标门 — σ²/TTR/EGR/Pσ²       │    │
│  │ G6 动态轨一致性 — 事实/角色/伏笔     │    │
│  │ G7 状态落盘门 — 12项WRITE-CHECK      │    │
│  └─────────────────────────────────────┘    │
│          │ 打回 ≤3次                        │
│          └────→ REVISE → 重入G3             │
│                                              │
│  每10章触发一次阶段质检 (14项)               │
│  约50%进度触发门禁3 (G8人类审核)             │
└─────────────────────────────────────────────┘
    │ 全书完成
    ▼
┌─────────────────────────────────────────────┐
│  全书终审流程 (14项检查)                     │
│  ── 门禁4 (G8人类终审) ──                    │
│  → 三级敏感词检测 → 番茄小说格式导出         │
└─────────────────────────────────────────────┘
```

***

## 3. 目录结构详解

```
novel-ops-v1.0.0/
├── SKILL.md                          # [技能入口] TRAE技能定义文件，含触发词、描述
├── README.md                         # 项目说明文档
├── LICENSE                           # MIT 许可证
├── CODE_WIKI.md                      # [本文档] 完整代码维基
├── docs/
│   └── install.md                    # Windows+TRAE 安装教程（分步手把手）
│
└── novel-system/                     # [核心工作区] 小说项目模板（复制到项目目录）
    ├── ORCHESTRATOR.md              # [L4主编调度] 核心流程定义，系统"宪法"
    │
    ├── static/                       # [L2静态轨] 阶段0产出，写作过程中一般不修改
    │   ├── market_research.md        # 步骤1产出: 市场调研报告
    │   ├── topic.md                  # 步骤2产出: 选题确认书
    │   ├── core_creative_card.md     # 步骤2.5产出: 核心创意卡（北极星，AI不可改写）
    │   ├── outline.md                # 步骤3产出: 三幕结构大纲（200-330章）
    │   ├── characters.md             # 步骤4产出: 人物档案（含Soul Field铁律）
    │   ├── pacing.md                 # 步骤5产出: 节奏规划（爽点/爆点清单）
    │   ├── packaging.md              # 步骤6产出: 运营包装（书名/简介/标签）
    │   └── prompts/                  # [L3角色提示词] 10个Agent角色定义
    │       ├── topic-market.md       #   Agent1: 选题市场调研
    │       ├── topic.md              #   Agent2: 选题确认
    │       ├── material-prep.md      #   Agent2.8: 素材准备（行业/打脸/情感素材库）
    │       ├── outline.md            #   Agent3: 三幕大纲设计
    │       ├── characters.md         #   Agent4: 人物档案（含Soul Field定义）
    │       ├── pacing.md             #   Agent5: 节奏规划
    │       ├── operations.md         #   Agent6: 运营包装（书名简介标签）
    │       ├── creative-disruption.md#   Agent7: 创意扰动（防同质化）
    │       ├── writer.md             #   Agent8: 写手（章节草稿生成）
    │       └── qc.md                 #   Agent9: 质检编辑（A/B/D三组检查）
    │
    ├── dynamic/                      # [L2动态轨] 每章读写，首次运行从templates/初始化
    │   ├── templates/                #   15个动态轨模板（新小说初始化来源）
    │   │   ├── 00_INDEX.md           #   索引文件 + 核心创意卡同步（北极星）
    │   │   ├── progress.md           #   当前阶段/章号/卷号/步骤完成状态
    │   │   ├── summaries.md          #   最近5章压缩摘要（每章约200字）
    │   │   ├── foreshadowing.md      #   伏笔种植/回收记录（超20章标黄/超40章标红）
    │   │   ├── decisions.md          #   创意扰动提案记录
    │   │   ├── character-state.md    #   角色状态（情绪/位置/关系/已知信息）
    │   │   ├── established-facts.md  #   已确立事实（世界观/时间线/地理/数字）
    │   │   ├── used-tropes.md        #   套路使用日志（冷却期检查）
    │   │   ├── next-hook.md          #   待回报钩子 + 章尾钩子规划
    │   │   ├── emotion-beat.md       #   情感弧线状态（连续3章同方向预警）
    │   │   ├── subplot-tracker.md    #   副线当前阶段与出场频率追踪
    │   │   ├── sample-library.md     #   模仿样本特征卡库（容量上限5）
    │   │   ├── fingerprint.json      #   角色语言指纹库（口头禅/句式/比喻）
    │   │   ├── compliance-log.md     #   平台合规日志（字数/AI检测/查重/敏感词）
    │   │   ├── gate-log.md           #   各门禁通过/失败记录（断点恢复依据）
    │   │
    │   ├── qa/                       #   [运行时创建] 质检报告目录
    │   │   ├── ch001_qa.md           #     各章QA报告
    │   │   └── stage10_qa.md         #     10章阶段质检报告
    │   └── material-prep-report.md   #   [运行时创建] 素材准备报告
    │
    ├── tools/                        # [L1工具脚本] 3个Python量化工具
    │   ├── metrics.py                #   人写特征度量（核心量化工具）
    │   ├── chapter-word-counter.py   #   章节字数统计（番茄平台标准）
    │   └── report-gen.py            #   质检报告HTML生成器
    │
    ├── chapters/                     # [运行时创建] 章节草稿与终稿
    │   ├── ch001_draft.md            #   G3写作门产出: 章节草稿
    │   └── ch001_final.md            #   G7落盘门产出: 章节终稿
    │
    └── publish/                      # [运行时创建] 发布导出目录
        └── fanqie/                   #   番茄小说格式导出（门禁4通过后）
```

***

## 4. 核心模块职责

### 4.1 Layer 5: 交互入口层 — SKILL.md

**文件**: [SKILL.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/SKILL.md)

**职责**: 作为 TRAE/Claude Code 技能的入口文件，负责：

1. 定义技能元数据（name, description）
2. 声明触发词：启动新书 / 写下一章 / 继续写作 / 推进章节
3. 自包含执行 ORCHESTRATOR.md 定义的完整写作流程
4. 模式判断：读取 `dynamic/progress.md` 判断进入新书模式或章节循环模式

**启动流程**:

```
1. 环境确认（检查 novel-system/ 目录结构完整性）
2. 如 dynamic/ 为空 → 从 templates/ 初始化15个动态轨
3. 读 progress.md → 判断模式:
   - 不存在/阶段0 → 进入「新书模式」
   - 章号≥1     → 进入「章节循环模式」
```

***

### 4.2 Layer 4: 主编调度层 — ORCHESTRATOR.md

**文件**: [ORCHESTRATOR.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/ORCHESTRATOR.md)

**职责**: 系统的"宪法"，所有写作决策以此为准。定义完整的两大执行模式和四大人工决策点。

**A. 新书模式（阶段0: 全局规划）**

| 步骤  | Agent角色 | 输入           | 产出文件                                                   | 核心动作                               |
| --- | ------- | ------------ | ------------------------------------------------------ | ---------------------------------- |
| 1   | 选题市场    | 人类偏好         | `static/market_research.md`                            | WebSearch三组关键词+WebFetch抓取+TOP3推荐   |
| 2   | 选题确认    | 市场报告         | `static/topic.md`                                      | 确定赛道/金手指/爽点引擎/差异化                  |
| 2.5 | 核心创意卡   | 选题卡+作者协作     | `static/core_creative_card.md` + `dynamic/00_INDEX.md` | 5项设定：城市/行业/核心能力/核心矛盾/创意差异化（AI不可改写） |
| 2.8 | 素材准备    | 选题卡+创意卡+市场报告 | `dynamic/material-prep-report.md`                      | 行业素材库+打脸场景素材库+情感线素材库               |
| 3   | 大纲Agent | 选题卡+创意卡+素材   | `static/outline.md`                                    | 200-330章三幕结构，22%:30%:30%:18%比例     |
| 4   | 人物Agent | 选题卡+大纲+创意卡   | `static/characters.md`                                 | 每人定义Soul Field铁律（5维）               |
| 5   | 节奏Agent | 大纲+人物卡       | `static/pacing.md`                                     | 10章大爆点+3章小爽点+张弛比检查表                |
| 6   | 运营优化    | 选题卡+大纲       | `static/packaging.md`                                  | 书名三选一+短/长简介+3主标签+4-5副标签            |
| 7   | 创意扰动    | 审大纲          | 追加`dynamic/decisions.md`                               | 同质化自检+扰动注入+差异化3点确认                 |

**门禁1（G8人类审核）**: 汇总8项文件（市场/选题/创意卡/素材/大纲/人物/节奏/包装/创意），等待用户通过

**B. 章节循环模式**

每章执行 G1→G2→G3→G4→G5→G6→G7 七级门禁，详见第5节

**C. 四大人工决策点（G8）**

| 门禁  | 触发时机       | 审核内容                     |
| --- | ---------- | ------------------------ |
| 门禁1 | 阶段0完成后     | 选题方向/主线/卖点/核心创意卡5项/素材/大纲 |
| 门禁2 | 前3章完成后（强制） | 300字冲突/钩子/爽点密度/AI味分/人设   |
| 门禁3 | 约50%进度     | 主线推进/人物弧光/节奏拖沓/市场反馈      |
| 门禁4 | 全书完成后      | 终稿质量/标题简介标签/发布就绪/合规自保    |

***

### 4.3 Layer 3: 角色Agent层 — static/prompts/

10个提示词文件，每个定义一个独立角色Agent的行为规范：

| 文件                                                                                                                                   | 角色名       | 关键职责                        | 核心输入                | 核心输出                      |
| ------------------------------------------------------------------------------------------------------------------------------------ | --------- | --------------------------- | ------------------- | ------------------------- |
| [topic-market.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/static/prompts/topic-market.md)               | 选题市场Agent | 2026年番茄热门题材调研，热度/增速/改编率三维分析 | 人类偏好                | `market_research.md`      |
| [topic.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/static/prompts/topic.md)                             | 选题Agent   | 基于市场报告确定赛道、金手指、爽点引擎         | 市场报告                | `topic.md`                |
| [material-prep.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/static/prompts/material-prep.md)             | 素材准备Agent | 行业/打脸/情感三大素材库建设             | 选题卡+创意卡             | `material-prep-report.md` |
| [outline.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/static/prompts/outline.md)                         | 大纲Agent   | 200-330章三幕结构，爽点/伏笔/副线编织     | 选题卡+创意卡+素材          | `outline.md`              |
| [characters.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/static/prompts/characters.md)                   | 人物Agent   | 每人定义Soul Field铁律+语言指纹       | 选题卡+大纲+创意卡          | `characters.md`           |
| [pacing.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/static/prompts/pacing.md)                           | 节奏Agent   | 3章小爽/10章大爆/3:1张弛比规划         | 大纲+人物卡              | `pacing.md`               |
| [operations.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/static/prompts/operations.md)                   | 运营优化Agent | 书名/简介/标签的番茄平台调性适配           | 选题卡+大纲              | `packaging.md`            |
| [creative-disruption.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/static/prompts/creative-disruption.md) | 创意扰动Agent | 同质化检测+反预期元素注入               | 审大纲/审同质化报告          | `decisions.md`            |
| [writer.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/static/prompts/writer.md)                           | 写作Agent   | 1200-1500字章节草稿，四段式结构+AI味词规避 | 章节卡+节奏卡+热轨          | `chapters/chN_draft.md`   |
| [qc.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/static/prompts/qc.md)                                   | 质检Agent   | A组合规+B组人写特征+D组状态一致性三组检查     | 草稿+章节卡+热轨+metrics输出 | `dynamic/qa/chN_qa.md`    |

***

### 4.4 Layer 2: 状态持久层

#### 4.4.1 Static 静态轨（6文件）

写入后即锁定，AI无权修改核心创意卡5项设定：

| 文件                      | 生命周期   | 写入时机           | 读取时机                 |
| ----------------------- | ------ | -------------- | -------------------- |
| `market_research.md`    | 阶段0    | 步骤1完成          | 步骤2选题参考              |
| `topic.md`              | 阶段0    | 步骤2完成          | 步骤3-6参考              |
| `core_creative_card.md` | 全书     | 步骤2.5完成（AI不可改） | **每章G1加载，作为北极星**     |
| `outline.md`            | 阶段0    | 步骤3完成          | 每章G1加载当前章大纲条目        |
| `characters.md`         | 阶段0    | 步骤4完成          | 每章G1加载出场人物Soul Field |
| `pacing.md`             | 阶段0    | 步骤5完成          | 每章G1加载节奏要求           |
| `packaging.md`          | 阶段0+终审 | 步骤6+门禁4前       | 门禁4审核用               |

#### 4.4.2 Dynamic 动态轨（15文件，详见第6节）

***

### 4.5 Layer 1: 工具脚本层 — tools/

详见第8节工具脚本详解。

***

## 5. 8级门禁系统

### 5.1 门禁总览

```
G8（人类终审，4个决策点）
 │
 ├── 门禁1: 选题+大纲终稿审核（新书模式结束）
 ├── 门禁2: 前3章必审（强制）
 ├── 门禁3: 中段转折（约50%进度）
 └── 门禁4: 全书终审

G1-G7（全自动，章节循环每章必过）
 │
 G1  状态加载门     ← 读取15条动态轨
  │
 G2  模仿学习门     ← 样本特征卡+角色指纹
  │
 G3  写作门         ← 草稿生成+禁词扫描
  │
 G4  平台规则门     ← 字数/节奏/合规7项检查
  │
 G5  量化指标门     ← σ²/TTR/EGR/Pσ²/FP达标
  │
 G6  动态轨一致性门  ← 事实/套路/钩子/角色/副线7项
  │
 G7  状态落盘门     ← 12项WRITE-CHECK
```

### 5.2 各门禁详细说明

#### G1 状态加载门（THINK 阶段开始）

* **通过条件**: 15个动态轨文件全部成功读取

* **核心动作**: 按序读取15个文件 → 组装「章节卡」（含章号/摘要/大纲/人物/节奏/伏笔/角色状态/事实/套路/钩子/情感/副线/创意卡）

* **失败处理**: 文件缺失→从templates初始化；状态不一致→以最近G7落盘为准覆盖

* **读取顺序**: [ORCHESTRATOR.md §三·G1](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/ORCHESTRATOR.md#L392-L425)

#### G2 模仿学习门（DRAFT 前）

* **通过条件**: 样本库≥1个匹配样本 + 特征卡提取完成

* **核心动作**:

  1. 每10章刷新一次样本库（WebSearch搜索同类爆款片段）
  2. 提取入场方式/章末钩子类型/对话占比/σ²/TTR/EGR/Pσ²参考值
  3. 根据本章类型（爽点/过渡/情感/爆点）匹配最合适样本

* **失败处理**: 样本库空→用默认特征卡（σ²≥150, TTR≥0.55, EGR≤1.5, Pσ²≥400）

#### G3 写作门（DRAFT 阶段）

* **通过条件**: 草稿字数1200-1500 + 禁词扫描0命中 + 章末有钩子

* **核心动作**:

  1. 调用写作Agent（writer.md），传入完整章节卡
  2. 产出 `chapters/chN_draft.md`（3位零填充章号）
  3. 主编扫描禁词：前3章0容忍，后续章节≤2个放行

* **写作约束**: σ²≥120 / TTR≥0.48 / EGR≤2.0 / Pσ²≥300 / 对话占比15%-40% / 指纹≥2次/章

#### G4 平台规则门（VERIFY 阶段1/3）

* **检查清单**（7项）:

  1. 单章字数: 1200-1500字（chapter-word-counter.py验证）
  2. 3章一小爽: 距上次爽点≤3章
  3. 10章一大爆: 距上次爆点≤10章
  4. 憋屈不超2章: 主角受委屈≤连续2章
  5. 章末钩子: 有悬念/反转/预告
  6. 意识形态合规: 不渲染系统性歧视
  7. 前后章衔接: 与上一章结尾自然衔接

#### G5 量化指标门（VERIFY 阶段2/3）

* **B组章级指标**（必达）:

  | 指标  | 计算公式        | 门限    | AI区间  | 人写区间  |
  | --- | ----------- | ----- | ----- | ----- |
  | σ²  | 句长方差（标准差）   | ≥120  | <80   | >150  |
  | TTR | 独特词数/总词数    | ≥0.48 | <0.42 | >0.55 |
  | EGR | 笼统情感词数/感官词数 | ≤2.0  | >3.0  | <1.5  |
  | Pσ² | 段落长度方差      | ≥300  | <200  | >400  |

* **C组卷级指标**（每10章检查）: Cσ²≥1.0（连接词密度方差）/ Iσ²≥1.8（信息密度方差）/ FP≥2（指纹匹配）

* **工具调用**: `python tools/metrics.py chapters/chN_draft.md [--fingerprint fingerprint.json]`

#### G6 动态轨一致性门（VERIFY 阶段3/3）

* **检查清单**（7项，D组优先于A/B）:

  1. 人物Soul Field一致性: 行为不违背铁律
  2. 人物声音区分度: 遮标签能认出说话人
  3. 伏笔一致性: 种植/回收在登记表中
  4. 时间线一致性: 与已确立事实无矛盾
  5. 世界观一致性: 不违反已确立规则
  6. 副线编织: 本章推进≥1条副线
  7. 前后文衔接: 开头与上章结尾衔接

* **硬约束**: D组不通过即使A/B达标也不准入库

#### G7 状态落盘门（章末收尾）

* **12项 WRITE-CHECK**（必须全部完成才算一章结束）:

| #   | 操作      | 目标文件                                      | 验证方式                               |
| --- | ------- | ----------------------------------------- | ---------------------------------- |
| 1   | 写入终稿    | `chapters/chN_final.md`                   | 文件存在且非空                            |
| 2   | 字数检查    | -                                         | chapter-word-counter.py: 1200-1500 |
| 3-6 | 指标验证    | -                                         | metrics.py: σ²/TTR/EGR/Pσ² 达标      |
| 7   | 指纹验证    | -                                         | metrics.py --fingerprint: FP≥2     |
| 8   | 章号+1    | `dynamic/progress.md`                     | 读取确认                               |
| 9   | 更新角色状态  | `dynamic/character-state.md`              | 读取确认                               |
| 10  | 更新伏笔    | `dynamic/foreshadowing.md`                | 读取确认                               |
| 11  | 更新钩子+套路 | `dynamic/next-hook.md` + `used-tropes.md` | 读取确认                               |
| 12  | 门禁日志    | `dynamic/gate-log.md`                     | 读取确认                               |

* **其余动态轨更新**: summaries.md / established-facts.md / emotion-beat.md / subplot-tracker.md / compliance-log.md / 00\_INDEX.md

### 5.3 REVISE 打回升级机制

质检不通过时的处置策略（最多4次）：

| 打回次数     | 处置动作                            |
| -------- | ------------------------------- |
| 通过（轻微问题） | 主编局部修改 → 写入chN\_final.md        |
| 第1次打回    | REVISE 局部修改（修改问题段落）             |
| 第2次打回    | DRAFT 全章重写（从头生成）                |
| 第3次打回    | 触发创意扰动Agent → 注入变量到decisions.md |
| 第4次打回    | 升级G8人工审核（暂停流程等用户）               |

### 5.4 10章阶段质检（每10章触发一次）

当章号N为10的倍数时，额外执行14项检查：

1. 质检Agent二道闸清单 → stageN\_qa.md
2. 运营优化Agent复检"贴"度
   3-7. 核对character-state / established-facts / used-tropes / next-hook / foreshadowing
3. **同质化检测**: `metrics.py chN-9_final.md...chN_final.md --perturb`（σ²下降+EGR上升→注入扰动）
4. C组卷级指标（Cσ²/Iσ²）
5. **SC文风稳定性**: `metrics.py ... --stability`（SC<0.6→以稳定章节为基准重写漂移章）
   11-14. 情感疲劳检测 / 副线频率全量核对 / 样本库刷新 / 合规日志审查

***

## 6. 15条动态轨说明

**模板目录**: [novel-system/dynamic/templates/](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/)

### 6.1 进度与摘要类（2文件）

| 文件名                                                                                                                 | 用途                | 预警机制 | G1读 | G7写     |
| ------------------------------------------------------------------------------------------------------------------- | ----------------- | ---- | --- | ------- |
| [progress.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/progress.md)   | 当前阶段、章号、卷号、步骤完成状态 | —    | ✅   | ✅（章号+1） |
| [summaries.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/summaries.md) | 最近5章压缩摘要（每章约200字） | —    | ✅   | ✅（追加）   |

### 6.2 故事追踪类（5文件）

| 文件名                                                                                                                                 | 用途                                        | 预警机制                     | G1读 | G7写   |
| ----------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- | ------------------------ | --- | ----- |
| [foreshadowing.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/foreshadowing.md)         | 伏笔种植/回收记录（含章号）                            | **>20章未回收标黄，>40章标红强制处理** | ✅   | ✅     |
| [character-state.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/character-state.md)     | 各角色：情绪/物理状态/位置/关系/已知信息/代价累积/Soul Field压力点 | —                        | ✅   | ✅     |
| [established-facts.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/established-facts.md) | 已确立事实：世界观/时间线/地理/数字/角色背景                  | 防自相矛盾（G6比对）              | ✅   | ✅（追加） |
| [used-tropes.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/used-tropes.md)             | 套路使用日志：套路名+变体描述+使用章号                      | **冷却期检查**（未到期→使用显著变体）    | ✅   | ✅     |
| [next-hook.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/next-hook.md)                 | 待回报钩子清单 + 章尾钩子规划                          | 钩子逾期未回报预警                | ✅   | ✅     |

### 6.3 节奏与结构类（3文件）

| 文件名                                                                                                                             | 用途                       | 预警机制                    | G1读    | G7写         |
| ------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ----------------------- | ------ | ----------- |
| [emotion-beat.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/emotion-beat.md)       | 情感弧线状态：主情绪/曲线位置/触发点/情感代偿 | **连续3章同方向→强制调整**        | ✅      | ✅           |
| [subplot-tracker.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/subplot-tracker.md) | 副线追踪：当前阶段/出场章号/待回收线索     | **>5章未出场标黄，每8章必须出场≥1次** | ✅      | ✅           |
| [decisions.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/decisions.md)             | 创意扰动提案 + 重大决策记录          | —                       | ✅（取最新） | ✅（同质化检测触发时） |

### 6.4 质量与风格类（3文件）

| 文件名                                                                                                                           | 用途                                         | 预警机制            | G1读       | G7写       |
| ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | --------------- | --------- | --------- |
| [sample-library.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/sample-library.md) | 模仿样本特征卡库：σ²/TTR/EGR/Pσ²+入场方式+钩子类型          | **容量上限5个，定期刷新** | ✅（G2读）    | ✅（每10章刷新） |
| [fingerprint.json](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/fingerprint.json)   | 角色语言指纹：口头禅/phrases/标志性动作/actions           | —               | ✅（G2+G5读） | ✅（阶段0初始化） |
| [00\_INDEX.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/00_INDEX.md)            | 总索引：核心创意卡同步 + static/dynamic文件状态 + 8张追踪表索引 | 北极星同步校验         | ✅（校验）     | ✅（索引更新）   |

### 6.5 日志与合规类（2文件）

| 文件名                                                                                                                           | 用途                        | 预警机制       | G1读         | G7写        |
| ----------------------------------------------------------------------------------------------------------------------------- | ------------------------- | ---------- | ----------- | ---------- |
| [compliance-log.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/compliance-log.md) | 合规日志：AI占比/原创度/查重/敏感词/意识形态 | 章级+全书审查    | ✅（G4读）      | ✅（G4+G7追加） |
| [gate-log.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/dynamic/templates/gate-log.md)             | 门禁通过记录：各门禁通过/失败+时间+原因     | **断点恢复依据** | ✅（确认上章G7通过） | ✅（每门禁追加）   |

***

## 7. 10个角色Agent提示词

### 7.1 阶段0规划角色（前7个）

#### 7.1.1 写作Agent (writer.md) — 最核心的生产角色

**文件**: [static/prompts/writer.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/static/prompts/writer.md)

**工作流程5步**:

1. **LOAD-CHECK**：读7个热轨文件 → 输出「章节交接清单」（硬约束：未输出禁止写章）
2. **章节结构设计**：四段式 入场200字→升温400字→爆点500字→余韵+钩子200字
3. **正文写作执行**：

   * 句式节奏: 长短句交替σ²≥150，每段3-5句

   * 对话设计: 占比≥30%，潜台词设计，声音区分度

   * 感官描写: 笼统词→身体反应（难过→胃紧/嗓子发紧）

   * 指纹注入: ≥2次/章（主角比喻/方言/口头禅）

   * 章末钩子: 必须有悬念驱动翻页
4. **AI味词规避**：禁用"然而/因此/总而言之"等过渡词 + 禁用笼统情感词 + 禁用"她不禁/不由得"句式
5. **章节衔接**：前100字交代时间地点动作，上章钩子前300字内回应

**输出格式**: `# 第N章: [标题]` + 正文1200-1500字 + 本章元数据（字数/爽点标注/温度档位/钩子/伏笔/指纹/情感线）

#### 7.1.2 质检Agent (qc.md) — 把关角色

**文件**: [static/prompts/qc.md](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/static/prompts/qc.md)

**三组检查全覆盖**:

* **A组合规**（5项硬性）: AI占比≤30% / 原创度≥70% / 查重≤2处（metrics.py --plagiarism）/ 红线词0处 / 意识形态合规

* **B组人写特征**（5项指标）: σ²/TTR/EGR/Pσ²/FP 全部用 metrics.py 计算，禁止目测

* **D组状态一致性**（7项，**优先于A/B**）: 事实/套路/钩子/角色/副线/时间线/伏笔 — 不通过即使A/B达标也不准入库

* **前3章专项**（5项强制）: 300字冲突密度 / 钩子强度 / 第3章有爽点 / AI味分≤30 / 人设一致

**输出**: QA报告（含A/B/D三组表格 + 准入库判定 + 具体修改建议，每项问题必须给位置+问题+方法）

***

## 8. 工具脚本详解

### 8.1 metrics.py — 人写特征度量工具（最核心）

**文件**: [tools/metrics.py](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/tools/metrics.py)

**语言**: Python 3.10+（标准库 + 可选jieba分词）

#### 8.1.1 词库常量

| 词库                    | 数量  | 用途                                                                              |
| --------------------- | --- | ------------------------------------------------------------------------------- |
| `VAGUE_EMOTION_WORDS` | 80+ | AI常用笼统情感词（难过/开心/紧张/焦虑/尴尬/憋屈/心累...）+ 川渝方言情感词（冒火/巴适/心欠欠...）                       |
| `SENSORY_WORDS`       | 80+ | 人写具体感官词（胃紧/手凉/心跳加速/后背发凉/视野发白...）+ 川渝身体感受（脚杆打闪闪/脑壳昏...）+ 程序员术语（CPU烧了/脑子宕机/蓝屏...） |
| `TRANSITION_WORDS`    | 14  | 过渡/连接词（然而/因此/于是/不过/综上所述...）— Cσ²计算用                                             |

#### 8.1.2 核心计算函数

| 函数                                                   | 签名                             | 返回值          | 用途                             |
| ---------------------------------------------------- | ------------------------------ | ------------ | ------------------------------ |
| `split_sentences(text)`                              | `str → list[str]`              | 句子列表         | 按句号/问号/感叹号/省略号分句，过滤<2字短句       |
| `split_paragraphs(text)`                             | `str → list[str]`              | 段落列表         | 按换行分段                          |
| `tokenize(text)`                                     | `str → list[str]`              | 词列表          | 优先jieba分词→退化按字符（TTR计算用）        |
| `calc_sentence_length_variance(sentences)`           | `list[str] → float`            | σ²值          | 句长方差标准差（句式多样性）                 |
| `calc_ttr(text)`                                     | `str → float`                  | TTR值         | 独特词/总词（用词丰富度）                  |
| `calc_egr(text)`                                     | `str → float`                  | EGR值         | 子串匹配（不分词）统计笼统词/感官词比值           |
| `calc_paragraph_length_variance(paragraphs)`         | `list[str] → float`            | Pσ²值         | 段落长度方差标准差（段落节奏）                |
| `calc_transition_density_variance(paragraphs)`       | `list[str] → float`            | Cσ²值         | 连接词密度方差                        |
| `calc_info_density_variance(paragraphs)`             | `list[str] → float`            | Iσ²值         | 信息密度方差（长度>1词占比）                |
| `calc_fingerprint_match(text, fingerprint)`          | `str, dict → tuple[int, dict]` | (FP次数, 命中详情) | 语言指纹匹配计数                       |
| `calc_style_stability(metrics_list)`                 | `list[dict] → float`           | SC值(0-1)     | 跨章文风稳定性（多章指标相对均值偏差）            |
| `calc_plagiarism_check(text_a, text_b, min_ngram=8)` | `str, str, int → list[str]`    | 雷同片段列表       | 查重自检：连续8字以上雷同                  |
| `detect_homogenization(chapter_files)`               | `list[str] → dict`             | 检测报告         | 多章同质化检测（开头单调性/结构单调性/指标趋势/中段停滞） |

#### 8.1.3 门限阈值 THRESHOLDS

```python
THRESHOLDS = {
    "sigma2":  {"min": 25,   "ai": "<15",   "human": ">15"},   # 注意：ORCHESTRATOR.md定义门限为≥120
    "ttr":     {"min": 0.25, "ai": "<0.15",  "human": ">0.15"}, # 注意：ORCHESTRATOR.md定义门限为≥0.48
    "egr":     {"max": 0.60, "ai": ">0.60",  "human": "<0.50"},# 注意：ORCHESTRATOR.md定义门限为≤2.0
    "psigma2": {"min": 80,   "ai": "<50",   "human": ">50"},   # 注意：ORCHESTRATOR.md定义门限为≥300
    "csigma2": {"min": 1.0,  "ai": "<0.5",  "human": ">1.5"},
    "isigma2": {"min": 1.8,  "ai": "<1.0",  "human": ">2.5"},
    "fp":      {"min": 2,    "ai": "=0",    "human": ">3"},
    "sc":      {"min": 0.75, "ai": "<0.6",  "human": ">0.85"},
}
```

> ⚠️ **注意**: metrics.py 内部阈值（σ²≥25等）与 ORCHESTRATOR.md 定义的门禁阈值（σ²≥120等）不一致，实际以 ORCHESTRATOR.md 的门禁规则为准。metrics.py 的 check\_threshold 用于提供纠正建议的基准。

#### 8.1.4 纠正建议 CORRECTIONS

| 指标不达标 | 建议操作                      |
| ----- | ------------------------- |
| σ²低   | 插入3-5字短句打断节奏，或将长句拆为两句     |
| TTR低  | 替换高频词的30%为同义词，加入个人习惯用语    |
| EGR高  | 将笼统词替换为具体感官描写（胃紧/手凉/视野发白） |
| Pσ²低  | 合并或拆分段落，制造长短段交替           |
| FP少   | 植入口头禅/标志性动作，每章≥2次         |
| SC低   | 识别漂移最大的章节，以稳定章节为基准重写      |

#### 8.1.5 同质化检测 PERTURB\_ACTIONS

检测到问题时的创意扰动建议库（给选项不替决定）：

| 问题类型             | 扰动选项                 |
| ---------------- | -------------------- |
| 开头单调性（连续3章同开头）   | 视角偏移/对话开场/时间错位/静默开场  |
| 结构单调性（连续3章同结构指纹） | 留白章/物件叙事/揭秘章结构/日常章结构 |
| 指标下降（σ²/Pσ²持续下降） | 短句穿插/感官词注入/段落重组      |
| EGR上升（情感趋于笼统）    | 感官替换/触觉优先            |
| 中段停滞（σ²波动过小）     | 主线扰动/副线激活/反派行动       |

#### 8.1.6 CLI 用法

```bash
# 基础分析（文本报告）
python tools/metrics.py chapters/ch001.md

# JSON输出（便于其他工具调用）
python tools/metrics.py chapters/ch001.md --json

# 带语言指纹匹配
python tools/metrics.py chapters/ch001.md --fingerprint dynamic/fingerprint.json

# 模仿评价（对比样本）
python tools/metrics.py chapters/ch001.md --compare samples/best_seller_ch1.txt

# 查重自检（连续8字雷同）
python tools/metrics.py chapters/ch001.md --plagiarism samples/best_seller_ch1.txt

# 文风稳定性（跨章SC系数）
python tools/metrics.py ch048.md ch049.md ch050.md --stability

# 同质化检测+创意扰动建议
python tools/metrics.py ch048.md ch049.md ch050.md --perturb
```

***

### 8.2 chapter-word-counter.py — 章节字数统计工具

**文件**: [tools/chapter-word-counter.py](file:///c:/Users/Administrator/Desktop/novel-ops-v1.0.0/novel-system/tools/chapter-word-counter.py)

**语言**: Python 3.10+（仅标准库，无第三方依赖）

#### 8.2.1 核心函数

| 函数                                        | 签名                              | 用途                                                  | <br />             |
| ----------------------------------------- | ------------------------------- | --------------------------------------------------- | ------------------ |
| `count_chinese_chars(text)`               | `str → int`                     | 统计CJK中文字符（排除标点/空白/英文/数字），用正则匹配U+4E00-U+9FFF等5个CJK区块 | <br />             |
| `count_all_chars(text)`                   | `str → int`                     | 统计所有可见字符（排除空白）                                      | <br />             |
| `analyze_file(filepath)`                  | `str → dict`                    | 分析单文件：返回中文字数/总字符/可见字符/行数+错误信息                       | <br />             |
| `check_standard(char_count, min, max)`    | `int,int,int → tuple[bool,str]` | 检查是否在字数范围内（不足/超标/达标）                                | <br />             |
| `_render_bar(count, min, max, bar_width)` | `int*4 → str`                   | 可视化进度条：\`---======                                  | ====---\` 形式显示当前位置 |
| `expand_files(patterns)`                  | `list[str] → list[str]`         | glob通配符展开（Windows shell不自动展开时用）                     | <br />             |
| `results_to_json(results, min, max)`      | `list, int, int → str`          | 批量结果转JSON（含时间戳/标准/汇总/逐文件详情）                         | <br />             |

#### 8.2.2 默认字数标准

```python
DEFAULT_MIN_WORDS = 2600  # 番茄小说平台标准最低
DEFAULT_MAX_WORDS = 3300  # 番茄小说平台标准最高
```

> ⚠️ **注意**: 此脚本默认标准为2600-3300字，但 ORCHESTRATOR.md + writer.md 中定义的单章标准为 **1200-1500字**。使用时需用 `--min 1200 --max 1500` 参数覆盖默认值。

#### 8.2.3 CLI 用法

```bash
# 单章统计（默认2600-3300）
python tools/chapter-word-counter.py chapters/ch001.md

# 单章统计（番茄1200-1500标准）
python tools/chapter-word-counter.py chapters/ch001.md --min 1200 --max 1500

# 多章批量 + JSON输出 + 安静模式（只显示不达标的）
python tools/chapter-word-counter.py chapters/ch001.md chapters/ch002.md --json --quiet

# glob通配符批量统计（Windows需加引号）
python tools/chapter-word-counter.py "chapters/ch*.md" --min 1200 --max 1500
```

***

## 9. 数据流与状态管理

### 9.1 状态读写矩阵

| 动态轨文件                | G1读    | G2读    | G3写    | G4读    | G5读    | G6读    | G7写    | 10章质检  | 门禁4终审   |
| -------------------- | ------ | ------ | ------ | ------ | ------ | ------ | ------ | ------ | ------- |
| progress.md          | ✅      | <br /> | <br /> | <br /> | <br /> | <br /> | ✅章号+1  | <br /> | <br />  |
| summaries.md         | ✅      | <br /> | <br /> | <br /> | <br /> | <br /> | ✅追加    | <br /> | <br />  |
| foreshadowing.md     | ✅      | <br /> | <br /> | <br /> | <br /> | ✅核对    | ✅      | ✅超期核对  | ✅全量回收   |
| decisions.md         | ✅      | <br /> | <br /> | <br /> | <br /> | <br /> | <br /> | ✅注入    | <br />  |
| character-state.md   | ✅      | <br /> | <br /> | <br /> | <br /> | ✅核对    | ✅      | ✅核对    | ✅全量     |
| established-facts.md | ✅      | <br /> | <br /> | <br /> | <br /> | ✅核对    | ✅      | ✅核对    | ✅全量     |
| used-tropes.md       | ✅      | <br /> | <br /> | <br /> | <br /> | ✅核对    | ✅      | ✅分布检查  | ✅全量     |
| next-hook.md         | ✅      | <br /> | <br /> | <br /> | <br /> | ✅核对    | ✅      | ✅进度    | ✅全量回报   |
| emotion-beat.md      | ✅      | <br /> | <br /> | <br /> | <br /> | <br /> | ✅      | ✅疲劳检测  | ✅完整性    |
| subplot-tracker.md   | ✅      | <br /> | <br /> | <br /> | ✅出场频率  | ✅核对    | ✅      | ✅频率全量  | ✅全量收束   |
| sample-library.md    | <br /> | ✅刷新    | <br /> | <br /> | <br /> | <br /> | <br /> | ✅刷新    | <br />  |
| fingerprint.json     | <br /> | ✅      | <br /> | <br /> | ✅FP计算  | <br /> | <br /> | <br /> | <br />  |
| compliance-log.md    | <br /> | <br /> | <br /> | ✅写入    | <br /> | <br /> | ✅追加    | ✅审查    | ✅终检     |
| gate-log.md          | ✅上章G7  | <br /> | <br /> | ✅G4记录  | ✅G5记录  | ✅G6记录  | ✅G7记录  | <br /> | <br />  |
| 00\_INDEX.md         | ✅      | <br /> | <br /> | <br /> | <br /> | <br /> | ✅      | <br /> | ✅创意卡一致性 |

### 9.2 章节循环数据流

```
                ┌─────────────────────────────────────────────────┐
                │              G1 状态加载门                      │
                │  从15个动态轨 + 6个静态轨 读取 → 组装「章节卡」  │
                └────────────────────────┬────────────────────────┘
                                         │
                                         ▼
                ┌─────────────────────────────────────────────────┐
                │              G2 模仿学习门                      │
                │  sample-library.md + fingerprint.json           │
                │  → 提取样本特征卡(σ²/TTR/EGR/Pσ²参考值)         │
                └────────────────────────┬────────────────────────┘
                                         │
                                         ▼
                ┌─────────────────────────────────────────────────┐
                │              G3 写作门                          │
                │  调用写作Agent → chapters/chN_draft.md          │
                │  + 禁词扫描(前3章0容忍, 后续≤2个)               │
                └────────────────────────┬────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
          ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
          │ G4 平台规则门  │  │ G5 量化指标门  │  │ G6 一致性门    │
          │ (A组合规7项)   │  │ (B组指标5项)   │  │ (D组一致性7项) │
          │ +合规日志追加  │  │ +metrics.py    │  │ +7维一致性核对 │
          │                │  │ 调用          │  │                │
          └────────┬───────┘  └────────┬───────┘  └────────┬───────┘
                   │                   │                   │
                   └───────────────────┼───────────────────┘
                                       │ 三组全通过
                                       ▼
                           ┌───────────────────────────┐
                           │  REVISE 阶段              │
                           │  QA报告处置建议           │
                           │  · 轻微: 主编局部修改     │
                           │  · 第1次: 局部重写        │
                           │  · 第2次: 全章重写        │
                           │  · 第3次: 创意扰动注入    │
                           │  · 第4次: 升级G8人工      │
                           └─────────────┬─────────────┘
                                         │ 修改完成
                                         ▼
                ┌─────────────────────────────────────────────────┐
                │              G7 状态落盘门（12项WRITE-CHECK）    │
                │                                                   │
                │  1. chN_final.md 写入 ✓                          │
                │  2-7. 字数 + 5项指标 工具验证 ✓                   │
                │  8. progress.md 章号+1 ✓                         │
                │  9. character-state.md 更新 ✓                    │
                │  10. foreshadowing.md 更新 ✓                     │
                │  11. next-hook + used-tropes 更新 ✓              │
                │  12. gate-log 更新 ✓                             │
                │                                                   │
                │  + 追加更新: summaries / facts / emotion /       │
                │             subplot / compliance / 00_INDEX       │
                └─────────────────────────────────────────────────┘
                                         │
                                         ▼
                                   进入下一章G1
```

***

## 10. 依赖关系

### 10.1 外部依赖

| 依赖                     | 是否必需  | 版本要求  | 用途                                 | 安装命令                                |
| ---------------------- | ----- | ----- | ---------------------------------- | ----------------------------------- |
| **TRAE / Claude Code** | ✅ 必需  | 最新版   | 运行 NovelOps v2 Skill 的 AI Agent 宿主 | 官网下载                                |
| **Python**             | ⚠️ 推荐 | 3.10+ | 运行 tools/ 下3个量化脚本                  | `https://www.python.org/downloads/` |
| **jieba**              | ⚠️ 推荐 | 最新    | TTR分词（缺则降级按字符计算，精度降低）              | `pip install jieba`                 |
| **Git**                | ❌ 可选  | -     | 动态轨版本管理（纯文本可diff）                  | 官网下载                                |

### 10.2 内部模块依赖图

```
SKILL.md (入口)
  └── 调用 ORCHESTRATOR.md (主编调度)
        ├── 阶段0 → 调用 static/prompts/*.md (10个Agent)
        │     ├── topic-market.md → 用 WebSearch + WebFetch 工具
        │     ├── topic.md
        │     ├── material-prep.md
        │     ├── outline.md
        │     ├── characters.md → 写入 dynamic/fingerprint.json
        │     ├── pacing.md
        │     ├── operations.md
        │     └── creative-disruption.md → 写入 dynamic/decisions.md
        │
        └── 章节循环 (G1-G7)
              ├── G1 → 读 15个 dynamic/*.md + 6个 static/*.md
              ├── G2 → 读 sample-library.md + fingerprint.json
              ├── G3 → 调用 writer.md → 写 chapters/chN_draft.md
              ├── G4 → 调用 qc.md + 调用 chapter-word-counter.py
              │         → 写 compliance-log.md + gate-log.md
              ├── G5 → 调用 qc.md + 调用 metrics.py (B组+C组+FP)
              │         → 写 gate-log.md
              ├── G6 → 调用 qc.md → 读全部动态轨核对 + 写 gate-log.md
              └── G7 → 写 chapters/chN_final.md
                        + 写 15个 dynamic/*.md (12项WRITE-CHECK)
                        + 调用 metrics.py (验证)
                        + 调用 chapter-word-counter.py (验证)
```

### 10.3 文件间依赖关系

| 文件类别            | 依赖源                               | 产生者                                  | 消费者                    |
| --------------- | --------------------------------- | ------------------------------------ | ---------------------- |
| **核心创意卡**       | 作者输入                              | 步骤2.5协作                              | 全流程每一步（北极星约束）          |
| **Static轨**     | 市场数据+作者偏好+AI生成                    | 阶段0各Agent                            | 章节循环G1+G2+G3+G6        |
| **Dynamic轨初始化** | static/outline.md + characters.md | 门禁1通过后AI提取                           | 章节循环每章G7更新             |
| **章节草稿**        | 15动态轨+6静态轨+样本特征卡                  | G3写作Agent                            | G4/G5/G6质检             |
| **章节终稿**        | 草稿+QA报告                           | REVISE修改后G7                          | 下一章G1上下文衔接 + publish导出 |
| **QA报告**        | 草稿+metrics输出+热轨                   | 质检Agent                              | REVISE阶段修改参考           |
| **量化数据**        | 章节文本                              | metrics.py / chapter-word-counter.py | G4/G5/G7门禁判定           |

***

## 11. 项目运行方式

### 11.1 环境准备

#### A. 安装 TRAE + NovelOps v2 技能（必做）

**方法一：TRAE界面导入zip（最简单）**

1. 下载安装 TRAE: `https://www.trae.cn/ide/download`（或TraeWork）
2. 登录 TRAE 账号
3. **设置 → 技能与命令 → 创建 → 全局**
4. 直接上传 `novel-ops-v1.0.0.zip`（zip根目录含SKILL.md）
5. 确认技能面板出现 **novelOps-v2**

**方法二：复制到全局技能目录（推荐，便于后续编辑模板）**

```powershell
# 打开技能目录
explorer %userprofile%\.trae-cn\skills

# 把解压后的整个项目目录复制进去，目录名必须是 novelOps-v2
xcopy /E /I "D:\Downloads\novel-ops-v1.0.0" "%userprofile%\.trae-cn\skills\novelOps-v2"

# 重启TRAE或新建对话 → 技能生效
```

#### B. 安装 Python 环境（推荐，用于量化质检）

```powershell
# 1. 安装 Python 3.10+ (官网下载，勾选 Add to PATH)
python --version  # 验证

# 2. 安装 jieba 分词（metrics.py TTR精度提升）
pip install jieba

# 3. 验证
cd novel-system
python tools/metrics.py --help
python tools/chapter-word-counter.py --help
```

### 11.2 首次运行完整流程

#### Step 1: 准备小说项目工作目录

```powershell
# 方式A：把 novel-system 整体复制为项目目录
xcopy /E /I "%userprofile%\.trae-cn\skills\novelOps-v2\novel-system" "D:\my-novel-project"

# 方式B：手动初始化 dynamic 目录
mkdir D:\my-novel-project\dynamic
xcopy /E /I "%userprofile%\.trae-cn\skills\novelOps-v2\novel-system\dynamic\templates\*" "D:\my-novel-project\dynamic\"
# 并把 tools/, static/, ORCHESTRATOR.md 复制到项目目录
```

在 TRAE 中打开 `D:\my-novel-project` 目录，开启对话。

#### Step 2: 启动新书 → 阶段0全局规划

对 Agent 说：

```
启动新书
```

Agent 会自包含地执行：

1. 环境确认 → 初始化 dynamic/（如果为空）
2. 选题市场Agent → 生成 `static/market_research.md`
3. 选题Agent → 生成 `static/topic.md`
4. 与你协作填写 **核心创意卡5项**（城市/行业/核心能力/核心矛盾/创意差异化）→ 写入 `00_INDEX.md`
5. 素材准备Agent → 行业/打脸/情感三大素材库
6. 大纲Agent → 三幕结构200-330章大纲
7. 人物Agent → 每人Soul Field铁律+语言指纹
8. 节奏Agent → 爽点/爆点/张弛比规划
9. 运营Agent → 书名/简介/标签
10. 创意扰动Agent → 同质化检查+扰动建议

**停在门禁1，等你审核通过。**

#### Step 3: 门禁1审核 → 前3章特殊流程

审核8项文件后，对 Agent 说：

```
通过
```

进入前3章写作：

* 双重G5指标检查（需达到人写区间：σ²>150, TTR>0.55, EGR<1.5, Pσ²>400）

* 前300字必须直接冲突切入（砍掉所有铺垫）

* 第1章：重生触发+初次打脸

* 第2章：打脸升级+情感线种子

* 第3章：第一个小爽点释放

**停在门禁2，强制等你确认。**

#### Step 4: 门禁2通过 → 章节循环模式

通过后，之后每章只需说一句话：

```
写下一章
```

Agent 会自动执行 G1-G7 完整循环：

```
G1加载15轨 → G2提取样本特征 → G3写草稿 → G4/G5/G6质检 → 
(打回重写≤3次) → G7更新15轨+写终稿 → 完成
```

每章约几秒钟内完成全部自动流程（写作+质检+落盘），期间无需任何人工干预。

#### Step 5: 可选 — 手动查看质检数据

```powershell
cd D:\my-novel-project

# 单章量化指标报告
python tools/metrics.py chapters/ch001_final.md

# 多章文风稳定性（最近10章）
python tools/metrics.py chapters/ch041_final.md chapters/ch042_final.md ... chapters/ch050_final.md --stability

# 同质化检测+创意扰动建议
python tools/metrics.py chapters/ch041_final.md ... chapters/ch050_final.md --perturb

# 字数批量检查
python tools/chapter-word-counter.py "chapters/ch*_final.md" --min 1200 --max 1500
```

#### Step 6: 门禁3（约50%进度）+ 门禁4（全书终审）

到达约50%进度时，Agent会自动停在门禁3等你审核；全部写完后执行14项终审检查，停在门禁4。通过后执行：

1. 三级敏感词检测
2. 按番茄小说格式导出到 `publish/fanqie/`

### 11.3 会话中断后恢复

会话意外断开后，只需对 Agent 说：

```
继续写作
```

Agent 自动恢复流程：

1. 读 `dynamic/progress.md` → 确定断点章号
2. 读 `dynamic/gate-log.md` → 确定断点处门禁状态
3. 读15个动态轨 → 恢复全部状态
4. 从断点处未通过的门禁继续执行

***

## 12. 故障恢复机制

### 12.1 会话断开恢复（最常见）

| 中断位置         | 恢复依据                           | 恢复动作          |
| ------------ | ------------------------------ | ------------- |
| G3写作中断       | `chapters/chXXX_draft.md` 是否存在 | 读草稿继续，或重写     |
| G4/G5/G6质检中断 | `gate-log.md` 中该门禁状态           | 重新执行当前门禁      |
| G7落盘中断       | 检查哪些WRITE-CHECK已落盘             | 补全未完成项，不重复已完成 |
| 上章G7已通过      | `progress.md` 章号               | 正常开始下一章G1     |

### 12.2 子Agent调用失败处理

| 失败类型                     | 处理策略                                   |
| ------------------------ | -------------------------------------- |
| **工具不存在**（如metrics.py缺失） | 打印警告 → 使用内置简化逻辑替代 → 记录到gate-log.md     |
| **工具执行超时**               | 重试1次 → 仍超时则跳过该项检查 → 标记"待人工确认"          |
| **工具输出异常**               | 记录原始输出到decisions.md → 请求人类确认           |
| **依赖缺失**（如jieba未装）       | 使用降级方案（TTR按字符计算）→ 打印警告                 |
| **子Agent（写作/质检）失败**      | 自动重试1次 → 仍失败则主编读对应prompt，在当前会话中扮演该角色完成 |

> **铁律**: 工具失败/子Agent失败 **均不中断创作流程**，仅在gate-log.md标记，下次会话优先修复。

### 12.3 门禁连续失败处理

某门禁连续3次未通过时：

1. 记录失败原因到 `gate-log.md`
2. **暂停当前章节**写作循环
3. 向用户报告：失败原因 + 建议修改方向
4. 等待用户指示（重写/跳过/修改大纲/调整参数）
5. 用户确认后从G1重新开始当前章

### 12.4 每章启动自检清单

启动每章G1前自动检查：

* [ ] `dynamic/progress.md` 可读

* [ ] 15个动态轨文件存在（不存在则从templates初始化）

* [ ] `gate-log.md` 上一章 G1-G7 全部通过记录

* [ ] `static/core_creative_card.md` 可读（北极星存在）

* [ ] 3个工具脚本存在（不存在则走降级逻辑）

***

## 13. 设计原则与约束优先级

### 13.1 六大执行原则

| 原则           | 说明                                                   |
| ------------ | ---------------------------------------------------- |
| **一次一章**     | 每轮对话只推进一个章节的完整循环（THINK→DRAFT→VERIFY→REVISE→G7），不批量生成 |
| **门禁必过**     | G1-G7 全部通过才进入下一章；任何门禁未通过不得进入下一阶段                     |
| **用户只审G8**   | G1-G7全自动；4个关键门禁（门禁1/2/3/4）暂停等用户；前3章强制门禁2审核           |
| **状态落盘优先**   | 宁可多写一次文件，不可丢失状态；G7的12项WRITE-CHECK完成才算一章结束            |
| **故障不阻塞**    | 子Agent失败/工具失败均走降级路径，不中断创作主流程                         |
| **核心创意卡北极星** | 5项核心设定（城市/行业/能力/矛盾/差异化）全流程锁定，**AI无权修改**              |

### 13.2 写作约束冲突优先级（高→低）

```
1. 平台合规（违禁词/意识形态） — 一票否决
2. Soul Field 一致性 — 角色铁律不可违背，违背且无铺垫→G6失败
3. 核心创意卡约束 — 5项北极星，偏离即退回重写
4. 节奏铁律（3章爽/10章爆/憋屈≤2章） — 必须满足，G4检查
5. metrics指标门限（σ²/TTR/EGR/Pσ²） — G5必须达标
6. 字数标准（1200-1500） — G3+G4检查
7. 伏笔回收时效（>20标黄/>40标红） — G3+G6检查
8. 文风稳定性（SC≥0.75） — 每10章检查
```

### 13.3 自动化与人工分工

| 环节            | 执行者              | 说明              |
| ------------- | ---------------- | --------------- |
| 选题市场调研        | AI自动执行 + 人工确认    | AI搜索整理数据，用户确认方向 |
| 核心创意卡5项       | 人工填写 + AI格式化     | 作者提供，AI无权修改     |
| 大纲/人物/节奏/运营包装 | AI生成 + 人工确认（门禁1） | AI生成，用户审核通过     |
| 章节写作 G1-G7    | **全自动**          | 门禁自动执行，无需人工干预   |
| 前3章审核         | **强制人工**（门禁2）    | 前三章是签约生死线，必须人工审 |
| 后续章节审核        | 可选人工（默认跳过G8）     | 用户可随时介入，默认全自动   |
| 约50%中段审核      | 人工（门禁3）          | 检查主线推进/人物弧光/节奏  |
| 全书终审          | 人工（门禁4）          | 14项终检后人工确认发布    |
| 故障恢复          | **自动恢复**         | 读状态文件从断点续跑，不丢进度 |

***

## 附录：命令速查表

### 工具脚本

```bash
# ============ metrics.py ============
python tools/metrics.py chapters/ch001.md                          # 基础分析
python tools/metrics.py chapters/ch001.md --json                   # JSON输出
python tools/metrics.py chapters/ch001.md --fingerprint fp.json    # 带语言指纹
python tools/metrics.py ch001.md --compare sample.txt              # 模仿评价
python tools/metrics.py ch001.md --plagiarism sample.txt           # 查重自检
python tools/metrics.py ch048.md ch049.md ch050.md --stability     # 文风稳定性
python tools/metrics.py ch048.md ch049.md ch050.md --perturb       # 同质化检测

# ============ chapter-word-counter.py ============
python tools/chapter-word-counter.py chapters/ch001.md                        # 单章(默认2600-3300)
python tools/chapter-word-counter.py chapters/ch001.md --min 1200 --max 1500  # 番茄1200-1500标准
python tools/chapter-word-counter.py "chapters/ch*.md" --json --quiet         # 批量+JSON+只看不达标
```

### TRAE 对话触发词

| 对话输入                       | 触发动作                    |
| -------------------------- | ----------------------- |
| `启动新书` / `开始新项目` / `从零开始写` | 进入新书模式阶段0，跑全局规划7步骤→停门禁1 |
| `通过` / `可以` / `没问题`        | 当前门禁（G8）通过，进入下一阶段       |
| `这里要改…` / `把XX改成…`         | 当前G8打回，AI按修改意见修订后重新提交   |
| `重来` / `重新规划`              | 废弃本轮阶段0，重新跑全局规划         |
| `写下一章` / `推进章节` / `写第N章`   | 进入章节循环，执行G1-G7写一章       |
| `继续写作` / `继续`              | 会话中断后恢复，从断点门禁继续         |

***

> **文档结束**\
> 本文档基于 novel-ops-v1.0.0 代码库生成，所有文件链接均指向仓库绝对路径。

<br />
