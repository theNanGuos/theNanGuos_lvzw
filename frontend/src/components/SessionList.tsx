import { useState } from 'react'
import { Check, MessageSquare, MoreHorizontal, Pencil, Plus, Trash2, X } from 'lucide-react'
import type { ChatSessionSummary } from '../api'

interface SessionListProps {
  sessions: ChatSessionSummary[]
  activeSessionId: string
  disabled?: boolean
  onNew: () => void
  onSelect: (sessionId: string) => void
  onRename: (sessionId: string, title: string) => Promise<void>
  onDelete: (sessionId: string) => Promise<void>
}

function relativeDate(value: string) {
  const date = new Date(value)
  const today = new Date()
  if (date.toDateString() === today.toDateString()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}

export function SessionList({
  sessions,
  activeSessionId,
  disabled = false,
  onNew,
  onSelect,
  onRename,
  onDelete,
}: SessionListProps) {
  const [menuId, setMenuId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [saving, setSaving] = useState(false)
  const [actionError, setActionError] = useState('')

  function beginRename(session: ChatSessionSummary) {
    setEditingId(session.id)
    setDraftTitle(session.title)
    setMenuId(null)
  }

  async function saveRename(sessionId: string) {
    const title = draftTitle.trim()
    if (!title || saving) return
    setSaving(true)
    setActionError('')
    try {
      await onRename(sessionId, title)
      setEditingId(null)
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : '重命名失败')
    } finally {
      setSaving(false)
    }
  }

  async function removeSession(session: ChatSessionSummary) {
    setMenuId(null)
    if (!window.confirm(`删除对话“${session.title}”？关联作品会继续保留。`)) return
    setActionError('')
    try {
      await onDelete(session.id)
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : '删除失败')
    }
  }

  return (
    <section className="session-list-panel">
      <div className="session-list-heading">
        <span>最近对话</span>
        <button type="button" onClick={onNew} disabled={disabled} title="新建对话"><Plus size={15} /></button>
      </div>
      <div className="session-list">
        {actionError && <div className="session-action-error">{actionError}</div>}
        {sessions.length === 0 ? (
          <div className="session-list-empty"><MessageSquare size={16} /><span>暂无对话</span></div>
        ) : sessions.map((session) => (
          <div className={`session-row ${session.id === activeSessionId ? 'active' : ''}`} key={session.id}>
            {editingId === session.id ? (
              <form onSubmit={(event) => { event.preventDefault(); void saveRename(session.id) }}>
                <input
                  autoFocus
                  value={draftTitle}
                  maxLength={100}
                  onChange={(event) => setDraftTitle(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Escape') setEditingId(null)
                  }}
                />
                <button type="submit" disabled={!draftTitle.trim() || saving} title="保存"><Check size={14} /></button>
                <button type="button" onClick={() => setEditingId(null)} title="取消"><X size={14} /></button>
              </form>
            ) : (
              <>
                <button
                  className="session-select"
                  type="button"
                  disabled={disabled}
                  onClick={() => { setMenuId(null); onSelect(session.id) }}
                >
                  <MessageSquare size={14} />
                  <span><strong>{session.title}</strong><small>{relativeDate(session.updated_at)}</small></span>
                </button>
                <button
                  className="session-menu-trigger"
                  type="button"
                  title="对话操作"
                  onClick={() => setMenuId((current) => current === session.id ? null : session.id)}
                >
                  <MoreHorizontal size={15} />
                </button>
                {menuId === session.id && (
                  <div className="session-menu">
                    <button type="button" onClick={() => beginRename(session)}><Pencil size={13} /> 重命名</button>
                    <button type="button" className="danger" onClick={() => void removeSession(session)}><Trash2 size={13} /> 删除</button>
                  </div>
                )}
              </>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}
