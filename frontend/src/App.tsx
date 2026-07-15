import { useMemo, useState } from 'react'
import {
  AudioLines,
  ChevronRight,
  CircleStop,
  Download,
  FileAudio,
  FolderOpen,
  GitBranch,
  Headphones,
  LoaderCircle,
  Music2,
  Play,
  Plus,
  SlidersHorizontal,
  Sparkles,
  Upload,
} from 'lucide-react'
import { createProject, mediaUrl, runProject, uploadAsset } from './api'
import type { GeneratedTrack, Preset, RunResult } from './api'
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
          <span className="brand-mark"><Music2 size={19} /></span>
          <span>南郭先生们</span>
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
            <h1>{view === 'compose' ? '创作台' : '工作流'}</h1>
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
                <div><span>01</span><h2>创作简报</h2></div>
                <SlidersHorizontal size={18} />
              </div>

              <label className="field">
                <span>作品名称</span>
                <input value={title} maxLength={100} onChange={(event) => setTitle(event.target.value)} />
              </label>

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

              <fieldset className="field">
                <legend>预设乐团</legend>
                <div className="preset-control">
                  {([
                    ['auto', '自动'],
                    ['pop_vocal', '流行人声'],
                    ['classical_instrumental', '古典器乐'],
                  ] as const).map(([value, label]) => (
                    <button
                      type="button"
                      key={value}
                      className={preset === value ? 'selected' : ''}
                      onClick={() => setPreset(value)}
                    >{label}</button>
                  ))}
                </div>
              </fieldset>

              <label className={`upload-zone ${audio ? 'has-file' : ''}`}>
                <input
                  type="file"
                  accept="audio/mp3,audio/mpeg,audio/wav,audio/flac,audio/mp4,audio/ogg"
                  onChange={(event) => setAudio(event.target.files?.[0] ?? null)}
                />
                {audio ? <FileAudio size={22} /> : <Upload size={22} />}
                <span>{audio ? audio.name : '添加参考音频'}</span>
                <small>{audio ? `${(audio.size / 1024 / 1024).toFixed(1)} MB` : 'MP3, WAV, FLAC, M4A · 最大 20 MB'}</small>
              </label>

              <button className="run-button" type="button" disabled={!request.trim() || busy} onClick={handleRun}>
                {busy ? <LoaderCircle className="spin" size={18} /> : <Play size={18} fill="currentColor" />}
                {busy ? statusCopy[status] : '召集乐团开始创作'}
                {!busy && <ChevronRight size={17} />}
              </button>
            </section>

            <section className="output-panel">
              <div className="panel-heading">
                <div><span>02</span><h2>乐团工作区</h2></div>
                <button className="icon-button" type="button" title="查看工作流" onClick={() => setView('workflow')}>
                  <GitBranch size={17} />
                </button>
              </div>
              <div className="mini-flow"><WorkflowCanvas preset={preset} compact /></div>
              <div className="result-area">
                {finalPrompt ? (
                  <>
                    <div className="result-title"><Headphones size={17} /> 生成音乐</div>
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
              <div className="preset-control compact-control">
                {(['auto', 'pop_vocal', 'classical_instrumental'] as Preset[]).map((value) => (
                  <button key={value} className={preset === value ? 'selected' : ''} onClick={() => setPreset(value)}>
                    {value === 'auto' ? '自动' : value === 'pop_vocal' ? '流行人声' : '古典器乐'}
                  </button>
                ))}
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
