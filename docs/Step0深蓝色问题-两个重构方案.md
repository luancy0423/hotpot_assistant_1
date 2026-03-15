# Step0（第一步·输入食材）深蓝色问题 — 两个重构方案

## 问题简述

Step0 使用「方案 B」：`#ing-card-wrap`（Column）包 `#ing-card-group`（Group），CSS 对壳设米色、直接子层透明。但 Gradio 在 Column/Group 内部还会插入多层 `.block`、`.gr-form` 等，这些层使用主题的 **secondary 色**（蓝），且注入顺序或优先级常盖过我们的样式，导致**深蓝色一直改不干净**。

---

## 方案一：Step0 区块化（类似 Step1 方案 C）

**思路**：不依赖「一个大壳」透出米色，而是把食材区拆成多块，每块都是「自定义 HTML 标题 + gr.Group」，由我们自己的容器包住，从结构上减少被主题染色的层级。

**做法**：

1. **components.py**  
   新增 Step0 用的小标题函数，例如：
   - `step0_section_header_html(title: str, icon: str) -> str`  
   返回类似 `<div class="step0-section-header">…</div>`，仅做标题，不包背景。

2. **ui.py（Step0 布局）**  
   把当前「一个 Column(ing-card-wrap) + 一个 Group(ing-card-group)」拆成多个「Column + HTML 标题 + Group」：
   - 块 1：标题「🖊 食材名称 / 搜索」+ Group（名称输入、搜索下拉、默认提示）
   - 块 2：标题「⏱ 涮煮时间与份数」+ Group（时间 Slider、份数 Slider）
   - 块 3：标题「✔ 操作」+ Group（加入清单、清空）
   - 块 4：标题「🎤 语音 / 📷 识图」+ Group（语音、识图两列）  
   每个块用 `gr.Column(elem_classes=["step0-card"])` 包住，Group 用 `elem_classes=["step0-card-body"]`。

3. **style.css**  
   - `.step0-card`：米色底、圆角、外边距（与当前 ing-card-wrap 视觉一致）。
   - `.step0-card-body`、`.step0-card .block`、`.step0-card .gr-form`：`background: transparent !important`，让块内只透出 `.step0-card` 的米色。
   - 输入框/按钮等仍用现有白底、边框规则（可沿用 `#ing-card-group` 的规则或改为 `.step0-card-body input` 等）。

**优点**：  
- 从 DOM 上减少「大块被主题直接着色」的容器，每块都是我们命名的 class，易控。  
- 与 Step1 方案 C 思路一致，后续维护统一。

**缺点**：  
- ui.py 改动较多，要重新排布 Row/Column。  
- 若 Gradio 在 Group 内部仍插入带 secondary 的节点，可能还需对 `.step0-card-body` 内层再补几条透明。

---

## 方案二：Step0 根壳 + 强制覆盖层（最小改结构）

**思路**：**不大改现有 Step0 的组件结构**，只增加一个「我们完全可控的根壳」和一段**只针对 Step0、优先级最高的 CSS**，让米色和透明规则一定盖过主题。

**做法**：

1. **ui.py（仅包一层壳）**  
   - 在 `with step0:` 里，在 `gr.HTML(step_header_html(...))` 之后、现有 `with gr.Column(elem_id="ing-card-wrap", ...)` 之前：
     - 插入 `gr.HTML('<div class="step0-beige-root">')`。
   - 在 Step0 内容末尾（例如在「底部悬浮栏」或抽屉之前），插入 `gr.HTML('</div>')`，与上面成对，把整页 Step0 内容包在 `<div class="step0-beige-root">` 内。  
   - 注意：Gradio 可能把相邻 HTML 与 Column 拆开，若发现 `</div>` 未正确闭合，可改为在「ing-card-wrap 的 Column」外包一层 Column，并给该外层 Column `elem_classes=["step0-beige-root"]`（用 Gradio 的 Column 当根壳），避免依赖 HTML 闭合。

2. **style.css（Step0 专用高优先级块）**  
   - 在 `_CSS` **末尾**单独加一段注释：`/* ===== Step0 强制覆盖（最后加载） ===== */`，然后写：
     - `.step0-beige-root` 或 `#page-step0 .step0-beige-root`：`background: var(--shuai-cell-bg, #EDEBDE) !important;`，并设 `min-height`、`border-radius`、`padding` 等，使整块 Step0 视觉为一整块米色底。
     - `.step0-beige-root *`：不直接设背景（避免把输入框也盖掉）。
     - `.step0-beige-root > div`、`.step0-beige-root .block`、`.step0-beige-root .gr-group`、`.step0-beige-root .gr-form`：`background: transparent !important;`，让中间层全部透明，只透出根壳米色。
     - 保留并沿用现有 `#ing-card-wrap`、`#ing-card-group` 的米色/透明规则；若根壳已提供整页米色，可把 `#ing-card-wrap` 改为透明或与根壳一致，避免双重背景。

3. **可选**：在 `launch_demo()` 里把 Step0 这段 CSS 拼在 `_CSS` 的**最后**再传给 `demo.launch(css=...)`，确保在 theme 和其余样式之后加载，提高覆盖概率。

**优点**：  
- 几乎不动现有 Step0 的 Row/Column/Group 结构，只加一层根壳和一段 CSS。  
- 风险集中在「选择器能否盖过主题」和「根壳是否正确包住整页」，便于排查。

**缺点**：  
- 依赖选择器优先级与加载顺序，Gradio 升级或 theme 变更后可能需再微调。  
- 若 Gradio 把 Step0 内容渲染在 iframe 或 shadow root 内，根壳选择器可能失效，需再改用 iframe 内样式或全局提高优先级（如 `body .step0-beige-root`）。

---

## 对比小结

| 维度         | 方案一（区块化）           | 方案二（根壳 + 强制覆盖）     |
|--------------|----------------------------|--------------------------------|
| 改动范围     | ui 布局 + components + CSS | 主要 CSS + ui 加一层壳/HTML   |
| 对主题的依赖 | 低，结构上减少被染色的层   | 依赖优先级盖过 theme          |
| 可维护性     | 结构清晰，与 Step1 一致    | 逻辑简单，但需注意加载顺序    |
| 实施难度     | 中等偏上                   | 较小                          |

若你更在意**长期稳定、少被主题牵制**，优先考虑**方案一**；若希望**先快速试一版、少动布局**，可先做**方案二**，再视效果决定是否上方案一。
