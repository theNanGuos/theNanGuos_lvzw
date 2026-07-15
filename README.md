# the Nan Guos - 南郭先生们

一个基于 LangGraph 的本地多智能体音乐创作实验项目。Conductor Agent 负责理解需求和选择工作流，作词、作曲、编曲等 Agent 负责各自领域，Prompt Compiler 最终生成供 Suno 兼容服务使用的提示词。

## 当前能力

目前实现两个预设工作流：

```text
pop_vocal:
Conductor -> Lyrics -> Melody -> Arrange -> Prompt Compiler

classical_instrumental:
Conductor -> Melody -> Arrange -> optional Score Export -> Prompt Compiler
```

Agent 使用 Pydantic 模型传递结构化状态。古典器乐工作流会跳过歌词节点，并可根据 Melody Agent 的 `score_spec` 在项目 `artifacts/` 目录导出 MusicXML 与 MIDI。

- FastAPI 提供本地项目、音频上传和工作流运行接口。
- React 创作台提供预设选择、参考音频上传、工作流画布和结果展示。
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

# OpenAI 兼容服务优先使用 json_mode；本项目会用普通聊天请求返回 JSON，再在本地校验
# 若服务明确支持工具调用或 OpenAI structured outputs，可改为 function_calling/json_schema
LLM_STRUCTURED_OUTPUT_METHOD=json_mode

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

KIE/Suno provider 按 Kie 文档调用 `POST /api/v1/generate`。提交请求需要 Bearer token、`model`、`customMode`、`instrumental` 和 `callBackUrl`；本项目提交后仍会轮询 `/api/v1/generate/record-info` 下载生成结果。器乐生成会使用 custom mode，因此必须有 `style` 和 `title`，CLI 会优先使用工作流产生的标题和风格。

一键启动本地开发环境：

```bash
./start.sh
```

脚本会在缺少 `.venv` 或 `frontend/node_modules` 时自动安装依赖，并同时启动后端和前端。API 默认位于 `http://127.0.0.1:8000`，交互文档位于 `/docs`，创作工作台位于 `http://127.0.0.1:5173`。按 `Ctrl+C` 会停止两个开发服务。
在前端点击“召集乐团开始创作”会先运行 Agent 工作流生成最终提示词，然后调用 KIE/Suno 生成音乐并轮询任务详情；生成完成后的 mp3 会保存到 `works/` 根目录，前端会显示播放器和下载入口。

如需手动启动，分别运行：

```bash
uv run uvicorn app.api:app --reload

cd frontend
npm run dev
```

项目元数据、上传音频和运行结果分别保存在 `data/projects/<project-id>/` 下的 `project.json`、`assets/` 和 `runs/` 中。
运行日志默认写入 `_logs/`，包括 API 工作流阶段、Agent 结构化输出、KIE/Suno 提交和轮询状态，可通过上面的 `LOG_*` 环境变量调整。

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
- `lib/`：提示词加载、音乐服务等工具。
- `providers/`：音乐生成供应商适配。
- `frontend/`：本地 React 创作工作台。
- `docs/`：架构与设计说明。
- `data/`：本地项目、上传资产和运行数据，不提交版本库。

开发约束见 [AGENTS.md](AGENTS.md)，当前架构见 [docs/architecture.md](docs/architecture.md)。
