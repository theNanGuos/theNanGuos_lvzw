import { useEffect, useMemo, useRef, useState } from 'react'
import {
  AudioLines,
  Brain,
  CheckCircle2,
  ChevronRight,
  CircleStop,
  Clock3,
  Download,
  FileAudio,
  GitBranch,
  Headphones,
  History,
  LoaderCircle,
  Library,
  MessageSquare,
  Paperclip,
  Play,
  Plus,
  SlidersHorizontal,
  Sparkles,
  Send,
  Upload,
  Waves,
  X,
} from 'lucide-react'
import {
  createProject,
  createSession,
  clearMemory,
  deleteSession,
  deleteMemoryPreference,
  getMemory,
  getProject,
  getRun,
  getSession,
  listPortfolio,
  listSessions,
  mediaUrl,
  renameSession,
  runProjectAsync,
  sendChatMessage,
  uploadAsset,
  uploadSessionAsset,
  updateMemoryPreference,
} from './api'
import type {
  ChatMessage,
  ChatSession,
  ChatSessionSummary,
  DemoAudio,
  GeneratedAudioAnalysis,
  GeneratedTrack,
  PortfolioItem,
  Preset,
  RunResult,
  UserPreference,
  UserProfile,
} from './api'
import { WorkflowCanvas } from './components/WorkflowCanvas'
import { ChatWorkflowRun } from './components/ChatWorkflowRun'
import { PortfolioView } from './components/PortfolioView'
import { SessionList } from './components/SessionList'
import { MemoryView } from './components/MemoryView'
import './App.css'

type View = 'chat' | 'compose' | 'portfolio' | 'memory' | 'workflow'
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
  { value: 'auto', label: '自动选择', description: '由指挥 Agent 选择合适的乐团路径' },
  { value: 'pop_vocal', label: '流行人声', description: '歌词、旋律、节奏和制作完整协作' },
  { value: 'classical_instrumental', label: '古典器乐', description: '主题、和声、配器与可选乐谱导出' },
  { value: 'electronic_instrumental', label: '电子器乐', description: '节奏先行，突出低频和音色设计' },
  { value: 'soundtrack_score', label: '影视配乐', description: '情绪叙事、空间声景和主题发展' },
]

const genreOptions = ['自动选择', '流行', '摇滚', '电子', 'R&B', '爵士', '古典', '民谣', '嘻哈', '影视配乐', '世界音乐']
const languageOptions = ['自动选择', '纯音乐', '中文', '英文', '日语', '韩语', '西班牙语']
const instrumentOptions = ['钢琴', '原声吉他', '电吉他', '弦乐', '管弦乐', '合成器', '鼓组', '贝斯', '民族乐器', '人声']

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

function sessionSummary(session: ChatSession): ChatSessionSummary {
  return {
    id: session.id,
    title: session.title,
    active_project_id: session.active_project_id,
    message_count: session.messages.length,
    created_at: session.created_at,
    updated_at: session.updated_at,
  }
}

function App() {
  const [view, setView] = useState<View>('chat')
  const [title, setTitle] = useState('未命名作品')
  const [request, setRequest] = useState('')
  const [preset, setPreset] = useState<Preset>('auto')
  const [genre, setGenre] = useState('自动选择')
  const [language, setLanguage] = useState('自动选择')
  const [instruments, setInstruments] = useState<string[]>([])
  const [audio, setAudio] = useState<File | null>(null)
  const [status, setStatus] = useState<RunStatus>('idle')
  const [result, setResult] = useState<RunResult | null>(null)
  const [error, setError] = useState('')
  const [progress, setProgress] = useState(0)
  const [currentStage, setCurrentStage] = useState('draft')
  const [portfolio, setPortfolio] = useState<PortfolioItem[]>([])
  const [memoryProfile, setMemoryProfile] = useState<UserProfile | null>(null)
  const [memoryLoading, setMemoryLoading] = useState(false)
  const [memoryNotice, setMemoryNotice] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [chatInput, setChatInput] = useState('')
  const [chatAudio, setChatAudio] = useState<File | null>(null)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatSending, setChatSending] = useState(false)
  const [chatSessions, setChatSessions] = useState<ChatSessionSummary[]>([])
  const [mobileSessionsOpen, setMobileSessionsOpen] = useState(false)
  const monitorVersion = useRef(0)
  const sessionSelectionVersion = useRef(0)
  const chatAudioInputRef = useRef<HTMLInputElement>(null)

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

  // Initialization intentionally runs once; URL history changes reload persisted state.
  /* oxlint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    void refreshPortfolio()
    void refreshMemory()
    void initializeSessions()

    const handleHistoryChange = () => window.location.reload()
    window.addEventListener('popstate', handleHistoryChange)
    return () => window.removeEventListener('popstate', handleHistoryChange)
  }, [])
  /* oxlint-enable react-hooks/exhaustive-deps */

  const hasRunningPortfolioItem = portfolio.some((item) => item.status === 'running')
  useEffect(() => {
    if (!hasRunningPortfolioItem) return
    const timer = window.setInterval(() => void refreshPortfolio(), 1200)
    return () => window.clearInterval(timer)
  }, [hasRunningPortfolioItem])

  useEffect(() => {
    if (!memoryNotice) return
    const timer = window.setTimeout(() => setMemoryNotice(''), 3600)
    return () => window.clearTimeout(timer)
  }, [memoryNotice])

  async function refreshPortfolio() {
    try {
      setPortfolio(await listPortfolio())
    } catch {
      // The primary workspace remains usable when the local API is unavailable.
    }
  }

  async function refreshMemory() {
    setMemoryLoading(true)
    try {
      setMemoryProfile(await getMemory())
    } catch {
      // Conversation and creation remain available if memory storage cannot be read.
    } finally {
      setMemoryLoading(false)
    }
  }

  async function handleMemoryUpdate(preference: UserPreference, value: string) {
    try {
      const updated = await updateMemoryPreference(preference.key, {
        value,
        kind: preference.kind,
        confidence: preference.confidence,
      })
      setMemoryProfile((profile) => profile ? {
        ...profile,
        preferences: profile.preferences.map((item) => item.key === updated.key ? updated : item),
      } : profile)
      setMemoryNotice(`已更新记忆：${updated.value}`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '记忆更新失败')
      throw reason
    }
  }

  async function handleMemoryDelete(key: string) {
    if (!window.confirm('删除这条长期记忆？')) return
    try {
      setMemoryProfile(await deleteMemoryPreference(key))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '记忆删除失败')
    }
  }

  async function handleMemoryClear() {
    if (!window.confirm('清空全部长期偏好和创作习惯？此操作不会删除作品。')) return
    try {
      setMemoryProfile(await clearMemory())
      setMemoryNotice('长期记忆已清空')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '记忆清空失败')
    }
  }

  async function refreshSessions() {
    const sessions = await listSessions()
    setChatSessions(sessions)
    return sessions
  }

  async function initializeSessions() {
    try {
      const sessions = await refreshSessions()
      const params = new URLSearchParams(window.location.search)
      const requestedId = params.get('session') || window.localStorage.getItem('nanguos.session')
      const session = sessions.find((item) => item.id === requestedId) || sessions[0]
      if (session) await selectSession(session.id, false)
    } catch {
      // A new local conversation can still be started when session restoration fails.
    }
  }

  function updateSessionLocation(nextSessionId: string, push: boolean) {
    const url = new URL(window.location.href)
    if (nextSessionId) {
      url.searchParams.set('session', nextSessionId)
      window.localStorage.setItem('nanguos.session', nextSessionId)
    } else {
      url.searchParams.delete('session')
      window.localStorage.removeItem('nanguos.session')
    }
    window.history[push ? 'pushState' : 'replaceState']({}, '', url)
  }

  function resetProjectState() {
    setTitle('未命名作品')
    setRequest('')
    setPreset('auto')
    setGenre('自动选择')
    setLanguage('自动选择')
    setInstruments([])
    setAudio(null)
    setStatus('idle')
    setProgress(0)
    setCurrentStage('draft')
    setResult(null)
    setError('')
  }

  async function restoreSessionProject(projectId: string, selectionVersion: number) {
    try {
      const project = await getProject(projectId)
      if (selectionVersion !== sessionSelectionVersion.current) return
      setTitle(project.title)
      setRequest(project.user_request)
      setPreset(project.preset)
      setGenre(!project.genre || project.genre === 'auto' ? '自动选择' : project.genre)
      setLanguage(!project.language || project.language === 'auto' ? '自动选择' : project.language)
      setInstruments(project.instruments ?? [])
      setProgress(project.progress)
      setCurrentStage(project.current_stage)
      setStatus(project.status === 'draft' ? 'idle' : project.status)
      setError(project.error || '')
      if (!project.latest_run_id) return
      if (project.status === 'running') {
        void monitorRun(project.id, project.latest_run_id).catch((reason) => {
          setError(reason instanceof Error ? reason.message : '作品状态恢复失败')
          setStatus('failed')
        })
      } else {
        const run = await getRun(project.id, project.latest_run_id)
        if (selectionVersion === sessionSelectionVersion.current) setResult(run)
      }
    } catch (reason) {
      if (selectionVersion !== sessionSelectionVersion.current) return
      setError(reason instanceof Error ? reason.message : '关联作品读取失败')
    }
  }

  async function selectSession(nextSessionId: string, push = true) {
    if (chatSending) return
    const selectionVersion = ++sessionSelectionVersion.current
    monitorVersion.current += 1
    const session = await getSession(nextSessionId)
    if (selectionVersion !== sessionSelectionVersion.current) return
    setSessionId(session.id)
    setChatMessages(session.messages)
    setChatInput('')
    setChatAudio(null)
    setView('chat')
    setMobileSessionsOpen(false)
    resetProjectState()
    updateSessionLocation(session.id, push)
    if (session.active_project_id) {
      await restoreSessionProject(session.active_project_id, selectionVersion)
    }
  }

  async function handleSelectSession(nextSessionId: string) {
    try {
      await selectSession(nextSessionId)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '会话读取失败')
    }
  }

  function startNewConversation(push = true) {
    if (chatSending) return
    sessionSelectionVersion.current += 1
    monitorVersion.current += 1
    setSessionId('')
    setChatMessages([])
    setChatInput('')
    setChatAudio(null)
    setView('chat')
    setMobileSessionsOpen(false)
    resetProjectState()
    updateSessionLocation('', push)
  }

  async function handleRenameSession(targetSessionId: string, nextTitle: string) {
    try {
      const updated = await renameSession(targetSessionId, nextTitle)
      setChatSessions((sessions) => sessions.map((item) => (
        item.id === updated.id
          ? { ...item, title: updated.title, updated_at: updated.updated_at }
          : item
      )))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '会话重命名失败')
      throw reason
    }
  }

  async function handleDeleteSession(targetSessionId: string) {
    try {
      await deleteSession(targetSessionId)
      const remaining = await refreshSessions()
      if (targetSessionId !== sessionId) return
      if (remaining[0]) await selectSession(remaining[0].id, false)
      else startNewConversation(false)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '会话删除失败')
      throw reason
    }
  }

  async function monitorRun(projectId: string, runId: string) {
    const version = ++monitorVersion.current
    setStatus('running')
    for (;;) {
      const run = await getRun(projectId, runId)
      if (version !== monitorVersion.current) return
      setProgress(run.progress)
      setCurrentStage(run.current_stage)
      if (run.status === 'completed') {
        setResult(run)
        setStatus('completed')
        await refreshPortfolio()
        return
      }
      if (run.status === 'failed') {
        throw new Error(run.error || '音乐工作流执行失败')
      }
      await new Promise((resolve) => window.setTimeout(resolve, 800))
    }
  }

  async function handleRun() {
    if (!request.trim() || busy) return
    monitorVersion.current += 1
    setError('')
    setResult(null)
    try {
      setStatus('creating')
      setProgress(2)
      setCurrentStage('creating_project')
      const project = await createProject({
        title: title.trim() || '未命名作品',
        user_request: request.trim(),
        preset,
        genre: genre === '自动选择' ? 'auto' : genre,
        language: language === '自动选择' ? 'auto' : language,
        instruments,
      })
      if (audio) {
        setStatus('uploading')
        setProgress(5)
        setCurrentStage('uploading_reference')
        await uploadAsset(project.id, audio)
      }
      setStatus('running')
      const run = await runProjectAsync(project.id)
      await monitorRun(project.id, run.id)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '未知错误')
      setStatus('failed')
    }
  }

  async function handleChat() {
    const content = chatInput.trim()
    if (!content || chatSending) return
    setChatSending(true)
    setChatInput('')
    setError('')
    setChatMessages((messages) => [
      ...messages,
      {
        id: `pending-${Date.now()}`,
        role: 'user',
        content,
        audio_attachments: chatAudio ? [{
          id: 'pending-audio',
          filename: chatAudio.name,
          path: '',
          content_type: chatAudio.type,
          size: chatAudio.size,
        }] : [],
        created_at: new Date().toISOString(),
      },
    ])
    try {
      let activeSessionId = sessionId
      if (!activeSessionId) {
        const session = await createSession(content.slice(0, 36))
        activeSessionId = session.id
        setSessionId(session.id)
        setChatSessions((sessions) => [sessionSummary(session), ...sessions])
        updateSessionLocation(session.id, true)
      }
      const attachment = chatAudio ? await uploadSessionAsset(activeSessionId, chatAudio) : null
      const response = await sendChatMessage(activeSessionId, content, attachment ? [attachment.id] : [])
      setChatAudio(null)
      if (chatAudioInputRef.current) chatAudioInputRef.current.value = ''
      setChatMessages(response.session.messages)
      if (response.remembered_preferences?.length) {
        setMemoryNotice(`已记住：${response.remembered_preferences.map((item) => item.value).join('、')}`)
        void refreshMemory()
      }
      setChatSessions((sessions) => [
        sessionSummary(response.session),
        ...sessions.filter((item) => item.id !== response.session.id),
      ])
      if (response.project_id) {
        const item = (await listPortfolio()).find((entry) => entry.project_id === response.project_id)
        if (item) {
          setTitle(item.title)
          setRequest(item.user_request)
          setPreset(item.preset)
          setProgress(item.progress)
          setCurrentStage(item.current_stage)
        }
      }
      await refreshPortfolio()
      await refreshSessions()
      if (response.project_id && response.run_id) {
        setChatSending(false)
        await monitorRun(response.project_id, response.run_id)
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '未知错误')
      setStatus('failed')
    } finally {
      setChatSending(false)
    }
  }

  async function openPortfolioItem(item: PortfolioItem) {
    monitorVersion.current += 1
    setTitle(item.title)
    setRequest(item.user_request)
    setPreset(item.preset)
    setProgress(item.progress)
    setCurrentStage(item.current_stage)
    setStatus(item.status === 'draft' ? 'idle' : item.status)
    setResult(null)
    setView('compose')
    if (!item.latest_run_id) return
    try {
      if (item.status === 'running') {
        await monitorRun(item.project_id, item.latest_run_id)
      } else {
        const run = await getRun(item.project_id, item.latest_run_id)
        setResult(run)
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '作品读取失败')
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

        <button
          className="new-project"
          type="button"
          onClick={() => view === 'chat' ? startNewConversation() : window.location.reload()}
        >
          <Plus size={16} /> {view === 'chat' ? '新建对话' : '新建作品'}
        </button>

        <nav className="side-nav" aria-label="工作区导航">
          <button className={view === 'chat' ? 'active' : ''} onClick={() => setView('chat')}>
            <MessageSquare size={17} /> 对话
          </button>
          <button className={view === 'compose' ? 'active' : ''} onClick={() => setView('compose')}>
            <AudioLines size={17} /> 创作台
          </button>
          <button className={view === 'portfolio' ? 'active' : ''} onClick={() => setView('portfolio')}>
            <Library size={17} /> 作品集
          </button>
          <button className={view === 'memory' ? 'active' : ''} onClick={() => { setView('memory'); void refreshMemory() }}>
            <Brain size={17} /> 记忆库
          </button>
          <button className={view === 'workflow' ? 'active' : ''} onClick={() => setView('workflow')}>
            <GitBranch size={17} /> 工作流
          </button>
        </nav>

        {view === 'chat' ? (
          <SessionList
            sessions={chatSessions}
            activeSessionId={sessionId}
            disabled={chatSending}
            onNew={() => startNewConversation()}
            onSelect={(id) => void handleSelectSession(id)}
            onRename={handleRenameSession}
            onDelete={handleDeleteSession}
          />
        ) : view === 'memory' ? (
          <div className="sidebar-card">
            <span>长期记忆</span>
            <strong>{memoryProfile?.preferences.length ?? 0} 条偏好</strong>
            <small>在所有会话和自动创作中生效</small>
          </div>
        ) : (
          <div className="sidebar-card">
            <span>当前乐团</span>
            <strong>{selectedPreset.label}</strong>
            <small>{selectedPreset.description}</small>
          </div>
        )}

        <div className="local-badge"><CircleStop size={13} /> Local workspace</div>
      </aside>

      {mobileSessionsOpen && (
        <div className="session-drawer" role="dialog" aria-modal="true" aria-label="对话列表">
          <button className="session-drawer-backdrop" type="button" onClick={() => setMobileSessionsOpen(false)} aria-label="关闭对话列表" />
          <aside>
            <div className="session-drawer-heading"><strong>对话</strong><button type="button" onClick={() => setMobileSessionsOpen(false)} title="关闭"><X size={17} /></button></div>
            <SessionList
              sessions={chatSessions}
              activeSessionId={sessionId}
              disabled={chatSending}
              onNew={() => startNewConversation()}
              onSelect={(id) => void handleSelectSession(id)}
              onRename={handleRenameSession}
              onDelete={handleDeleteSession}
            />
          </aside>
        </div>
      )}

      <main className="workspace">
        <header className="topbar">
          <div>
            <div className="eyebrow">MUSIC AGENT STUDIO</div>
            <h1>{view === 'chat' ? '与南郭先生对话' : view === 'compose' ? '音乐创作工作台' : view === 'portfolio' ? '我的作品集' : view === 'memory' ? '长期记忆库' : '乐团工作流'}</h1>
          </div>
          <div className={`run-state ${status}`}>
            {busy ? <LoaderCircle className="spin" size={15} /> : <span className="status-dot" />}
            {statusCopy[status]}
          </div>
        </header>

        {memoryNotice && <div className="memory-notice" role="status"><Brain size={16} /><span>{memoryNotice}</span></div>}

        {view === 'chat' ? (
          <section className="chat-panel">
            <div className="chat-heading">
              <div>
                <span>南郭乐团代表</span>
                <h2>南郭先生</h2>
              </div>
              <div className="chat-heading-actions">
                <button className="mobile-session-button" type="button" onClick={() => setMobileSessionsOpen(true)} title="查看对话"><History size={18} /></button>
                <MessageSquare size={20} />
              </div>
            </div>
            <div className="chat-messages" aria-live="polite">
              {chatMessages.length === 0 ? (
                <div className="chat-empty">
                  <Sparkles size={24} />
                  <strong>从一个想法开始</strong>
                </div>
              ) : chatMessages.map((message) => (
                <article className={`chat-message ${message.role} ${message.workflow_run ? 'has-workflow' : ''}`} key={message.id}>
                  <span>{message.role === 'user' ? '你' : '南郭先生'}</span>
                  <p>{message.content}</p>
                  {message.audio_attachments?.map((attachment) => (
                    <div className="chat-audio-attachment" key={attachment.id}>
                      <FileAudio size={15} />
                      <span>{attachment.filename}</span>
                      <small>{(attachment.size / 1024 / 1024).toFixed(1)} MB</small>
                    </div>
                  ))}
                  {!!message.remembered_preferences?.length && (
                    <div className="chat-memory-confirmation">
                      <Brain size={16} />
                      <div><strong>偏好已记录</strong><span>{message.remembered_preferences.map((item) => item.value).join('、')}</span></div>
                    </div>
                  )}
                  {message.workflow_run && <ChatWorkflowRun reference={message.workflow_run} />}
                </article>
              ))}
              {chatSending && (
                <div className="chat-thinking"><LoaderCircle className="spin" size={15} /> 正在处理</div>
              )}
            </div>
            {error && <div className="chat-error">{error}</div>}
            <form className="chat-composer" onSubmit={(event) => { event.preventDefault(); void handleChat() }}>
              {chatAudio && (
                <div className="chat-file-chip">
                  <FileAudio size={15} />
                  <span>{chatAudio.name}</span>
                  <button
                    type="button"
                    onClick={() => {
                      setChatAudio(null)
                      if (chatAudioInputRef.current) chatAudioInputRef.current.value = ''
                    }}
                    title="移除参考音频"
                  ><X size={14} /></button>
                </div>
              )}
              <input
                ref={chatAudioInputRef}
                className="chat-file-input"
                type="file"
                accept="audio/mp3,audio/mpeg,audio/wav,audio/flac,audio/mp4,audio/ogg"
                onChange={(event) => setChatAudio(event.target.files?.[0] ?? null)}
              />
              <button
                className="chat-attach-button"
                type="button"
                onClick={() => chatAudioInputRef.current?.click()}
                disabled={chatSending}
                title="添加参考音频"
              >
                <Paperclip size={18} />
                <span>上传参考音频</span>
              </button>
              <textarea
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                placeholder="例如：以后默认给我做纯音乐，这次想要一首雨夜氛围电子曲"
                maxLength={4000}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    void handleChat()
                  }
                }}
              />
              <button type="submit" disabled={!chatInput.trim() || chatSending} title="发送">
                {chatSending ? <LoaderCircle className="spin" size={18} /> : <Send size={18} />}
              </button>
            </form>
          </section>
        ) : view === 'portfolio' ? (
          <PortfolioView items={portfolio} onOpenProject={(item) => void openPortfolioItem(item)} />
        ) : view === 'memory' ? (
          <MemoryView
            profile={memoryProfile}
            loading={memoryLoading}
            onRefresh={refreshMemory}
            onUpdate={handleMemoryUpdate}
            onDelete={handleMemoryDelete}
            onClear={handleMemoryClear}
            works={portfolio}
            onOpenWork={(work) => void openPortfolioItem(work)}
          />
        ) : view === 'compose' ? (
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
                    <select aria-label="预设乐团" value={preset} onChange={(event) => setPreset(event.target.value as Preset)}>
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

              <div className="creative-controls">
                <fieldset className="field">
                  <legend>流派</legend>
                  <div className="select-wrap">
                    <select aria-label="流派" value={genre} onChange={(event) => setGenre(event.target.value)}>
                      {genreOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </div>
                </fieldset>
                <fieldset className="field">
                  <legend>语言</legend>
                  <div className="select-wrap">
                    <select aria-label="语言" value={language} onChange={(event) => setLanguage(event.target.value)}>
                      {languageOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </div>
                </fieldset>
              </div>

              <fieldset className="field instrument-field">
                <legend>主要乐器</legend>
                <div className="instrument-options">
                  {instrumentOptions.map((instrument) => {
                    const selected = instruments.includes(instrument)
                    return (
                      <button
                        type="button"
                        aria-pressed={selected}
                        className={selected ? 'selected' : ''}
                        key={instrument}
                        onClick={() => setInstruments((current) => (
                          selected ? current.filter((item) => item !== instrument) : [...current, instrument]
                        ))}
                      >
                        {instrument}
                      </button>
                    )
                  })}
                </div>
              </fieldset>

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
              <div className="progress-track" aria-label={`执行进度 ${progress}%`}>
                <span style={{ width: `${progress}%` }} />
              </div>
              <div className="stage-label"><span>{currentStage}</span><strong>{progress}%</strong></div>
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
