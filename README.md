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

## 环境

- Python 3.12+
- `uv`
- 一个兼容 OpenAI Chat Completions API 的模型服务

创建 `.env`：

```dotenv
MODEL_NAME=your-model
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1

# 仅使用 --generate 时需要
KIE_API_KEY=your-kie-api-key
KIE_BASE_URL=https://api.kie.ai
KIE_MODEL=V4
```

安装依赖并运行：

```bash
uv sync
uv run python main.py "生成一首温暖的中文民谣"
```

默认只输出最终提示词，不会调用音乐生成服务。显式传入 `--generate` 才会使用 `lib/suno.py` 中配置的 provider：

```bash
uv run python main.py "生成一首温暖的中文民谣" --generate
```

启动本地 API：

```bash
uv run uvicorn app.api:app --reload
```

API 默认位于 `http://127.0.0.1:8000`，交互文档位于 `/docs`。项目元数据、上传音频和运行结果分别保存在 `data/projects/<project-id>/` 下的 `project.json`、`assets/` 和 `runs/` 中。

另开一个终端启动前端：

```bash
cd frontend
npm install
npm run dev
```

创作工作台位于 `http://127.0.0.1:5173`。

## 测试

```bash
uv run pytest
```

## 目录

- `agents/`：Agent 节点。
- `app/`：LangGraph 工作流。
- `models/`：结构化状态和输出模型。
- `prompts/`：各角色的系统提示词。
- `lib/`：提示词加载、音乐服务等工具。
- `data/`：后续用于本地项目和运行数据，不提交版本库。

开发约束和后续顺序见 [AGENTS.md](AGENTS.md)。
