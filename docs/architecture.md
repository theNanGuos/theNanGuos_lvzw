# 架构概览

theNanGuos 是一个完全本地运行的多 Agent 音乐创作实验台。系统分为四个简单层次：

```text
React workspace
      |
FastAPI + local project store
      |
LangGraph music workflows
      |
score tools / music generation providers
```

## 工作流

当前提供多个受约束的预设，不同音乐类型复用节点但走不同路径：

- `pop_vocal`：Audio Reference、Conductor、Lyrics、Melody、Harmony、Rhythm、Arrange、Sound Design、Mix Review、Prompt Compiler。
- `classical_instrumental`：Audio Reference、Conductor、Melody、Harmony、Arrange、可选 Score Export、Sound Design、Mix Review、Prompt Compiler。
- `electronic_instrumental`：Audio Reference、Conductor、Rhythm、Melody、Harmony、Arrange、Sound Design、Mix Review、Prompt Compiler。
- `soundtrack_score`：Audio Reference、Conductor、Melody、Harmony、Arrange、Sound Design、Mix Review、Prompt Compiler。

Conductor 只能选择已注册的预设。所有 LLM 节点使用 Pydantic 结构化输出，关键领域数据不从自由文本消息中解析。

## 本地数据

每个项目使用独立目录：

```text
data/projects/<project-id>/
  project.json
  assets/
  artifacts/
    score.musicxml
    score.mid
  runs/
    <run-id>.json
```

`LocalProjectStore` 是唯一负责该目录结构的模块。当前不使用数据库。

## 长短期记忆

短期记忆按会话保存在 `data/sessions/<session-id>/session.json`，每个 session 维护独立消息上下文和摘要。长期记忆保存在 `data/memory/user_profile.json`，由 `LocalMemoryStore` 使用 Pydantic 校验和临时文件替换方式读写，不依赖数据库。

长期记忆分为三类：

- 语义记忆：人声、流派、语言、乐器、时长和制作风格等规范化偏好。
- 行为记忆：各预设工作流的实际完成次数。
- 情景记忆：本地项目和作品是事实来源，记忆上下文只引用最近作品，不复制音频数据。

Chat Agent 只提取用户明确表达的候选记忆。`LocalMemoryStore` 负责 key 规范化、重复证据增强和冲突值替换。执行工作流前会确定性解析 `effective_preferences`，优先级为显式项目参数和预设、当前请求、长期偏好、系统默认值。Conductor 和 Prompt Compiler 只使用解析后的有效偏好补充未指定内容。

## 外部能力

音乐生成通过 `MusicGenerationProvider` 协议隔离。当前实现是 `KieSunoProvider`，CLI 只有显式传入 `--generate` 才会产生真实请求。

MusicXML 和 MIDI 由 `music21` 从受约束的 `ScoreSpec` 生成。demo 音频渲染需要本机安装 MuseScore 或 FluidSynth，目前尚未接入；缺少这些程序不影响提示词和乐谱生成。

## 前端边界

创作台支持输入音乐构想，选择流派、语言、主要乐器和预设乐团，上传参考音频，运行工作流并查看结果。React Flow 只负责展示受约束的预设执行路径，不允许前端任意图映射为后端代码。对话页负责自然语言创作和运行过程展示，作品集负责作品管理，记忆库负责长期偏好与创作经历管理。
