# WorkBuddy 启动说明（NovelOps v2 项目级技能）

> 本文件说明如何在 WorkBuddy 中部署并复现 NovelOps v2 的网文连载流水线环境。
> 适用场景：在当前机器或其他设备上重建一致的 WorkBuddy 工作环境。

## 1. 环境依赖

| 依赖 | 用途 | 安装 |
|---|---|---|
| Python 3.8+（实测 3.13） | 运行 `novel-system/tools/` 下的指标 / 计数器脚本 | 系统自带或官网安装 |
| `jieba` | 中文分词，提升 TTR（用词多样性）指标精度 | `pip install jieba` |
| `aitext_detector` 权重 `models.json`（~107MB） | `--aitext` 模式的 AI 文本占比参考检测 | 手动下载（见 §3），**不入库** |

> 不装 `jieba` 也能跑（TTR 自动降级为按字符计算）；不下载 `models.json` 也能跑（`--aitext` 参考检测被跳过，不影响 7 项硬门禁）。

## 2. 仓库与分支

- **`main`**：跟踪上游源仓库 `git@github.com:kalandramo/novel-ops.git`（`origin/main`），用于同步官方更新。日常不要在 `main` 上直接改业务文件。
- **`workbuddy-env`**：从 `main` 派生，承载 **WorkBuddy 适配层** —— `.workbuddy/skills/novelOps/`（已适配的 `SKILL.md` + 工具模板）以及本启动说明。在 WorkBuddy 中实际使用的是这个分支。

**同步源更新：**
```bash
git checkout main && git pull origin main
git checkout workbuddy-env && git merge main
# 若源 novel-system 模板有更新，手动把根目录 novel-system/ 同步到
# .workbuddy/skills/novelOps/novel-system/
```

## 3. 在另一台设备复现

```bash
git clone git@github.com:kalandramo/novel-ops.git
cd novel-ops
git checkout workbuddy-env
```

用 WorkBuddy 打开该目录，项目级技能 `.workbuddy/skills/novelOps` 会被自动加载。

然后补齐运行时依赖：
```bash
pip install jieba
```

下载 AI 检测权重（仅 `--aitext` 模式需要，非必选）：
- 地址：`https://github.com/lyc8503/AITextDetector/releases/download/model/models.json`
- 大小：约 107 MB（精确 112,338,400 字节）
- 放置到以下两处（第二份保证「新建书」复制模板时一并带权）：
  1. `novel-system/tools/aitext_detector/models.json`
  2. `.workbuddy/skills/novelOps/novel-system/tools/aitext_detector/models.json`

> 若 `github.com` 不可直连，请换可访问 GitHub 的网络后再下；该文件仅在官方 Release 提供，无 raw 镜像。

## 4. 验证安装

```bash
# 基础指标（应输出 7/7 硬门禁通过）
python novel-system/tools/metrics.py samples/human_fanqie_changanshihua_ch1.txt

# 含 AI 检测参考层（权重就位时，会额外输出 AITextDetector(AI占比) 行）
python novel-system/tools/metrics.py samples/human_fanqie_changanshihua_ch1.txt --aitext
```

## 5. 使用

在 WorkBuddy 中直接说：
- **「启动新书」** —— 全局规划（阶段 0 市场调研 → 全局规划，停在门禁 1 等你审）
- **「写下一章」** —— 章节循环（按 `ORCHESTRATOR.md` 协议推进）

## 6. 注意事项

- `models.json`（~107MB）已被 `.gitignore` 排除，不会进版本库；另一台设备需手动下载。
- `.workbuddy/` 下仅 `skills/` 入库，个人记忆（`memory/`）与项目数据（`projects/` 等）不入库。
- `aitext_detector` 对中文网文假阳性偏高（人写样本曾报 80.8%），仅作参考，不直接用于「AI 占比 ≤30%」判定；以 7 项硬门禁为主。
- 本技能的宿主适配：原生的「Task 工具唤起子代理」在 WorkBuddy 中对应 **`Agent` 工具**；阶段 0 调研使用 `WebSearch` / `WebFetch`。
