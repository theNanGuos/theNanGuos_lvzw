# theNanGuos：南郭先生们

![theNanGuos](icon.png)

theNanGuos 是一个基于 LangGraph 的本地多智能体音乐创作实验项目。系统把作词、旋律、和声、节奏、编曲、音色和审听等职责交给不同的“南郭”，再由对话南郭理解需求、指挥南郭选择受约束的工作流，最终生成音乐提示词、可选乐谱、演示音频和完整音乐。

项目提供 FastAPI 后端与 React 前端，支持自然语言创作、参考音频上传、工作流进度展示、长期偏好记忆以及本地作品播放和下载。项目数据和生成产物均保存在本地文件系统。

## 快速启动

### 1. 准备运行环境

根目录的 `start.sh` 目前仅支持 Linux。脚本会自动检查并准备以下依赖：

- Python 3.12 与 uv
- Node.js 24 LTS 与 npm
- FFmpeg 与 ffprobe
- Python 和前端项目依赖

缺少系统工具时，脚本可能需要 root 或 `sudo` 权限，并需要能够访问系统软件源、Python 软件源和 npm。

### 2. 配置服务

在项目根目录复制环境变量模板：

```bash
cp .env.example .env
```

编辑 `.env`，至少填写兼容 OpenAI Chat Completions API 的模型服务：

```dotenv
MODEL_NAME=your-model
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
LLM_STRUCTURED_OUTPUT_METHOD=function_calling
```

如果模型服务不支持函数调用或结构化输出，可改为：

```dotenv
LLM_STRUCTURED_OUTPUT_METHOD=prompt_json
```

如需生成完整音乐，还需要配置 KIE/Suno 兼容服务：

```dotenv
KIE_API_KEY=your-kie-api-key
KIE_BASE_URL=https://api.kie.ai
KIE_MODEL=V4
KIE_CALLBACK_URL=https://your-public-host.example.com/kie/callback
KIE_STYLE=Pop
```

未配置 KIE/Suno 时仍可启动项目，并通过下文不带 `--generate` 的命令行方式生成音乐提示词；网页端生成完整音乐需要上述配置。

### 3. 启动项目

在项目根目录运行：

```bash
./start.sh
```

首次启动会安装和同步依赖，之后会同时运行：

- 前端工作区：<http://127.0.0.1:5173>
- 后端 API：<http://127.0.0.1:8000>
- API 文档：<http://127.0.0.1:8000/docs>

开发前端通过同源路径访问 API，再由 Vite 代理到后端。这一方式支持 IDE
端口转发和远程开发环境，避免浏览器把 `127.0.0.1:8000` 解析到访问者自己的计算机。
如需覆盖代理目标，可设置 `VITE_API_PROXY_TARGET`。

按 `Ctrl+C` 会同时停止前后端服务。

只准备依赖、不启动服务：

```bash
BOOTSTRAP_ONLY=1 ./start.sh
```

## 使用方法

启动后打开 <http://127.0.0.1:5173>，可以通过四个主要页面使用系统：

1. **对话**：直接描述想创作的音乐，例如“生成一首温暖的中文民谣”。也可以上传参考音频，由系统创建项目并选择合适的乐团工作流。
2. **创作台**：填写作品名称、预设乐团、流派、语言、主要乐器和创作构想，上传参考音频后开始生成，并查看智能体节点与执行进度。
3. **作品集**：查看正在生成或已经完成的作品，播放生成音频、查看波形并下载文件。
4. **记忆库**：查看和管理系统记录的语言、流派、乐器及人声偏好。当前请求和创作台中的明确设置始终优先于长期偏好。

系统支持流行人声、古典器乐、电子器乐、影视配乐、爵士乐团、摇滚人声、原声民谣和嘻哈人声等预设。选择“自动判断”时，指挥南郭会根据当前需求决定工作流；器乐工作流会自动跳过作词环节。

## 命令行使用

只运行智能体工作流并输出最终音乐提示词：

```bash
uv run python main.py "生成一首温暖的中文民谣"
```

同时调用已配置的 KIE/Suno 服务生成音乐：

```bash
uv run python main.py "生成一首温暖的中文民谣" --generate
```

## 手动启动

如果依赖已经准备完成，也可以分别启动后端和前端：

```bash
uv run uvicorn app.api:app --reload
```

在另一个终端中运行：

```bash
cd frontend
npm run dev
```

## 本地数据

- `data/`：项目、会话、偏好和上传资产
- `works/`：生成的音乐、封面、演示音频和波形
- `_logs/`：本地运行日志
