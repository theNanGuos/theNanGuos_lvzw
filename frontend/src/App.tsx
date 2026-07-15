import { useMemo, useState } from 'react'
import {
  AudioLines,
  CheckCircle2,
  ChevronRight,
  CircleStop,
  Clock3,
  Download,
  FileAudio,
  FolderOpen,
  GitBranch,
  Headphones,
  LoaderCircle,
  Play,
  Plus,
  SlidersHorizontal,
  Sparkles,
  Upload,
  Waves,
  X,
} from 'lucide-react'
import { createProject, mediaUrl, runProject, uploadAsset } from './api'
import type { DemoAudio, GeneratedAudioAnalysis, GeneratedTrack, Preset, RunResult } from './api'
import { WorkflowCanvas } from './components/WorkflowCanvas'
import './App.css'

type View = 'compose' | 'workflow'
type RunStatus = 'idle' | 'creating' | 'uploading' | 'running' | 'completed' | 'failed'

const statusCopy: Record<RunStatus, string> = {
  idle: '准备就绪',
  creating: '创建项目',
  uploading: '上传参考音频',
  running: '创作与生成中',
  completed: '音乐生成完成',
  failed: '执行失败',
}

const presetOptions: Array<{ value: Preset; label: string; description: string }> = [
  { value: 'auto', label: '自动选择', description: '由指挥 Agent 判断最合适的乐团路径' },
  { value: 'pop_vocal', label: '流行人声', description: '歌词、旋律、节奏和制作完整协作' },
  { value: 'classical_instrumental', label: '古典器乐', description: '主题、和声、配器与可选乐谱导出' },
  { value: 'electronic_instrumental', label: '电子器乐', description: '节奏先行，突出低频和音色设计' },
  { value: 'soundtrack_score', label: '影视配乐', description: '情绪叙事、空间声景和主题发展' },
]

const statusSteps: Array<{ value: RunStatus; label: string }> = [
  { value: 'creating', label: '建档' },
  { value: 'uploading', label: '参考' },
  { value: 'running', label: '生成' },
  { value: 'completed', label: '完成' },
]

function stepState(current: RunStatus, step: RunStatus) {
  const currentIndex = statusSteps.findIndex((item) => item.value === current)
  const stepIndex = statusSteps.findIndex((item) => item.value === step)
  if (current === 'failed') return 'muted'
  if (current === 'idle') return 'pending'
  if (stepIndex < currentIndex || current === 'completed') return 'done'
  if (step === current) return 'current'
  return 'pending'
}

function App() {
  const [view, setView] = useState<View>('compose')
  const [title, setTitle] = useState('未命名作品')
  const [request, setRequest] = useState('')
  const [preset, setPreset] = useState<Preset>('auto')
  const [audio, setAudio] = useState<File | null>(null)
  const [status, setStatus] = useState<RunStatus>('idle')
  const [result, setResult] = useState<RunResult | null>(null)
  const [error, setError] = useState('')

  const busy = ['creating', 'uploading', 'running'].includes(status)
  const finalPrompt = useMemo(
    () => (result?.state.final_prompt as string | undefined) ?? '',
    [result],
  )
  const generatedTracks = useMemo(
    () => (result?.state.generated_tracks as GeneratedTrack[] | undefined) ?? [],
    [result],
  )
  const demoAudio = useMemo(
    () => result?.state.demo_audio as DemoAudio | undefined,
    [result],
  )
  const audioAnalyses = useMemo(
    () => (result?.state.generated_audio_analysis as GeneratedAudioAnalysis[] | undefined) ?? [],
    [result],
  )
  const selectedPreset = presetOptions.find((option) => option.value === preset) ?? presetOptions[0]

  async function handleRun() {
    if (!request.trim() || busy) return
    setError('')
    setResult(null)
    try {
      setStatus('creating')
      const project = await createProject({
        title: title.trim() || '未命名作品',
        user_request: request.trim(),
        preset,
      })
      if (audio) {
        setStatus('uploading')
        await uploadAsset(project.id, audio)
      }
      setStatus('running')
      const run = await runProject(project.id)
      setResult(run)
      setStatus('completed')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '未知错误')
      setStatus('failed')
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand" aria-label="南郭先生们">
          <span className="brand-mark"><img src="/icons.png" alt="" /></span>
          <span><strong>南郭先生们</strong><small>Agent Studio</small></span>
        </div>

        <button className="new-project" type="button" onClick={() => window.location.reload()}>
          <Plus size={16} /> 新建作品
        </button>

        <nav className="side-nav" aria-label="工作区导航">
          <button className={view === 'compose' ? 'active' : ''} onClick={() => setView('compose')}>
            <AudioLines size={17} /> 创作台
          </button>
          <button className={view === 'workflow' ? 'active' : ''} onClick={() => setView('workflow')}>
            <GitBranch size={17} /> 工作流
          </button>
        </nav>

        <div className="sidebar-card">
          <span>当前乐团</span>
          <strong>{selectedPreset.label}</strong>
          <small>{selectedPreset.description}</small>
        </div>

        <div className="recent-projects">
          <div className="section-label">本地项目</div>
          <div className="empty-projects">
            <FolderOpen size={18} />
            <span>运行后的项目保存在本地</span>
          </div>
        </div>

        <div className="local-badge"><CircleStop size={13} /> Local workspace</div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <div className="eyebrow">MUSIC AGENT STUDIO</div>
            <h1>{view === 'compose' ? '音乐创作工作台' : '乐团工作流'}</h1>
          </div>
          <div className={`run-state ${status}`}>
            {busy ? <LoaderCircle className="spin" size={15} /> : <span className="status-dot" />}
            {statusCopy[status]}
          </div>
        </header>

        {view === 'compose' ? (
          <div className="compose-layout">
            <section className="brief-panel">
              <div className="panel-heading">
                <div><span>01</span><h2>创作输入</h2></div>
                <SlidersHorizontal size={18} />
              </div>

              <div className="field-grid">
                <label className="field">
                  <span>作品名称</span>
                  <input value={title} maxLength={100} onChange={(event) => setTitle(event.target.value)} />
                </label>

                <fieldset className="field">
                  <legend>预设乐团</legend>
                  <div className="select-wrap">
                    <select value={preset} onChange={(event) => setPreset(event.target.value as Preset)}>
                      {presetOptions.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </div>
                </fieldset>
              </div>

              <div className="preset-card">
                <Sparkles size={16} />
                <div>
                  <strong>{selectedPreset.label}</strong>
                  <span>{selectedPreset.description}</span>
                </div>
              </div>

              <label className="field grow">
                <span>音乐构想</span>
                <textarea
                  value={request}
                  onChange={(event) => setRequest(event.target.value)}
                  placeholder="描述风格、情绪、主题、配器或想讲述的故事..."
                  maxLength={2000}
                />
                <small>{request.length} / 2000</small>
              </label>

              <label className={`upload-zone ${audio ? 'has-file' : ''}`}>
                <input
                  type="file"
                  accept="audio/mp3,audio/mpeg,audio/wav,audio/flac,audio/mp4,audio/ogg"
                  onChange={(event) => setAudio(event.target.files?.[0] ?? null)}
                />
                {audio ? <FileAudio size={22} /> : <Upload size={22} />}
                <span>{audio ? audio.name : '参考音频'}</span>
                <small>{audio ? `${(audio.size / 1024 / 1024).toFixed(1)} MB` : 'MP3, WAV, FLAC, M4A · 最大 20 MB'}</small>
                {audio && (
                  <button
                    className="clear-file"
                    type="button"
                    onClick={(event) => {
                      event.preventDefault()
                      setAudio(null)
                    }}
                    title="移除参考音频"
                  >
                    <X size={14} />
                  </button>
                )}
              </label>

              <button className="run-button" type="button" disabled={!request.trim() || busy} onClick={handleRun}>
                {busy ? <LoaderCircle className="spin" size={18} /> : <Play size={18} fill="currentColor" />}
                {busy ? statusCopy[status] : '召集乐团开始创作'}
                {!busy && <ChevronRight size={17} />}
              </button>
            </section>

            <section className="output-panel">
              <div className="panel-heading">
                <div><span>02</span><h2>乐团编排</h2></div>
                <button className="icon-button" type="button" title="查看工作流" onClick={() => setView('workflow')}>
                  <GitBranch size={17} />
                </button>
              </div>
              <div className="mini-flow"><WorkflowCanvas preset={preset} compact /></div>
            </section>

            <section className="status-panel">
              <div className="panel-heading">
                <div><span>03</span><h2>执行状态</h2></div>
                {status === 'completed' ? <CheckCircle2 size={17} /> : <Clock3 size={17} />}
              </div>
              <div className="step-list">
                {statusSteps.map((step) => (
                  <div className={`step-item ${stepState(status, step.value)}`} key={step.value}>
                    <span>{stepState(status, step.value) === 'done' ? <CheckCircle2 size={14} /> : <span />}</span>
                    <strong>{step.label}</strong>
                  </div>
                ))}
              </div>
              <div className="run-summary">
                <span>状态</span>
                <strong>{statusCopy[status]}</strong>
              </div>
            </section>

            <section className="result-panel">
              <div className="panel-heading">
                <div><span>04</span><h2>作品输出</h2></div>
                <Waves size={18} />
              </div>
              <div className="result-area">
                {finalPrompt ? (
                  <>
                    <div className="result-title"><Headphones size={17} /> 生成音乐</div>
                    {demoAudio && (
                      <article className="demo-audio">
                        <div className="track-heading">
                          <strong>中间 Demo 音频</strong>
                          <span>{demoAudio.duration_seconds.toFixed(0)} 秒 · {demoAudio.tempo_bpm} BPM</span>
                        </div>
                        <audio controls preload="metadata" src={mediaUrl(demoAudio.audio_url)} />
                      </article>
                    )}
                    {generatedTracks.length > 0 ? (
                      <div className="track-list">
                        {generatedTracks.map((track, index) => (
                          <article className="track-item" key={`${track.audio_url}-${index}`}>
                            <div className="track-heading">
                              <strong>{track.title || `生成音乐 ${index + 1}`}</strong>
                              <a className="download-link" href={mediaUrl(track.download_url)} download>
                                <Download size={15} /> 下载
                              </a>
                            </div>
                            <audio controls preload="metadata" src={mediaUrl(track.audio_url)} />
                            {audioAnalyses[index]?.waveform_url && (
                              <img
                                className="waveform-image"
                                src={mediaUrl(audioAnalyses[index].waveform_url)}
                                alt={`${track.title || `生成音乐 ${index + 1}`} 波形图`}
                              />
                            )}
                            {audioAnalyses[index]?.inspection && (
                              <div className="audio-facts">
                                {audioAnalyses[index].inspection.duration_seconds && (
                                  <span>{audioAnalyses[index].inspection.duration_seconds.toFixed(0)} 秒</span>
                                )}
                                {audioAnalyses[index].inspection.codec_name && (
                                  <span>{audioAnalyses[index].inspection.codec_name}</span>
                                )}
                                {audioAnalyses[index].inspection.sample_rate && (
                                  <span>{audioAnalyses[index].inspection.sample_rate} Hz</span>
                                )}
                              </div>
                            )}
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p>音乐生成完成后会在这里显示播放器。</p>
                    )}
                    <details className="prompt-details">
                      <summary><Sparkles size={15} /> 最终音乐提示词</summary>
                      <p>{finalPrompt}</p>
                    </details>
                    <div className="result-meta">
                      <span>{String(result?.state.workflow ?? preset)}</span>
                      <span>{finalPrompt.length} 字符</span>
                      <span>{generatedTracks.length} 首音乐</span>
                    </div>
                  </>
                ) : error ? (
                  <div className="error-message"><strong>工作流未完成</strong><span>{error}</span></div>
                ) : (
                  <div className="empty-result">
                    <span className="empty-icon"><Sparkles size={22} /></span>
                    <strong>等待你的音乐构想</strong>
                    <span>生成完成后会在这里播放和下载音乐</span>
                  </div>
                )}
              </div>
            </section>
          </div>
        ) : (
          <section className="workflow-panel">
            <div className="workflow-toolbar">
              <div>
                <h2>乐团编排</h2>
                <p>拖动节点检查当前预设的执行路径</p>
              </div>
              <div className="select-wrap workflow-select">
                <select value={preset} onChange={(event) => setPreset(event.target.value as Preset)}>
                  {presetOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="full-flow"><WorkflowCanvas preset={preset} /></div>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
