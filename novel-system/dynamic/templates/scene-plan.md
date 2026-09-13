# 场景规划表 (scene-plan)

> 每章写作前由G3步骤2生成，记录本章所有场景的Scene-Sequel结构。
> 场景必须以Disaster结尾，禁止"干净成功"。

---

## 本章场景规划

**章号**：ch000
**章标题**：待定
**场景数量**：0

---

### 场景1

| 要素 | 内容 |
|------|------|
| scene_goal | [POV角色在本场景的具体目标，当前场景内可判断输赢] |
| scene_conflict | [阻碍目标的力量，至少3个层级递进的阻碍] |
| scene_disaster_type | [flat_no / yes_but / no_and_furthermore] |
| scene_disaster_detail | [灾难的具体内容，必须让主角处境变糟] |
| sequel_reaction | [角色对灾难的即时身心反应，实时呈现] |
| sequel_dilemma | [角色面临的两难选项，每条路都有代价] |
| next_scene_goal | [决策生成的下一场景目标] |
| satisfaction_type | [爽点模式：越级反杀/打脸权威/反派翻车/甜蜜超预期/无] |

### 场景2

（如本章有多个场景，复制上方表格填写）

---

## Scene-Sequel循环链

```
场景1 Goal → Conflict → Disaster → Sequel(Reaction→Dilemma→Decision)
  ↓ next_scene_goal
场景2 Goal → Conflict → Disaster → Sequel(Reaction→Dilemma→Decision)
  ↓ next_scene_goal
  ...
```

## 检查清单

- [ ] 每个场景都有明确的Goal（非全局目标，当前场景内可判断输赢）
- [ ] 每个场景的Conflict至少有3个层级递进的阻碍
- [ ] 每个场景以Disaster结尾（flat_no/yes_but/no_and_furthermore）
- [ ] 无"yes"场景（主角干净利落达成目标）
- [ ] Sequel中Reaction是实时呈现，非总结
- [ ] Sequel中Dilemma有两个以上不完美选项
- [ ] Decision生成下一个场景的Goal
