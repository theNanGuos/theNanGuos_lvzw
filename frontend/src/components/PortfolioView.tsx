import { useMemo, useRef, useState } from 'react'
import {
  ArrowUpRight,
  Clock3,
  Disc3,
  Download,
  Library,
  Pause,
  Play,
  Search,
} from 'lucide-react'
import { mediaUrl } from '../api'
import type { PortfolioItem, PortfolioTrack } from '../api'

interface PortfolioViewProps {
  items: PortfolioItem[]
  onOpenProject: (item: PortfolioItem) => void
}

interface LibraryTrack {
  key: string
  project: PortfolioItem
  track: PortfolioTrack
}

function durationLabel(seconds?: number | null) {
  if (!seconds) return '--:--'
  const minutes = Math.floor(seconds / 60)
  return `${minutes}:${Math.round(seconds % 60).toString().padStart(2, '0')}`
}

function Cover({ track, className = '' }: { track: PortfolioTrack; className?: string }) {
  return track.cover_url ? (
    <img className={className} src={mediaUrl(track.cover_url)} alt={`${track.title} 封面`} />
  ) : (
    <div className={`${className} cover-fallback`}><Disc3 /></div>
  )
}

export function PortfolioView({ items, onOpenProject }: PortfolioViewProps) {
  const [query, setQuery] = useState('')
  const [playingKey, setPlayingKey] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const runningItems = items.filter((item) => item.status === 'running')
  const tracks = useMemo(
    () => items.flatMap((project) => project.tracks.map((track, index) => ({
      key: `${project.project_id}-${index}`,
      project,
      track,
    }))),
    [items],
  )
  const filteredTracks = tracks.filter(({ track, project }) => {
    const needle = query.trim().toLocaleLowerCase()
    if (!needle) return true
    return `${track.title} ${track.style} ${project.title}`.toLocaleLowerCase().includes(needle)
  })
  const featured = filteredTracks[0]
  const playing = tracks.find((item) => item.key === playingKey)

  function toggleTrack(item: LibraryTrack) {
    const audio = audioRef.current
    if (playingKey === item.key && audio && !audio.paused) {
      audio.pause()
      setPlayingKey(null)
      return
    }
    setPlayingKey(item.key)
    window.setTimeout(() => void audioRef.current?.play(), 0)
  }

  return (
    <section className="portfolio-page">
      <header className="portfolio-titlebar">
        <div>
          <span>YOUR MUSIC LIBRARY</span>
          <h2>作品集</h2>
          <p>{tracks.length} 首作品 · {runningItems.length} 个任务正在生成</p>
        </div>
        <label className="portfolio-search">
          <Search size={16} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索歌曲或风格" />
        </label>
      </header>

      {featured ? (
        <div className="portfolio-featured">
          <Cover track={featured.track} className="featured-cover" />
          <div className="featured-copy">
            <span>最近作品</span>
            <h3>{featured.track.title}</h3>
            <p>{featured.track.style || featured.project.user_request}</p>
            <div className="featured-meta">
              <span><Clock3 size={14} /> {durationLabel(featured.track.duration_seconds)}</span>
              <span>{new Date(featured.project.updated_at).toLocaleDateString('zh-CN')}</span>
            </div>
            <div className="featured-actions">
              <button className="featured-play" type="button" onClick={() => toggleTrack(featured)}>
                {playingKey === featured.key ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
                {playingKey === featured.key ? '暂停' : '播放'}
              </button>
              <a href={mediaUrl(featured.track.download_url)} download title="下载歌曲"><Download size={18} /></a>
              <button type="button" title="打开项目" onClick={() => onOpenProject(featured.project)}><ArrowUpRight size={18} /></button>
            </div>
          </div>
        </div>
      ) : (
        <div className="portfolio-empty">
          <Library size={28} />
          <strong>{query ? '没有匹配的作品' : '作品集还是空的'}</strong>
          <span>{query ? '尝试其他歌曲名称或风格' : '生成的音乐会连同封面出现在这里'}</span>
        </div>
      )}

      {runningItems.length > 0 && (
        <section className="portfolio-section">
          <div className="portfolio-section-heading"><h3>正在生成</h3><span>{runningItems.length}</span></div>
          <div className="generating-list">
            {runningItems.map((item) => (
              <button type="button" key={item.project_id} onClick={() => onOpenProject(item)}>
                <span className="generating-icon"><Disc3 /></span>
                <span className="generating-copy"><strong>{item.title}</strong><small>{item.current_stage}</small></span>
                <span className="generating-percent">{item.progress}%</span>
                <i><span style={{ width: `${item.progress}%` }} /></i>
              </button>
            ))}
          </div>
        </section>
      )}

      {filteredTracks.length > 0 && (
        <section className="portfolio-section library-section">
          <div className="portfolio-section-heading"><h3>全部曲目</h3><span>{filteredTracks.length}</span></div>
          <div className="track-grid">
            {filteredTracks.map((item) => (
              <article className="library-track" key={item.key}>
                <div className="library-cover-wrap">
                  <Cover track={item.track} className="library-cover" />
                  <button type="button" title={playingKey === item.key ? '暂停' : '播放'} onClick={() => toggleTrack(item)}>
                    {playingKey === item.key ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
                  </button>
                </div>
                <div className="library-track-copy">
                  <strong>{item.track.title}</strong>
                  <span>{item.track.style || item.project.preset}</span>
                </div>
                <div className="library-track-meta">
                  <span>{durationLabel(item.track.duration_seconds)}</span>
                  <button type="button" title="打开项目" onClick={() => onOpenProject(item.project)}><ArrowUpRight size={15} /></button>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {playing && (
        <div className="portfolio-player">
          <Cover track={playing.track} className="player-cover" />
          <div><strong>{playing.track.title}</strong><span>{playing.track.style || playing.project.title}</span></div>
          <audio
            ref={audioRef}
            controls
            src={mediaUrl(playing.track.audio_url)}
            onEnded={() => setPlayingKey(null)}
          />
          <a href={mediaUrl(playing.track.download_url)} download title="下载歌曲"><Download size={17} /></a>
        </div>
      )}
    </section>
  )
}
