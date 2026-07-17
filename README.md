# the Nan Guos - 南郭先生们

一个基于 LangGraph 的本地多智能体音乐创作实验项目。“对话南郭”是南郭乐团的对外代表，负责用户对话、记忆读取和受约束的工作流分配；“指挥南郭”负责理解创作需求和选择音乐工作流，作词、旋律、编曲等南郭负责各自领域，“提示词南郭”最终生成供 Suno 兼容服务使用的提示词。

## 当前能力

目前实现多个可组合预设工作流：

```text
pop_vocal:
参考南郭 -> 指挥南郭 -> 作词南郭 -> 旋律南郭 -> 和声南郭 -> 节奏南郭 -> 编曲南郭 -> 音色南郭 -> 审听南郭 -> 提示词南郭

classical_instrumental:
参考南郭 -> 指挥南郭 -> 旋律南郭 -> 和声南郭 -> 编曲南郭 -> 可选乐谱导出 -> 音色南郭 -> 审听南郭 -> 提示词南郭

electronic_instrumental:
参考南郭 -> 指挥南郭 -> 节奏南郭 -> 旋律南郭 -> 和声南郭 -> 编曲南郭 -> 音色南郭 -> 审听南郭 -> 提示词南郭

soundtrack_score:
参考南郭 -> 指挥南郭 -> 旋律南郭 -> 和声南郭 -> 编曲南郭 -> 音色南郭 -> 审听南郭 -> 提示词南郭

jazz_ensemble:
参考南郭 -> 指挥南郭 -> 和声南郭 -> 节奏南郭 -> 旋律南郭 -> 即兴南郭 -> 演奏南郭 -> 编曲南郭 -> 音色南郭 -> 审听南郭 -> 提示词南郭

rock_vocal:
参考南郭 -> 指挥南郭 -> 作词南郭 -> 旋律南郭 -> 和声南郭 -> 节奏南郭 -> 演奏南郭 -> 编曲南郭 -> 音色南郭 -> 审听南郭 -> 提示词南郭

folk_acoustic:
参考南郭 -> 指挥南郭 -> 作词南郭 -> 旋律南郭 -> 和声南郭 -> 演奏南郭 -> 编曲南郭 -> 音色南郭 -> 审听南郭 -> 提示词南郭

hiphop_vocal:
参考南郭 -> 指挥南郭 -> 节奏南郭 -> 作词南郭 -> 旋律南郭 -> 和声南郭 -> 演奏南郭 -> 编曲南郭 -> 音色南郭 -> 审听南郭 -> 提示词南郭
```

Agent 使用 Pydantic 模型传递结构化状态。不同音乐类型会组合不同节点：人声流行包含作词南郭，电子器乐先由节奏南郭工作，古典和影视配乐跳过作词南郭，并可根据旋律南郭的 `score_spec` 在项目 `artifacts/` 目录导出 MusicXML 与 MIDI。爵士先建立和声与 swing 律动，再由即兴南郭和演奏南郭规划独奏、comping 与乐手互动；摇滚、原声民谣和嘻哈则分别围绕乐队动态、叙事演奏和 beat/flow 使用不同节点顺序。

- FastAPI 提供本地项目、音频上传和工作流运行接口。
- 对话南郭按 session 保存独立短期上下文，并把明确偏好规范化后合并到跨 session 用户画像。当前请求和显式创作参数优先于长期偏好。
- React 工作区提供对话入口、独立作品集与记忆库页面、后台生成进度、项目恢复、精确创作表单和工作流画布。记忆库支持查看、编辑、删除和清空长期偏好。
- KIE/Suno 接入通过独立 provider 封装，默认不会产生真实请求。

## 环境

- Python 3.12+
- `uv`
- 一个兼容 OpenAI Chat Completions API 的模型服务

创建 `.env`：

```dotenv
MODEL_NAME=your-model
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1

# 使用 function_calling/json_schema 时会通过 ChatOpenAI 启用 structured output 和 tool calling
# 若兼容服务不支持工具调用，可退回 json_mode/prompt_json
LLM_STRUCTURED_OUTPUT_METHOD=function_calling

# 仅使用 --generate 时需要
KIE_API_KEY=your-kie-api-key
KIE_BASE_URL=https://api.kie.ai
KIE_MODEL=V4
KIE_CALLBACK_URL=https://your-public-host.example.com/kie/callback

# 器乐 custom mode 未从工作流传入风格时使用
KIE_STYLE=Classical

# 可选：本地日志配置
LOG_DIR=_logs
LOG_LEVEL=INFO
LOG_MAX_BYTES=5242880
LOG_BACKUP_COUNT=5
```

安装依赖并运行 CLI：

```bash
uv sync
uv run python main.py "生成一首温暖的中文民谣"
```

默认只输出最终提示词，不会调用音乐生成服务。显式传入 `--generate` 才会使用 `lib/suno.py` 中配置的 provider：

```bash
uv run python main.py "生成一首温暖的中文民谣" --generate
```

KIE/Suno provider 按 Kie 文档调用 `POST /api/v1/generate`。提交请求需要 Bearer token、`model`、`customMode`、`instrumental` 和 `callBackUrl`；本项目提交后仍会轮询 `/api/v1/generate/record-info` 下载生成结果。器乐生成会使用 custom mode，因此必须有 `style` 和 `title`，CLI 会优先使用工作流产生的标题和风格。provider 会在请求前按所选模型自动裁剪 `prompt`、`style` 和 `title`，确保不超过 Kie 的字符限制；发生裁剪时会写入日志。

一键启动本地开发环境：

```bash
./start.sh
```

脚本会在缺少 `.venv` 或 `frontend/node_modules` 时自动安装依赖，并同时启动后端和前端。API 默认位于 `http://127.0.0.1:8000`，交互文档位于 `/docs`，创作工作台位于 `http://127.0.0.1:5173`。按 `Ctrl+C` 会停止两个开发服务。
前端默认进入“对话南郭”对话。对话南郭代表南郭乐团理解用户需求、读取记忆，并且只会选择白名单动作与预设工作流；对话消息可以附带参考音频，附件会随作品进入参考南郭分析。当用户要求开始创作时，后端立即返回 run id，并在本地后台线程中执行工作流。前端轮询 Run 状态显示阶段进度。生成完成后，Suno 音频和封面会分别以歌曲名称保存到 `works/` 下，并在独立作品集页面展示封面、风格、时长、进度、播放和下载入口。创作台可以选择流派、语言、主要乐器、预设乐团并上传 demo 音频。

长期记忆保存在 `data/memory/user_profile.json`，包括规范化偏好和工作流使用次数。相同偏好会增加证据次数和置信度，同一偏好 key 的新明确值会替换旧值。创作前系统会生成 `effective_preferences`：预设乐团与创作台显式参数优先，其次是当前请求，最后才使用长期默认值。新偏好写入后前端会显示轻量提示，并可在“记忆库”页面管理。

如需手动启动，分别运行：

```bash
uv run uvicorn app.api:app --reload

cd frontend
npm run dev
```

项目元数据、上传音频和运行结果分别保存在 `data/projects/<project-id>/` 下的 `project.json`、`assets/` 和 `runs/` 中。会话短期记忆和待关联的聊天音频分别保存在 `data/sessions/<session-id>/session.json` 与 `assets/`，跨会话偏好和工作流统计保存在 `data/memory/user_profile.json`。这些数据都使用临时文件替换方式写入，不需要数据库或消息队列。

主要新增接口：

- `POST /api/sessions`、`POST /api/sessions/{id}/messages`：创建会话并由对话南郭回复、路由。
- `POST /api/sessions/{id}/assets`：上传随对话消息发送的参考音频。
- `GET /api/sessions`、`GET/PATCH/DELETE /api/sessions/{id}`：列出、恢复、重命名和删除独立会话。
- `GET /api/portfolio`：读取已完成和正在生成的本地作品。
- `GET/DELETE /api/memory`：读取或清空本地长期记忆。
- `PATCH/DELETE /api/memory/preferences/{key}`：编辑或删除单条长期偏好。
- `POST /api/projects/{id}/runs/async`：启动后台运行并立即返回 Run。
- `GET /api/projects/{id}/runs/{run_id}`：读取进度、阶段、错误和最终产物。
运行日志默认写入 `_logs/`，包括 API 工作流阶段、Agent 结构化输出、KIE/Suno 提交和轮询状态，可通过上面的 `LOG_*` 环境变量调整。

## 工具调用

`tools/` 目录提供可被 API、LangGraph 节点或 Agent wrapper 调用的确定性工具：

- `inspect_audio`：调用 `ffprobe` 读取用户上传音频的时长、编码、采样率、声道、码率和文件大小。
- `trim_audio_preview`：调用 `ffmpeg` 从上传音频生成短预览片段并做基础响度规范化。
- `render_prompt_demo_audio`：根据提示词生成一个轻量 demo 音频，适合作为中间参考产物。
- `render_waveform` / `summarize_generated_audio`：对 Suno/KIE 生成的音频做元数据分析和波形图可视化。

这些工具都使用参数列表调用命令行程序，不拼接 shell 字符串；命令失败、缺少工具或超时会抛出清晰错误。使用前需在本机安装对应命令行工具，例如 `ffmpeg` 和 `ffprobe`。

`skills/` 目录提供按职能划分的 Agent 技能说明。Agent 初始化时会把对应 `SKILL.md` 加载进系统提示词，例如作词南郭加载参考音频作词技能，旋律南郭加载 demo 音频规划技能，编曲南郭加载音频分析编曲技能，提示词南郭加载 Suno 生成交接技能。

当 `LLM_STRUCTURED_OUTPUT_METHOD=function_calling` 或 `json_schema` 时，LLM 初始化会回到 `ChatOpenAI`，上传参考音频会先进入参考南郭。该节点使用 `llm.bind_tools(...)` 让模型调用白名单工具，例如 `inspect_uploaded_audio`、`create_uploaded_audio_preview` 和 `render_uploaded_audio_waveform`；工具参数只允许使用上传资产索引，不允许模型传任意本地路径。
提示词南郭产出最终提示词后，API 会受控调用 `render_prompt_demo_audio` 生成中间 demo 音频。KIE/Suno 音乐下载完成后，API 会受控调用 `summarize_generated_audio` 和 `render_waveform` 生成音频元数据与波形图；这些后处理工具失败时会写入错误字段和日志，不阻断主音乐生成结果。

## 测试

```bash
uv run pytest
```

前端验证：

```bash
cd frontend
npm run lint
npm run build
npm run test:e2e
```

## 目录

- `agents/`：Agent 节点。
- `app/`：LangGraph 工作流。
- `models/`：结构化状态和输出模型。
- `prompts/`：各角色的系统提示词。
- `skills/`：各角色加载的技能说明。
- `lib/`：提示词加载、音乐服务等工具。
- `tools/`：音频分析、预览生成、波形渲染和 demo 音频渲染工具。
- `providers/`：音乐生成供应商适配。
- `frontend/`：本地 React 创作工作台。
- `docs/`：架构与设计说明。
- `data/`：本地项目、上传资产和运行数据，不提交版本库。

开发约束见 [AGENTS.md](AGENTS.md)，当前架构见 [docs/architecture.md](docs/architecture.md)。
