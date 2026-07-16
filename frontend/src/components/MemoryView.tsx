import { useState } from 'react'
import { Brain, Check, Music2, Pencil, RotateCcw, Save, Trash2, X } from 'lucide-react'
import type { MemoryKind, PortfolioItem, UserPreference, UserProfile } from '../api'

const preferenceLabels: Record<string, string> = {
  vocal_preference: '人声偏好',
  preferred_genres: '偏好流派',
  preferred_languages: '偏好语言',
  preferred_instruments: '偏好乐器',
  avoided_instruments: '避免乐器',
  default_duration: '默认时长',
  production_style: '制作风格',
}

const workflowLabels: Record<string, string> = {
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

interface MemoryViewProps {
  profile: UserProfile | null
  loading: boolean
  onRefresh: () => Promise<void>
  onUpdate: (preference: UserPreference, value: string, kind: MemoryKind) => Promise<void>
  onDelete: (key: string) => Promise<void>
  onClear: () => Promise<void>
  works: PortfolioItem[]
  onOpenWork: (work: PortfolioItem) => void
}

function PreferenceRow({
  preference,
  onUpdate,
  onDelete,
}: {
  preference: UserPreference
  onUpdate: MemoryViewProps['onUpdate']
  onDelete: MemoryViewProps['onDelete']
}) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(preference.value)
  const [saving, setSaving] = useState(false)

  async function save() {
    const normalized = value.trim()
    if (!normalized || saving) return
    setSaving(true)
    try {
      await onUpdate(preference, normalized, preference.kind)
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  return (
    <article className="memory-row">
      <div className="memory-row-icon"><Brain size={17} /></div>
      <div className="memory-row-content">
        <span>{preferenceLabels[preference.key] ?? preference.key}</span>
        {editing ? (
          <input value={value} maxLength={300} onChange={(event) => setValue(event.target.value)} aria-label={`编辑${preferenceLabels[preference.key] ?? preference.key}`} />
        ) : (
          <strong>{preference.value}</strong>
        )}
        <small>
          {Math.round(preference.confidence * 100)}% 置信度 · {preference.evidence_count} 次确认 · {new Date(preference.last_seen_at).toLocaleDateString('zh-CN')}
        </small>
      </div>
      <div className="memory-row-actions">
        {editing ? (
          <>
            <button type="button" onClick={() => void save()} disabled={saving || !value.trim()} title="保存"><Save size={16} /></button>
            <button type="button" onClick={() => { setValue(preference.value); setEditing(false) }} title="取消"><X size={16} /></button>
          </>
        ) : (
          <>
            <button type="button" onClick={() => setEditing(true)} title="编辑"><Pencil size={16} /></button>
            <button type="button" onClick={() => void onDelete(preference.key)} title="删除"><Trash2 size={16} /></button>
          </>
        )}
      </div>
    </article>
  )
}

export function MemoryView({ profile, loading, onRefresh, onUpdate, onDelete, onClear, works, onOpenWork }: MemoryViewProps) {
  const preferences = profile?.preferences ?? []
  const workflows = Object.entries(profile?.workflow_counts ?? {}).sort(([, left], [, right]) => (right ?? 0) - (left ?? 0))

  return (
    <section className="memory-page">
      <header className="memory-titlebar">
        <div>
          <span>LONG-TERM MEMORY</span>
          <h2>记忆库</h2>
          <p>{preferences.length} 条长期偏好 · 跨会话生效</p>
        </div>
        <div>
          <button type="button" onClick={() => void onRefresh()} disabled={loading} title="刷新记忆"><RotateCcw className={loading ? 'spin' : ''} size={17} /></button>
          <button className="memory-clear" type="button" onClick={() => void onClear()} disabled={!preferences.length}>
            <Trash2 size={16} /> 清空记忆
          </button>
        </div>
      </header>

      <div className="memory-band">
        <Check size={17} />
        <span>当前消息和创作台显式参数优先；长期记忆只补充未指定内容。</span>
      </div>

      <section className="memory-section">
        <div className="memory-section-heading"><h3>偏好与习惯</h3><span>{preferences.length}</span></div>
        {preferences.length ? (
          <div className="memory-list">
            {preferences.map((preference) => (
              <PreferenceRow preference={preference} onUpdate={onUpdate} onDelete={onDelete} key={preference.key} />
            ))}
          </div>
        ) : (
          <div className="memory-empty"><Brain size={24} /><strong>还没有长期偏好</strong><span>在对话中明确说“以后默认……”后会记录在这里。</span></div>
        )}
      </section>

      <section className="memory-section">
        <div className="memory-section-heading"><h3>创作习惯</h3><span>{workflows.length}</span></div>
        <div className="memory-workflows">
          {workflows.length ? workflows.map(([workflow, count]) => (
            <div key={workflow}><span>{workflowLabels[workflow] ?? workflow}</span><strong>{count} 次</strong></div>
          )) : <span className="memory-muted">完成作品后会在这里累计工作流使用次数。</span>}
        </div>
      </section>

      <section className="memory-section">
        <div className="memory-section-heading"><h3>最近创作经历</h3><span>{works.length}</span></div>
        {works.length ? (
          <div className="memory-experiences">
            {works.slice(0, 6).map((work) => (
              <button type="button" onClick={() => onOpenWork(work)} key={work.project_id}>
                <span><Music2 size={16} /></span>
                <div><strong>{work.title}</strong><small>{workflowLabels[work.preset]} · {new Date(work.updated_at).toLocaleDateString('zh-CN')}</small></div>
                <em>{work.status === 'completed' ? '已完成' : work.status === 'running' ? `${work.progress}%` : work.status}</em>
              </button>
            ))}
          </div>
        ) : <span className="memory-muted">完成的作品会作为创作经历保留在这里。</span>}
      </section>
    </section>
  )
}
