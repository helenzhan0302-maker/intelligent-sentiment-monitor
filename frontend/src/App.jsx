import { useState, useCallback, useRef, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

// ── Helpers ───────────────────────────────────────────────────
function downloadMarkdown(report) {
  const title = (report.title || '深度报告').replace(/[\\/:*?"<>|]/g, '_').slice(0, 60)
  const blob = new Blob([report.content_md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${title}.md`
  a.click()
  URL.revokeObjectURL(url)
}

// ── ReportCard ─────────────────────────────────────────────────
function ReportCard({ report }) {
  const [expanded, setExpanded] = useState(false)

  const renderMarkdown = (md) => {
    let html = md
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/^### (.+)$/gm, '<h4 class="text-slate-200 font-medium mt-4 mb-2">$1</h4>')
      .replace(/^## (.+)$/gm, '<h3 class="text-violet-300 font-semibold mt-6 mb-3 text-lg">$1</h3>')
      .replace(/^# (.+)$/gm, '<h3 class="text-violet-300 font-semibold mt-6 mb-3 text-lg">$1</h3>')
      .replace(/\*\*(.+?)\*\*/g, '<strong class="text-slate-200">$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/^- (.+)$/gm, '<li class="ml-4 text-slate-400">• $1</li>')
      .replace(/\|(.+)\|/g, (match) => {
        const cells = match.split('|').filter(c => c.trim())
        if (cells.every(c => /^[-:\s]+$/.test(c))) return ''
        return '<tr>' + cells.map(c => `<td class="border border-slate-700 px-2 py-1 text-sm text-slate-400">${c.trim()}</td>`).join('') + '</tr>'
      })
      .replace(/\n\n/g, '<br/><br/>')
    return html
  }

  return (
    <div className="rounded-xl border border-violet-700/50 bg-violet-900/10 overflow-hidden">
      <button onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-violet-900/20 transition-colors text-left">
        <span className="text-lg">{expanded ? '📖' : '📕'}</span>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-violet-300 truncate">{report.title}</h4>
          {!expanded && <p className="text-xs text-slate-500 mt-0.5">{report.word_count} 字 · 点击展开阅读</p>}
        </div>
        <span className="text-slate-600 text-sm">{expanded ? '▲' : '▼'}</span>
      </button>
      {expanded && (
        <div className="px-4 pb-4 border-t border-violet-700/30 pt-3">
          <div className="prose prose-sm prose-invert max-w-none text-slate-400 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(report.content_md) }} />
          <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-800">
            <p className="text-xs text-slate-600">{report.word_count} 字 · 由系统自动生成，仅供参考</p>
            <button onClick={(e) => { e.stopPropagation(); downloadMarkdown(report) }}
              className="px-3 py-1 text-xs rounded-lg bg-violet-800/50 border border-violet-600/50
                         text-violet-300 hover:bg-violet-700/50 hover:text-violet-100 transition-all">
              📥 下载 Markdown
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── AuthModal ──────────────────────────────────────────────────
function AuthModal({ onClose, onAuth }) {
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)

    try {
      const endpoint = mode === 'login' ? '/auth/login' : '/auth/register'
      const body = mode === 'login'
        ? { username, password }
        : { username, password, invite_code: inviteCode }

      const resp = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail || '请求失败')

      // Store token
      localStorage.setItem('auth_token', data.token)
      localStorage.setItem('auth_user', JSON.stringify(data.user || { username: data.username }))
      onAuth({ token: data.token, username: data.user?.username || data.username })
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 w-full max-w-sm shadow-2xl">
        <h2 className="text-lg font-semibold text-slate-200 mb-4">
          {mode === 'login' ? '🔑 登录' : '📝 注册'}
        </h2>

        {error && (
          <div className="mb-3 p-2 bg-red-900/20 border border-red-800/50 rounded-lg text-red-400 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)}
            placeholder="用户名" required minLength={2}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-200
                       placeholder-slate-500 text-sm focus:outline-none focus:border-violet-500" />
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            placeholder="密码" required minLength={6}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-200
                       placeholder-slate-500 text-sm focus:outline-none focus:border-violet-500" />
          {mode === 'register' && (
            <input type="text" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)}
              placeholder="邀请码" required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-200
                         placeholder-slate-500 text-sm focus:outline-none focus:border-violet-500" />
          )}

          <button type="submit" disabled={submitting}
            className="w-full py-2 bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white
                       rounded-lg font-medium text-sm hover:from-violet-500 hover:to-fuchsia-500
                       disabled:opacity-50 transition-all">
            {submitting ? '请稍候...' : (mode === 'login' ? '登录' : '注册')}
          </button>
        </form>

        <div className="mt-4 text-center">
          <button onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
            className="text-xs text-slate-500 hover:text-violet-400 transition-colors">
            {mode === 'login' ? '没有账号？使用邀请码注册' : '已有账号？去登录'}
          </button>
        </div>
        <button onClick={onClose}
          className="mt-3 w-full text-xs text-slate-600 hover:text-slate-400 transition-colors">
          取消
        </button>
      </div>
    </div>
  )
}

// ── HistoryPanel ───────────────────────────────────────────────
function HistoryPanel({ token, onSelect, onClose }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`${API_BASE}/history`, {
      headers: { 'Authorization': `Bearer ${token}` },
    })
      .then(r => { if (!r.ok) throw new Error('加载失败'); return r.json() })
      .then(d => setItems(d.items || []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [token])

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-80 bg-slate-800 border-l border-slate-700 shadow-2xl overflow-y-auto">
      <div className="p-4 border-b border-slate-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">📋 搜索历史</h3>
        <button onClick={onClose}
          className="text-slate-500 hover:text-slate-300 text-lg leading-none">&times;</button>
      </div>

      <div className="p-3">
        {loading && <p className="text-xs text-slate-500 text-center py-8">加载中...</p>}
        {error && <p className="text-xs text-red-400 text-center py-8">❌ {error}</p>}
        {!loading && !error && items.length === 0 && (
          <p className="text-xs text-slate-500 text-center py-8">暂无搜索历史</p>
        )}
        {items.map((item) => (
          <button key={item.id}
            onClick={() => { onSelect(item); onClose() }}
            className="w-full text-left p-3 rounded-lg mb-1 hover:bg-slate-700/50 transition-colors
                       border border-transparent hover:border-slate-600/50">
            <p className="text-xs text-slate-300 truncate">
              {item.keywords?.join('、') || '无关键词'}
            </p>
            <p className="text-xs text-slate-600 mt-0.5">
              {item.created_at ? new Date(item.created_at).toLocaleString('zh-CN') : ''}
            </p>
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Constants ──────────────────────────────────────────────────
const PHASE_LABELS = {
  idle: '',
  search_start: '🔍 正在搜索...',
  search_status: '🤖 AI 增强搜索中...',
  search_done: '📋 搜索完成，正在评分...',
  scoring_start: '📊 智能评分中...',
  complete: '✅ 分析完成',
  error: '❌ 出错了',
}

const RANK_STYLE = {
  1: 'border-l-2 border-l-amber-400 bg-gradient-to-r from-amber-950/25 to-slate-800/30',
  2: 'border-l-2 border-l-slate-300 bg-gradient-to-r from-slate-600/20 to-slate-800/30',
  3: 'border-l-2 border-l-orange-400 bg-gradient-to-r from-orange-950/20 to-slate-800/30',
  4: 'border-l-2 border-l-blue-400 bg-gradient-to-r from-blue-950/15 to-slate-800/30',
  5: 'border-l-2 border-l-purple-400 bg-gradient-to-r from-purple-950/15 to-slate-800/30',
}

// ── Main App ───────────────────────────────────────────────────
export default function App() {
  const [keywordInput, setKeywordInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [results, setResults] = useState(null)
  const [partialNews, setPartialNews] = useState([])
  const [combinedReport, setCombinedReport] = useState(null)
  const [phase, setPhase] = useState('idle')
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  const abortRef = useRef(null)

  // Auth state
  const [auth, setAuth] = useState(() => {
    const token = localStorage.getItem('auth_token')
    const user = JSON.parse(localStorage.getItem('auth_user') || 'null')
    return token && user ? { token, username: user.username } : null
  })
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [showHistory, setShowHistory] = useState(false)

  const keywords = keywordInput
    .split(/[,，、]+/)
    .map((k) => k.trim())
    .filter(Boolean)

  // ── API helper with auth ────────────────────────────────────
  const apiFetch = useCallback((url, opts = {}) => {
    const headers = { ...opts.headers }
    if (auth?.token) {
      headers['Authorization'] = `Bearer ${auth.token}`
    }
    return fetch(url, { ...opts, headers }).then(async (resp) => {
      if (resp.status === 401) {
        // Token expired → force re-login
        localStorage.removeItem('auth_token')
        localStorage.removeItem('auth_user')
        setAuth(null)
        setShowAuthModal(true)
        throw new Error('登录已过期，请重新登录')
      }
      return resp
    })
  }, [auth?.token])

  const handleLogout = () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    setAuth(null)
    setResults(null)
    setCombinedReport(null)
  }

  const handleHistorySelect = async (item) => {
    // Load history detail
    try {
      const resp = await apiFetch(`${API_BASE}/history/${item.id}`)
      if (!resp.ok) throw new Error('加载失败')
      const data = await resp.json()
      setResults(data.results)
      setCombinedReport(null)
    } catch (err) {
      setError(err.message)
    }
  }

  // ── Search ──────────────────────────────────────────────────
  const handleAnalyze = useCallback(async () => {
    if (keywords.length === 0) return

    // Require auth
    if (!auth) { setShowAuthModal(true); return }

    setLoading(true)
    setError('')
    setResults(null)
    setPartialNews([])
    setCombinedReport(null)
    setPhase('search_start')
    setProgress({ current: 0, total: keywords.length })

    // SSE with auth — pass token via query param (EventSource can't set headers)
    const tokenParam = `&token=${encodeURIComponent(auth.token)}`
    const streamUrl = `${API_BASE}/search/stream?keywords=${encodeURIComponent(keywords.join(','))}${tokenParam}`
    const eventSource = new EventSource(streamUrl)
    abortRef.current = () => eventSource.close()

    eventSource.addEventListener('search_start', () => setPhase('search_start'))
    eventSource.addEventListener('search_status', () => setPhase('search_status'))

    eventSource.addEventListener('search_done', (e) => {
      const data = JSON.parse(e.data)
      setPhase('search_done')
      setPartialNews((prev) => [...prev, ...(data.news || [])])
    })

    eventSource.addEventListener('scoring_start', (e) => {
      const data = JSON.parse(e.data)
      setPhase('scoring_start')
      setProgress({ current: 0, total: data.total || 0 })
    })

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data)
      setResults(data)
      setPhase('complete')
      setLoading(false)
      eventSource.close()
    })

    eventSource.addEventListener('error', (e) => {
      try {
        const data = JSON.parse(e.data)
        setError(data.message || '未知错误')
      } catch {
        eventSource.close()
        fallbackToPost()
      }
      setPhase('error')
    })

    eventSource.onerror = () => {
      eventSource.close()
      if (!results) fallbackToPost()
    }

    async function fallbackToPost() {
      try {
        setPhase('search_start')
        const resp = await apiFetch(`${API_BASE}/search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ keywords }),
        })
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}))
          throw new Error(err.detail || `请求失败 (${resp.status})`)
        }
        const data = await resp.json()
        setResults(data)
        setPhase('complete')
      } catch (err) {
        setError(err.message || '网络错误')
        setPhase('error')
      } finally {
        setLoading(false)
      }
    }
  }, [keywords, results, auth, apiFetch])

  const handleCancel = () => {
    abortRef.current?.()
    setLoading(false)
    setPhase('idle')
  }

  const handleCombinedReport = async () => {
    if (!results?.results || !auth) return
    const top3 = results.results.slice(0, 3)
    if (top3.length === 0) return

    setCombinedReport({ loading: true, report: null, error: null })

    try {
      const resp = await apiFetch(`${API_BASE}/reports/generate-combined`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: top3.map((it) => ({
            id: it.id, title: it.title, source: it.source, snippet: it.snippet,
          })),
        }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        throw new Error(err.detail || `请求失败 (${resp.status})`)
      }
      const report = await resp.json()
      setCombinedReport({ loading: false, report, error: null })
    } catch (err) {
      setCombinedReport({ loading: false, report: null, error: err.message })
    }
  }

  const scoreColor = (s) => {
    if (s >= 7) return 'text-green-400'
    if (s >= 5) return 'text-yellow-400'
    return 'text-slate-500'
  }

  // ── Need SSE to pass token differently ──────────────────────
  // EventSource can't set headers, so we modify the backend to accept token as query param
  // Backend SSE endpoint: check for token query param as fallback

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Auth Modal */}
      {showAuthModal && (
        <AuthModal
          onClose={() => setShowAuthModal(false)}
          onAuth={(a) => setAuth(a)}
        />
      )}

      {/* History Panel */}
      {showHistory && auth && (
        <HistoryPanel
          token={auth.token}
          onSelect={handleHistorySelect}
          onClose={() => setShowHistory(false)}
        />
      )}

      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-800/80 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">📊</span>
            <h1 className="text-xl font-bold bg-gradient-to-r from-violet-400 to-amber-400 bg-clip-text text-transparent">
              智能舆情监测
            </h1>
            <span className="text-xs text-slate-600 bg-slate-800 px-2 py-0.5 rounded">v0.4</span>
          </div>

          <div className="flex items-center gap-3">
            {auth ? (
              <>
                <span className="text-xs text-slate-400">👤 {auth.username}</span>
                <button onClick={() => setShowHistory(true)}
                  className="px-2 py-1 text-xs rounded-lg bg-slate-700/50 border border-slate-600/50
                             text-slate-400 hover:bg-slate-600/50 hover:text-slate-200 transition-all">
                  📋 历史
                </button>
                <button onClick={handleLogout}
                  className="px-2 py-1 text-xs rounded-lg bg-slate-700/50 border border-slate-600/50
                             text-slate-500 hover:bg-red-900/30 hover:text-red-400 hover:border-red-700/50 transition-all">
                  🚪 退出
                </button>
              </>
            ) : (
              <button onClick={() => setShowAuthModal(true)}
                className="px-3 py-1 text-xs rounded-lg bg-violet-900/30 border border-violet-700/50
                           text-violet-400 hover:bg-violet-800/40 hover:text-violet-300 transition-all">
                🔑 登录
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Input Area */}
        <div className="mb-6">
          <label className="block text-sm text-slate-400 mb-2">
            🔍 输入监测关键词（逗号或顿号分隔）
          </label>
          <div className="flex gap-3">
            <input type="text" value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && keywords.length > 0 && !loading) handleAnalyze() }}
              placeholder="例如：新能源汽车, AI芯片, 固态电池"
              disabled={loading}
              className="flex-1 px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl
                         text-slate-100 placeholder-slate-600 text-lg
                         focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500
                         disabled:opacity-50 transition-colors" />
            {loading ? (
              <button onClick={handleCancel}
                className="px-6 py-3 bg-red-600/80 text-white font-medium rounded-xl
                           hover:bg-red-500 transition-all duration-200 whitespace-nowrap">
                取消
              </button>
            ) : (
              <button onClick={handleAnalyze} disabled={keywords.length === 0}
                className="px-6 py-3 bg-gradient-to-r from-violet-600 to-fuchsia-600
                           text-white font-medium rounded-xl
                           hover:from-violet-500 hover:to-fuchsia-500
                           disabled:opacity-50 disabled:cursor-not-allowed
                           transition-all duration-200 shadow-lg shadow-violet-500/25 whitespace-nowrap">
                🔍 开始分析
              </button>
            )}
          </div>
          {keywords.length > 0 && (
            <p className="text-xs text-slate-500 mt-2">
              监测 {keywords.length} 个关键词：{keywords.join('、')}
            </p>
          )}
        </div>

        {/* Progress Bar */}
        {loading && phase !== 'idle' && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-400">{PHASE_LABELS[phase] || phase}</span>
              {progress.total > 0 && <span className="text-xs text-slate-500">{progress.current}/{progress.total}</span>}
            </div>
            <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all duration-500 ${
                  phase === 'complete' ? 'bg-green-500' : phase === 'error' ? 'bg-red-500' :
                  'bg-gradient-to-r from-violet-500 to-fuchsia-500 animate-pulse'
                }`}
                style={{
                  width: phase === 'complete' ? '100%' : phase === 'error' ? '100%' :
                    phase === 'scoring_start' ? '70%' : phase === 'search_done' ? '60%' :
                    phase === 'search_status' ? '30%' : '15%',
                }} />
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-900/20 border border-red-800/50 rounded-xl text-red-400 text-sm">
            ❌ {error}
            <button onClick={handleAnalyze} className="ml-3 underline hover:text-red-300">重试</button>
          </div>
        )}

        {/* Streaming partial results */}
        {loading && partialNews.length > 0 && (
          <div className="mb-6">
            <p className="text-xs text-slate-500 mb-3">📋 已获取 {partialNews.length} 条相关新闻，评分中...</p>
            <div className="space-y-2 opacity-60">
              {partialNews.slice(0, 8).map((item, i) => (
                <div key={item.id || i} className="p-3 rounded-lg border border-slate-700/30 bg-slate-800/20">
                  <p className="text-sm text-slate-400 truncate">{item.title}</p>
                  <p className="text-xs text-slate-600 mt-1">{item.source}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Results */}
        {results && (
          <>
            <div className="mb-6 flex items-center gap-4 text-sm flex-wrap">
              <span className="px-3 py-1 rounded-lg bg-violet-900/30 border border-violet-700/50 text-violet-300">
                关键词：{results.keywords.join('、')}
              </span>
              <span className="text-slate-400">共 {results.total} 条</span>
              <span className="text-xs text-green-400">⚡ SSE 实时推送</span>

              {results.results.length >= 3 && !combinedReport?.report && (
                <button onClick={handleCombinedReport} disabled={combinedReport?.loading}
                  className="ml-auto px-4 py-1.5 text-sm rounded-lg
                             bg-gradient-to-r from-violet-600/80 to-fuchsia-600/80
                             text-white font-medium
                             hover:from-violet-500 hover:to-fuchsia-500
                             disabled:opacity-50 disabled:cursor-not-allowed
                             transition-all shadow-md shadow-violet-500/20">
                  {combinedReport?.loading ? '📝 正在生成综合报告...' : '📝 生成 Top 3 综合深度报告'}
                </button>
              )}
            </div>

            {combinedReport?.loading && (
              <div className="mb-6 p-4 rounded-xl border border-dashed border-violet-700/50 bg-violet-900/10">
                <div className="flex items-center gap-3">
                  <span className="inline-block w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
                  <span className="text-sm text-violet-400">正在生成 Top 3 综合深度分析报告，请稍候...</span>
                </div>
              </div>
            )}

            {combinedReport?.error && (
              <div className="mb-6 p-4 bg-red-900/20 border border-red-800/50 rounded-xl text-red-400 text-sm">
                ❌ {combinedReport.error}
                <button onClick={handleCombinedReport} className="ml-3 underline hover:text-red-300">重试</button>
              </div>
            )}

            {combinedReport?.report && (
              <div className="mb-8">
                <h2 className="text-lg font-semibold text-violet-400 mb-4 flex items-center gap-2">
                  <span>📝</span> Top 3 综合深度分析报告
                </h2>
                <ReportCard report={combinedReport.report} />
              </div>
            )}

            {results.total === 0 ? (
              <div className="text-center py-16">
                <span className="text-4xl">📭</span>
                <p className="text-slate-400 mt-3">未找到相关新闻</p>
              </div>
            ) : (
              <div className="space-y-3">
                {results.results.map((item) => {
                  const accent = RANK_STYLE[item.rank] || ''
                  return (
                    <a key={item.id} href={item.url} target="_blank" rel="noopener noreferrer"
                      className={`block p-4 rounded-xl border border-slate-700/50
                                 hover:border-slate-600/50 transition-all group ${accent}`}>
                      <div className="flex items-start gap-3">
                        <span className={`
                          shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold
                          ${item.rank === 1 ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                            item.rank === 2 ? 'bg-slate-300/20 text-slate-300 border border-slate-400/30' :
                            item.rank === 3 ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                            item.rank === 4 ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' :
                            item.rank === 5 ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' :
                            'bg-slate-700/50 text-slate-500'}
                        `}>
                          {item.rank}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2 mb-1">
                            <h3 className="text-slate-200 font-medium group-hover:text-violet-300 transition-colors leading-snug">
                              {item.title}
                            </h3>
                            <span className={`shrink-0 text-sm font-mono font-bold ${scoreColor(item.total_score)}`}>
                              {item.total_score}
                            </span>
                          </div>
                          <p className="text-xs text-slate-500 mb-2">
                            📰 {item.source}
                            {item.published_at && (() => {
                              try {
                                const d = new Date(item.published_at)
                                if (isNaN(d.getTime())) return null
                                return <span className="ml-2">· {d.toLocaleDateString('zh-CN')}</span>
                              } catch { return null }
                            })()}
                          </p>
                          {item.snippet && <p className="text-sm text-slate-400 mb-2 line-clamp-2">{item.snippet}</p>}
                          <div className="flex flex-wrap gap-2 text-xs">
                            {Object.entries(item.scores).map(([key, val]) => {
                              const icons = { '权威性': '🏛', '时效性': '⏱', '重要性': '📌', '影响度': '💥', '相关性': '🎯' }
                              return (
                                <span key={key} className={`px-1.5 py-0.5 rounded ${scoreColor(val)} bg-slate-900/50`} title={key}>
                                  {icons[key] || ''} {key} {val}
                                </span>
                              )
                            })}
                          </div>
                        </div>
                      </div>
                    </a>
                  )
                })}
              </div>
            )}
          </>
        )}

        {/* Idle */}
        {!loading && !results && !error && (
          <div className="text-center py-20">
            <div className="text-6xl mb-4">🚀</div>
            <h2 className="text-xl font-semibold text-slate-400 mb-2">智能舆情监测</h2>
            <p className="text-slate-500 max-w-md mx-auto">
              {auth
                ? '输入你关注的任意关键词，系统将自动搜索最新资讯并智能评分排序'
                : '请先登录，然后输入关键词开始智能舆情分析'}
            </p>
          </div>
        )}
      </main>

      <footer className="border-t border-slate-800 py-4 text-center text-xs text-slate-600">
        智能舆情监测平台 v0.4.0 · JWT 认证 + 搜索历史 · 结果仅供参考
      </footer>
    </div>
  )
}
