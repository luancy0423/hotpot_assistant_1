# 涮涮AI - 推送部署到 ModelScope 指南

本文说明如何把本项目从本机推送到 ModelScope Studio，并完成在线部署。

---

## 一、前置准备

1. **注册 ModelScope 账号**  
   打开 [https://www.modelscope.cn](https://www.modelscope.cn)，注册/登录。

2. **安装 Git 与 Git LFS**  
   - 安装 [Git](https://git-scm.com/)  
   - 安装 [Git LFS](https://git-lfs.com/)（大文件支持，Studio 可能用到）  
   - 终端执行：`git lfs install`（只需一次）

---

## 二、在 ModelScope 创建 Studio 应用

1. 登录后进入 **ModelScope 首页**，找到 **「创空间 / Studio」** 入口（或直接访问 [https://www.modelscope.cn/studios](https://www.modelscope.cn/studios)）。
2. 点击 **「创建创空间」** 或 **「新建 Studio」**。
3. 填写：
   - **名称**：如 `Hotpot_Assistant` 或 `涮涮AI`
   - **描述**：简短介绍
   - **框架/类型**：选择 **Gradio**（若选项里有）
4. 创建完成后，进入该 Studio 的 **「开发」** 或 **「代码」** 页面，会看到：
   - **克隆地址**：形如  
     `https://www.modelscope.cn/studios/<你的用户名>/<空间名>.git`  
   - 或带鉴权的：  
     `http://oauth2:<token>@www.modelscope.cn/studios/<用户名>/<空间名>.git`
5. 若页面有 **「使用我的 Token」**，先点开并生成/复制 Token，再复制带 `oauth2` 的克隆地址，便于后续 push 时鉴权。

---

## 三、本机准备：把代码推送到 Studio 仓库

有两种常见方式：**A）本机已有 Git 仓库**；**B）本机是纯文件夹、尚未用 Git 管理**。

### 方式 A：项目已经是 Git 仓库

1. 在项目根目录（有 `app.py` 的目录）打开终端。
2. 添加 ModelScope 为远程仓库（替换为你在 Studio 页看到的地址）：

   ```bash
   git remote add modelscope https://www.modelscope.cn/studios/<你的用户名>/<空间名>.git
   ```

   若使用 Token 克隆地址，则：

   ```bash
   git remote add modelscope http://oauth2:<你的Token>@www.modelscope.cn/studios/<用户名>/<空间名>.git
   ```

3. 确保要部署的文件都已提交：

   ```bash
   git add app.py api.py frontend/ demo.py run_tests.py requirements.txt
   git add data/ services/ context/
   git status
   git commit -m "feat: 涮涮AI Gradio 应用与 ModelScope 部署"
   ```

4. 推送到 ModelScope（首次可能需指定分支，一般为 `master` 或 `main`）：

   ```bash
   git push modelscope master
   ```

   若默认分支是 `main`：

   ```bash
   git push modelscope main
   ```

---

### 方式 B：本机还没有 Git，从「克隆空仓库」开始

1. 在 Studio 创建好后，在开发/代码页复制 **带 Token 的克隆地址**（例如 `http://oauth2:xxx@www.modelscope.cn/studios/LiuYicheng/Hotpot_Assistant.git`）。
2. 在本机选一个目录，克隆（会得到一个空或带初始文件的仓库）：

   ```bash
   git lfs install
   git clone http://oauth2:<Token>@www.modelscope.cn/studios/<用户名>/<空间名>.git
   cd <空间名>
   ```

3. 把当前项目里的所有需要的文件**复制**到刚克隆出来的目录里（保持目录结构）：

   - 必须包含：`app.py`、`frontend/`、`api.py`、`requirements.txt`
   - 以及目录：`data/`、`services/`、`context/`
   - 可选：`demo.py`、`run_tests.py`、`README.md`、`docs/` 等

4. 在克隆出来的目录里提交并推送：

   ```bash
   git add .
   git commit -m "Add 涮涮AI application"
   git push origin master
   ```

   （若默认分支是 `main`，把 `master` 改成 `main`。）

---

## 四、必须包含的文件与目录

| 路径 | 说明 |
|------|------|
| `app.py` | **必须**。ModelScope 约定的入口，内部会调用 `create_ui()` 并 `demo.launch()`。 |
| `frontend/` | **必须**。Gradio 界面与逻辑（ui.py、handlers、components 等）。 |
| `api.py` | **必须**。主 API，被 frontend 调用。 |
| `requirements.txt` | **必须**。至少包含 `gradio>=4.0.0`，供平台安装依赖。 |
| `data/` | **必须**。含 `ingredients_db.py`、`menu_api.py`、`user_preferences.py` 等。 |
| `services/` | **必须**。含 `cooking_plan_service.py`、`recognition_service.py`、`llm_service.py`。 |
| `context/` | **必须**。上下文工程（prompts、knowledge、few_shot、context_loader.py）。 |

不需要部署的可以不加（例如本地测试用的 `火锅食材涮煮时间表.md`、部分 `docs` 等，按需取舍）。

---

## 五、推送后在 ModelScope 上的操作

1. 回到 **Studio 页面**，在「开发」里确认代码已更新（或等待自动构建）。
2. 若平台有 **「运行 / 启动」** 按钮，点击后等待构建与启动。
3. 打开提供的 **应用链接**（如 `https://www.modelscope.cn/studios/<用户名>/<空间名>/view`），即可在浏览器中使用涮涮AI 界面。

若启动失败，查看 Studio 的 **「日志」** 或 **「构建日志」**，常见原因：

- 缺少 `app.py` 或 `requirements.txt`
- 缺少 `data/`、`services/`、`context/` 中某目录导致 import 报错
- 依赖未写进 `requirements.txt`（本项目仅需 `gradio`，一般无问题）

---

## 六、简要命令速查（本机已有 Git 且已提交过）

```bash
# 1. 添加远程（仅第一次）
git remote add modelscope http://oauth2:<Token>@www.modelscope.cn/studios/<用户名>/<空间名>.git

# 2. 确保文件已提交
git add app.py api.py frontend/ requirements.txt data/ services/ context/
git commit -m "Deploy to ModelScope"

# 3. 推送（分支名以 Studio 页面显示为准）
git push modelscope master
```

更多细节以 ModelScope 当前页面的「创建创空间 / 开发 / 克隆与推送」说明为准，可参阅 [ModelScope 文档中心](https://www.modelscope.cn)。
