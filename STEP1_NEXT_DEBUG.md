# Step1「下一步」卡住 — 排查位置说明

**步骤对应关系（以界面为准）**：

- **Step1 = 输入食材**（第一步）：添加/搜索食材，点「下一步」→ 进入 Step2（选择口味）。
- **Step2 = 选择口味**：锅底、口感、人数等，点「生成方案」→ 进入 Step3（方案结果页）。

若在 **Step1（输入食材）** 点「下一步」后卡住，问题在：**从「输入食材」到「选择口味」的导航或底部栏的下一步按钮绑定**。

---

## 1. 按钮定义与 step1（输入食材）布局

在 `app_gradio.py` 里先确认**代码里哪一列是「输入食材」**：

- 搜索 **`step0`**、**`step1`**：通常 `step0` = 输入食材，`step1` = 选择口味（若你界面把「输入食材」叫第一步，则对应代码里的 step0）。
- 输入食材页的「下一步」一般有两种实现方式：
  1. **底部购物车栏**里的「下一步 ›」按钮（通过 JS 触发隐藏的 Gradio 按钮，如 `btn_next`、`shuaiGrNext`）。
  2. 或该页内的一个 **gr.Button("下一步")** 直接绑定 `_nav_next_v4` 或类似导航函数。

**排查点**：确认你点的是哪一个「下一步」—— 底部栏的，还是页面内的；然后找对应的 `.click(...)` 绑定。

---

## 2. Step1（输入食材）的「下一步」点击绑定

在 **输入食材页** 点「下一步」应只做**页面切换**（step0 → step1，即到选择口味），不调用生成方案。

在 `app_gradio.py` 里搜索：

- **`btn_next`**：底部栏的「下一步 ›」往往通过 JS（如 `shuaiGrNext`）触发这个隐藏按钮。
- **`btn_next.click`** 或 **`.click(..., btn_next, ...)`**：看它绑定的 `fn` 和 `outputs`。
- **`_nav_next_v4`**：常见的「下一步」导航函数，根据当前 `step_state` 加 1 并更新各 step 的 visible。

典型形式（仅导航、无生成方案）：

```text
btn_next.click(
    fn=_nav_next_v4,
    inputs=[step_state],
    outputs=[step_state, step_home, step0, step1, step2, step3]
)
```

**排查点**：  
- `outputs` 必须是 6 个（step_state + 5 个 step 的 visible），且 `fn` 的 return 元组长度、顺序与之一致。  
- 若 `btn_next` 被绑定成「生成方案」的逻辑（inputs 很多、调 API），那就错了——生成方案应只在**选择口味页**的「生成方案」按钮上。

---

## 3. 生成方案函数（仅在 Step2「选择口味」页用到）

若卡住的是 **Step2 的「生成方案」** 而不是 Step1 的「下一步」，再查这里。

在 `app_gradio.py` 里搜索：

- **`api.generate_cooking_plan`**  
  - 调用处应在 **`btn_generate.click`** 绑定的 `fn` 里（选择口味页的「生成方案」按钮）。

该函数内部通常会：从 inputs 取食材与偏好 → 调 `api.generate_cooking_plan(...)`（可能较慢）→ return 更新 step_state 与各 step 的 visible。

**若卡住的是 Step1（输入食材）的「下一步」**：与本节无关，重点看 **2. 点击事件绑定** 和 **4. 返回值与 outputs**。

---

## 4. 返回值与 outputs 一一对应（最容易导致「卡住」）

**Step1（输入食材）的「下一步」** 绑定的若是 `_nav_next_v4`，则：

- `outputs=[step_state, step_home, step0, step1, step2, step3]` → 共 6 个。
- 对应 `fn` 必须 return 长度为 6 的元组，且顺序一致（step_state, step_home, step0, step1, step2, step3 的 visible 更新）。

若 **Step2 的「生成方案」** 卡住，则在该按钮的 `outputs` 上数个数，与对应 `fn` 的 return 元组长度、顺序一致（通常还会多 plan_md、plan_data 等）。

**排查点**：return 少一个、多一个或顺序错，Gradio 都可能表现为卡住或界面不更新。

---

## 5. 步骤与「开始吃饭」的衔接（可选）

- 输入食材(step0) → 下一步 → 选择口味(step1) → 生成方案 → 方案结果(step2) → 开始吃饭 → 计时(step3)。  
- 确认 **step_state** 与各 step 的 visible 在每步切换时一致。

---

## 6. 建议的排查顺序（Step1 = 输入食材的下一步卡住）

1. 在 **`btn_next.click`** 绑定的 **fn**（如 `_nav_next_v4`）里**第一行**加 `print("step1 下一步 clicked")`，点输入食材页的「下一步」，看终端是否立刻打印。  
   - 不打印 → 点击没触发到该 fn（例如 JS 没找到 `btn_next`、或绑错了按钮）。  
   - 打印了 → 继续下一步。

2. **数 return 和 outputs**：`btn_next.click(..., outputs=[...])` 的 outputs 应有 6 个（step_state + 5 个 step），fn 的 return 元组长度、顺序与之完全一致。

3. 若怀疑是 **底部栏「下一步 ›」** 的 JS 没触发：检查 `shuaiGrNext`、`btn-next-hidden`、`#btn-next-hidden` 的 DOM 是否存在（`visible=True`），以及 CSS 是否把按钮移出视口但仍可被 JS 点击。

---

## 7. 快速搜索关键词汇总（在 app_gradio.py 中）

| 目的                   | 搜索词 |
|------------------------|--------|
| Step1 输入食材页的下一步 | `btn_next`、`btn-next-hidden`、`shuaiGrNext`、`_nav_next_v4` |
| 点击绑定               | `btn_next.click`、`.click(` 且 outputs 含 step_state, step0, step1... |
| 步骤与可见性           | `step_state`、`step0`、`step1`、`step2`、`step3`、`gr.update(visible` |
| 选择口味页生成方案     | `btn_generate`、`生成方案`、`api.generate_cooking_plan` |

Step1（输入食材）的下一步卡住时，重点查 **btn_next** 的绑定和 **return 与 outputs 的 6 个一致**。
