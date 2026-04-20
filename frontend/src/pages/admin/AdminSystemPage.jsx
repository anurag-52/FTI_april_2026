import { useState, useEffect } from 'react'
import { Layout } from '../../components/Navigation'
import { PageHeader, LoadingSpinner, rupee } from '../../components/UI'
import { getDataStatus, triggerRefetch, getAdminUsers, getAdminSystem } from '../../api/client'

export default function AdminSystemPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refetching, setRefetching] = useState(null)

  const load = () => {
    Promise.all([getDataStatus(), getAdminUsers()])
      .then(([d, users]) => setData({ ...d, users }))
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleRefetch = async (source) => {
    setRefetching(source)
    try {
      await triggerRefetch(source)
      setTimeout(() => { load(); setRefetching(null) }, 3000)
    } catch {
      setRefetching(null)
    }
  }

  const pending = data?.users?.filter(u => u.confirmation_pending) || []

  return (
    <Layout>
      <PageHeader title="System Dashboard" />

      {loading ? (
        <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div>
      ) : (
        <div className="px-4 py-4 space-y-4">
          {/* Data feed status */}
          <div className="card p-4">
            <h2 className="font-semibold text-text mb-3">📡 Data Feed</h2>
            <div className="grid grid-cols-2 gap-3 text-sm mb-4">
              <div>
                <div className="text-xs text-muted">Last Scan</div>
                <div className="font-medium">{data?.last_scan_date || '—'}</div>
              </div>
              <div>
                <div className="text-xs text-muted">Source Used</div>
                <div className="font-medium capitalize">{data?.source_used || '—'}</div>
              </div>
              <div>
                <div className="text-xs text-muted">Stocks Scanned</div>
                <div className="font-medium">{data?.stocks_scanned ?? '—'}</div>
              </div>
              <div>
                <div className="text-xs text-muted">Status</div>
                <div className={`font-medium capitalize ${data?.status === 'completed' ? 'text-success' : data?.status === 'failed' ? 'text-danger' : 'text-muted'}`}>
                  {data?.status || '—'}
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-xs text-muted font-medium mb-1">Manual Re-fetch</div>
              {['yfinance', 'nse_bhavcopy', 'bse_bhavcopy'].map(src => (
                <button key={src} onClick={() => handleRefetch(src)}
                  disabled={!!refetching}
                  className={`w-full btn-outline text-sm py-2 ${refetching === src ? 'opacity-50' : ''}`}>
                  {refetching === src ? '⏳ Fetching...' : `🔄 Fetch from ${src.replace('_', ' ')}`}
                </button>
              ))}
            </div>
          </div>

          {/* Pending confirmations */}
          <div className="card p-4">
            <h2 className="font-semibold text-text mb-3">⏳ Pending Confirmations ({pending.length})</h2>
            {pending.length === 0 ? (
              <p className="text-muted text-sm">All traders have confirmed today's signals ✅</p>
            ) : (
              <div className="space-y-2">
                {pending.map(u => (
                  <div key={u.id} className="flex justify-between text-sm py-2 border-b border-border">
                    <div>
                      <div className="font-medium">{u.full_name}</div>
                      <div className="text-xs text-muted">{u.email}</div>
                    </div>
                    {u.inactivity_days > 0 && (
                      <span className="text-xs text-danger">⚠️ Day {u.inactivity_days}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Inactivity summary */}
          <div className="card p-4">
            <h2 className="font-semibold text-text mb-3">📊 Trader Status</h2>
            <div className="space-y-2 text-sm">
              {data?.users?.filter(u => u.role === 'trader').map(u => (
                <div key={u.id} className="flex justify-between py-1.5 border-b border-border">
                  <div>
                    <span className="font-medium">{u.full_name}</span>
                    {u.inactivity_days >= 5 && <span className="text-danger text-xs ml-2">⚠️ {u.inactivity_days}d</span>}
                  </div>
                  <span className={`text-xs font-medium ${u.status === 'active' ? 'text-success' : u.status === 'paused' ? 'text-warning' : 'text-danger'}`}>
                    {u.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </Layout>
  )
}
