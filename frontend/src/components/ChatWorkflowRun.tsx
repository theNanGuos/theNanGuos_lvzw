import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, Download, GitBranch, LoaderCircle, Music2, TriangleAlert } from 'lucide-react'
import {
  getRun,
  mediaUrl,
  type ChatWorkflowRun as WorkflowRunReference,
  type GeneratedAudioAnalysis,
  type GeneratedTrack,
  type RunResult,
} from '../api'
import { WorkflowCanvas } from './WorkflowCanvas'

const presetLabels = {
  auto: '自动选择',
  pop_vocal: '流行人声',
  classical_instrumental: '古典器乐',
  electronic_instrumental: '电子器乐',
  soundtrack_score: '影视配乐',
  jazz_ensemble: '爵士乐团',
  rock_vocal: '摇滚人声',
  folk_acoustic: '原声民谣',
  hiphop_vocal: '嘻哈人声',
}

function stageLabel(stage: string) {
  return {
    workflow: '乐团创作',
    demo_audio: '渲染预览',
    music_generation: '生成音乐',
    audio_analysis: '分析音频',
    completed: '创作完成',
    failed: '执行失败',
    interrupted: '执行中断',
  }[stage] ?? stage
}

export function ChatWorkflowRun({ reference }: { reference: WorkflowRunReference }) {
  const [run, setRun] = useState<RunResult | null>(null)
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    let cancelled = false
    let timer = 0

    async function refresh() {
      try {
        const nextRun = await getRun(reference.project_id, reference.run_id)
        if (cancelled) return
        setRun(nextRun)
        setLoadError('')
        if (nextRun.status === 'running') {
          timer = window.setTimeout(() => void refresh(), 900)
        }
      } catch (reason) {
        if (cancelled) return
        setLoadError(reason instanceof Error ? reason.message : '运行状态读取失败')
      }
    }

    void refresh()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [reference.project_id, reference.run_id])

  const tracks = useMemo(
    () => (run?.state.generated_tracks as GeneratedTrack[] | undefined) ?? [],
    [run],
  )
  const analyses = useMemo(
    () => (run?.state.generated_audio_analysis as GeneratedAudioAnalysis[] | undefined) ?? [],
    [run],
  )
  const status = run?.status ?? 'running'
  const progress = run?.progress ?? 0
  const currentStage = run?.current_stage ?? 'workflow'

  return (
    <section className={`chat-workflow-run ${status}`} aria-label={`${reference.title} 工作流`}>
      <header className="chat-run-heading">
        <div>
          <span><GitBranch size={14} /> {presetLabels[reference.preset]}</span>
          <strong>{reference.title}</strong>
        </div>
        <span className={`chat-run-status ${status}`}>
          {status === 'completed'
            ? <CheckCircle2 size={15} />
            : status === 'failed'
              ? <TriangleAlert size={15} />
              : <LoaderCircle className="spin" size={15} />}
          {status === 'completed' ? '已完成' : status === 'failed' ? '失败' : '执行中'}
        </span>
      </header>

      <div className="chat-run-canvas">
        <WorkflowCanvas
          preset={reference.preset}
          compact
          runStatus={status === 'draft' ? 'idle' : status}
          currentStage={currentStage}
        />
      </div>

      <div className="chat-run-progress">
        <div><span>{stageLabel(currentStage)}</span><strong>{progress}%</strong></div>
        <i aria-label={`执行进度 ${progress}%`}><span style={{ width: `${progress}%` }} /></i>
      </div>

      {(loadError || run?.error) && (
        <div className="chat-run-error"><TriangleAlert size={15} /> {loadError || run?.error}</div>
      )}

      {tracks.length > 0 && (
        <div className="chat-run-tracks">
          {tracks.map((track, index) => {
            const analysis = analyses[index]
            const duration = analysis?.inspection.duration_seconds ?? track.duration_seconds
            return (
              <article className="chat-track" key={`${track.audio_url}-${index}`}>
                {track.cover_url ? (
                  <img src={mediaUrl(track.cover_url)} alt={`${track.title} 封面`} />
                ) : (
                  <span className="chat-track-cover"><Music2 size={24} /></span>
                )}
                <div className="chat-track-content">
                  <div className="chat-track-heading">
                    <div><strong>{track.title || `生成音乐 ${index + 1}`}</strong><span>{track.style || presetLabels[reference.preset]}</span></div>
                    <a href={mediaUrl(track.download_url)} download title="下载音乐"><Download size={17} /></a>
                  </div>
                  <audio controls preload="metadata" src={mediaUrl(track.audio_url)} />
                  {analysis?.waveform_url && (
                    <img className="chat-track-waveform" src={mediaUrl(analysis.waveform_url)} alt={`${track.title} 波形图`} />
                  )}
                  {duration && <small>{Math.round(duration)} 秒</small>}
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
