# 涮涮AI - 上下文工程计划

## 一、现状与目标

### 1.1 当前上下文使用情况

| 场景 | 位置 | 当前上下文内容 |
|------|------|----------------|
| 涮菜顺序排序 | `services/llm_service.py` | **System**：一句「只输出合法 JSON」；**User**：锅底+用户模式+食材列表（名称/分类/时间/技巧）+ 输出格式说明 |

- 无统一「角色/人设」与领域知识注入  
- 无少样本示例（few-shot）  
- 无用户偏好、历史方案等会话上下文  
- 无结构化上下文模板与版本管理  

### 1.2 目标

- **效果**：大模型排序更符合火锅常识、用户模式与锅底差异更明显，输出格式更稳定。  
- **可扩展**：后续新增「健康建议生成」「涮煮技巧解释」等能力时，能复用同一套上下文体系。  
- **可维护**：提示词与领域知识集中管理、可配置、可 A/B 测试。

---

## 二、上下文工程范围

### 2.1 提示词与角色上下文（Prompt & Role）

- **系统角色（System）**：明确「火锅行家 + 只做下锅顺序决策」的人设与边界。  
- **任务说明**：输入是什么、输出是什么、约束（必须包含且仅包含当前食材、先久煮后易熟等）。  
- **输出格式**：严格 JSON schema 或示例，减少 markdown 包裹与多余文字。  

→ 对应：拆分并增强 `_build_sort_prompt`，引入可配置的 system / task 模板。

### 2.2 领域知识上下文（Domain Knowledge）

- **火锅通用原则**：先荤后素、先根茎后叶菜、汤底越煮越咸/嘌呤升高等。  
- **典型技巧**：毛肚/鸭肠「七上八下」、脑花/丸子需久煮、虾滑浮起即熟等。  
- **锅底差异**：麻辣更易熟、番茄偏酸对时间的影响、清汤标准等。  
- **用户模式**：老人/儿童需更熟、快手模式在安全前提下缩短等。  

→ 对应：在 `data/` 或 `services/` 下增加「领域知识」模块（如 `context/knowledge.py` 或 JSON），在构建 prompt 时按需注入。

### 2.3 少样本示例上下文（Few-shot）

- 提供 1～2 个「食材列表 → 下锅顺序」的完整示例（含锅底/模式），让模型模仿格式与推理逻辑。  
- 示例可从现有规则排序结果中选取，或人工标注。  

→ 对应：在 `llm_service` 的 prompt 中增加「示例」段落，或从配置文件读取。

### 2.4 用户与会话上下文（User & Session）

- **用户偏好**：已保存的锅底、口感、模式、过敏原；在调用大模型时注入「当前用户偏好」，便于排序时考虑过敏/口味。  
- **当前会话**：本单已选食材、锅底、模式（已有）；可选扩展：上一版方案、用户是否点过「再软一点」等。  

→ 对应：在 `generate_plan` / `sort_cooking_order_by_llm` 中传入 `user_preferences` 或 `session_context`，在 prompt 中增加「用户偏好/注意事项」段落。

### 2.5 检索增强（可选，后续）

- 若引入「火锅小百科」、食材详解等长文本：可按当前食材/锅底检索相关片段，作为补充上下文注入。  
- 当前阶段可只做「静态知识注入」，不做 RAG。

### 2.6 上下文模板与版本管理

- 将 system / user 模板、领域知识片段、few-shot 示例放到统一位置（如 `context/prompts.py` + `context/knowledge.json`）。  
- 支持通过配置或环境变量切换「上下文版本」，便于对比与回滚。

---

## 三、分阶段实施计划

### Phase 1：提示词与领域知识（优先）

| 步骤 | 内容 | 产出 |
|------|------|------|
| 1.1 | 建立上下文目录结构 | `context/` 或 `prompts/`，如 `prompts/sort_system.txt`、`prompts/sort_user_template.txt` |
| 1.2 | 编写并固化「涮菜排序」的 system prompt | 角色 + 任务边界 + 输出格式（JSON only） |
| 1.3 | 编写领域知识片段 | 火锅原则、典型技巧、锅底/模式差异，存为可注入文本或结构化数据 |
| 1.4 | 在 `llm_service` 中改为从模板 + 知识组装 prompt | 保持现有 API，仅改 `_build_sort_prompt` 及 `_call_chat_completion` 的 messages |

**验收**：排序接口输入不变，输出更稳定；可关闭知识注入做 A/B 对比。

---

### Phase 2：少样本与用户上下文

| 步骤 | 内容 | 产出 |
|------|------|------|
| 2.1 | 准备 1～2 个标准 few-shot 示例（输入食材+锅底/模式 → 下锅顺序 JSON） | 示例文件或常量，可配置 |
| 2.2 | 在排序 prompt 中插入 few-shot 段落 | 模型输出格式与逻辑更一致 |
| 2.3 | 在调用链中传入「用户偏好」（锅底、模式、过敏原等） | `generate_plan` → `sort_cooking_order_by_llm(..., user_preferences=...)` |
| 2.4 | 在 user prompt 中增加「用户偏好与注意事项」 | 如过敏原、老人/儿童模式说明 |

**验收**：勾选用户偏好后，排序结果能体现「避免过敏」「更熟/更嫩」等差异。

---

### Phase 3：模板化与可配置

| 步骤 | 内容 | 产出 |
|------|------|------|
| 3.1 | 统一读取模板与知识（文件或配置） | 如 `load_prompt("sort", "system")`、`get_domain_knowledge("broth_effect")` |
| 3.2 | 支持环境变量或配置切换「上下文版本」 | 如 `HOTPOT_PROMPT_VERSION=v1`，便于线上 A/B |
| 3.3 | 为后续 LLM 能力预留扩展点 | 如「健康建议」「技巧解释」共用同一套 context 加载机制 |

**验收**：改模板或知识文件即可生效，无需改业务代码。

---

### Phase 4（可选）：评估与迭代

| 步骤 | 内容 | 产出 |
|------|------|------|
| 4.1 | 定义简单评估方式 | 如：规则排序 vs LLM 排序在「久煮先下」「内脏快涮」等规则上的符合度 |
| 4.2 | 记录少量样本的模型输入/输出 | 便于排查与迭代 prompt |
| 4.3 | 根据 Badcase 迭代领域知识与 few-shot | 更新 knowledge 与示例 |

---

## 四、建议的目录与文件

```
Hotpot/
├── context/                      # 上下文工程（新增）
│   ├── prompts/
│   │   ├── sort_system.txt       # 涮菜排序 system
│   │   ├── sort_user_template.txt  # user 模板（占位符：食材列表、锅底、模式、知识片段、示例）
│   │   └── (后续) health_tips_system.txt 等
│   ├── knowledge/
│   │   ├── general_rules.txt     # 通用原则
│   │   ├── broth_mode_effect.txt # 锅底与模式影响
│   │   └── techniques.txt       # 典型技巧
│   ├── few_shot/
│   │   └── sort_examples.json    # 排序示例
│   └── context_loader.py         # 统一加载模板与知识、组装 prompt
├── services/
│   └── llm_service.py            # 调用 context_loader，不再手写长 prompt
└── docs/
    └── CONTEXT_ENGINEERING_PLAN.md  # 本文
```

---

## 五、与现有代码的衔接

- **`services/llm_service.py`**：  
  - `_build_sort_prompt` 改为调用 `context_loader.build_sort_prompt(items, broth_type, user_mode, user_preferences=None)`。  
  - `_call_chat_completion` 的 `messages` 中，system 与 user 内容均来自 context 模块。  

- **`services/cooking_plan_service.py`**：  
  - `_resolve_cooking_order` 在调用 `sort_cooking_order_by_llm` 时传入 `user_preferences`（可由 `api.generate_cooking_plan` 传入或从用户偏好读取）。  

- **`api.py`**：  
  - 若需要「当前用户偏好」参与排序，在 `generate_cooking_plan` 中读取 `get_user_preferences()` 并传入 `llm_service`。  

---

## 六、优先级小结

| 优先级 | 内容 | 阶段 |
|--------|------|------|
| P0 | 系统/用户提示词结构化 + 领域知识注入 | Phase 1 |
| P1 | Few-shot 示例 + 用户偏好注入 | Phase 2 |
| P2 | 模板与知识可配置、版本切换 | Phase 3 |
| P3 | 评估与 Badcase 迭代 | Phase 4 |

按上述顺序推进，即可在不大改接口的前提下，把「上下文工程」系统化，并为后续更多 LLM 能力打好基础。
