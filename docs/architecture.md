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

当前提供两个受约束的预设：

- `pop_vocal`：Conductor、Lyrics、Melody、Arrange、Prompt Compiler。
- `classical_instrumental`：Conductor、Melody、Arrange、可选 Score Export、Prompt Compiler。

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

## 外部能力

音乐生成通过 `MusicGenerationProvider` 协议隔离。当前实现是 `KieSunoProvider`，CLI 只有显式传入 `--generate` 才会产生真实请求。

MusicXML 和 MIDI 由 `music21` 从受约束的 `ScoreSpec` 生成。demo 音频渲染需要本机安装 MuseScore 或 FluidSynth，目前尚未接入；缺少这些程序不影响提示词和乐谱生成。

## 前端边界

创作台支持输入音乐构想、选择预设、上传参考音频、运行工作流和查看提示词。React Flow 目前用于查看和拖动预设节点，尚未把用户编辑后的任意图提交给后端执行。

下一阶段应先定义可校验的工作流 JSON schema 和节点注册表，再开放自定义连线，避免前端图直接映射为任意后端代码。
