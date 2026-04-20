import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Layout } from '../../components/Navigation'
import { PageHeader, StatusBadge, ErrorMsg, LoadingSpinner, rupee, PnL } from '../../components/UI'
import { getAdminUser, updateAdminUser } from '../../api/client'
import { AlertTriangle, CheckCircle2, Hourglass, XCircle } from 'lucide-react'


export default function AdminUserDetailPage() {
  const { id } = useParams()
  const [user, setUser]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [error, setError]   = useState('')
  const [success, setSuccess] = useState('')
  const [tab, setTab]       = useState('overview')

  const load = () => {
    getAdminUser(id).then(setUser).catch(console.error).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [id])

  const updateStatus = async (status) => {
    setSaving(true)
    try {
      await updateAdminUser(id, { status })
      await load()
      setSuccess(`Status updated to ${status} successfully`)
      setTimeout(() => setSuccess(''), 3000)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed')
    } finally {
      setSaving(false)
    }
  }

  const resetInactivity = async () => {
    setSaving(true)
    try {
      await updateAdminUser(id, { status: 'active', inactivity_days: 0, warned_day5: false, warned_day12: false })
      await load()
      setSuccess('Account reactivated successfully')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <Layout><div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div></Layout>

  const tabs = ['overview', 'positions', 'signals', 'capital']

  return (
    <Layout>
      <PageHeader title={user?.full_name || 'Trader'} subtitle={user?.email} showBack />

      {/* Status + quick actions */}
      <div className="px-4 py-3">
        <div className="card p-4">
          <div className="flex items-center justify-between mb-3">
            <StatusBadge status={user?.status} />
            {user?.inactivity_days > 0 ? (
              <span className="text-xs text-danger flex items-center gap-1"><AlertTriangle className="w-3.5 h-3.5" /> {user.inactivity_days} days inactive</span>
            ) : null}
          </div>
          {success && <div className="text-success text-sm mb-2">{success}</div>}
          <ErrorMsg msg={error} />
          <div className="flex flex-wrap gap-2 mt-3">
            {user?.status !== 'active' && (
              <button onClick={() => resetInactivity()} disabled={saving}
                className="btn-success !w-auto px-3 py-1.5 text-sm">
                <CheckCircle2 className="w-4 h-4 inline" /> Reactivate
              </button>
            )}
            {user?.status === 'active' && (
              <button onClick={() => updateStatus('paused')} disabled={saving}
                className="btn-outline !w-auto px-3 py-1.5 text-sm !text-warning !border-warning">
                ⏸ Pause
              </button>
            )}
            {user?.status !== 'suspended' && (
              <button onClick={() => updateStatus('suspended')} disabled={saving}
                className="btn-outline !w-auto px-3 py-1.5 text-sm !text-danger !border-danger">
                <div className="w-2 h-2 rounded-full bg-danger inline-block"/> Suspend
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="px-4 flex gap-2 overflow-x-auto pb-1 mb-2">
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors
              ${tab === t ? 'bg-brand text-white' : 'bg-white border border-border text-muted'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      <div className="px-4 space-y-3">
        {tab === 'overview' && (
          <>
            {/* Capital summary */}
            <div className="grid grid-cols-2 gap-3">
              <div className="card p-3">
                <div className="text-xs text-muted">Starting Capital</div>
                <div className="font-bold">{rupee(user?.starting_capital)}</div>
              </div>
              <div className="card p-3">
                <div className="text-xs text-muted">Available</div>
                <div className="font-bold text-brand">{rupee(user?.available_capital)}</div>
              </div>
              <div className="card p-3">
                <div className="text-xs text-muted">Risk %</div>
                <div className="font-bold">{user?.risk_percent}%</div>
              </div>
              <div className="card p-3">
                <div className="text-xs text-muted">Mobile</div>
                <div className="font-medium text-sm">{user?.mobile || '—'}</div>
              </div>
            </div>
            {/* Notifications */}
            <div className="card p-4">
              <div className="font-semibold text-sm mb-2">Notifications</div>
              <div className="text-sm space-y-1">
                <div className="flex items-center gap-1">Email: {user?.notify_email ? <><CheckCircle2 className="w-4 h-4 text-success" /> Enabled</> : <><XCircle className="w-4 h-4 text-muted" /> Disabled</>}</div>
                <div className="flex items-center gap-1">WhatsApp: {user?.notify_whatsapp ? <><CheckCircle2 className="w-4 h-4 text-success" /> Enabled</> : <><XCircle className="w-4 h-4 text-muted" /> Disabled</>}</div>
              </div>
            </div>
          </>
        )}

        {tab === 'positions' && (
          <div className="space-y-2">
            {user?.positions?.length === 0 && <p className="text-muted text-sm text-center py-8">No positions</p>}
            {user?.positions?.map(p => (
              <div key={p.id} className="card p-3">
                <div className="flex justify-between">
                  <div>
                    <div className="font-semibold text-sm">{p.stock?.ticker_nse}</div>
                    <div className="text-xs text-muted">{p.quantity} shares · Avg ₹{p.entry_price?.toFixed(2)}</div>
                  </div>
                  <PnL amount={p.pnl_amount} percent={p.pnl_percent} />
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'signals' && (
          <div className="space-y-2">
            {user?.signals?.length === 0 && <p className="text-muted text-sm text-center py-8">No signals</p>}
            {user?.signals?.slice(0, 20).map(s => (
              <div key={s.id} className="card p-3 flex justify-between text-sm">
                <div>
                  <span className={`font-semibold ${s.signal_type === 'BUY' ? 'text-success' : 'text-danger'}`}>
                    {s.signal_type}
                  </span>
                  <span className="ml-2 text-text">{s.stock?.ticker_nse}</span>
                  <div className="text-xs text-muted">{s.signal_date} · ₹{s.trigger_price?.toFixed(2)}</div>
                </div>
                <div className="text-right">
                  {s.confirmed === null ? <span className="text-amber-600 text-xs flex items-center gap-0.5"><Hourglass className="w-3.5 h-3.5" /> Pending</span> : null}
                  {s.confirmed === true ? <span className="text-success text-xs flex items-center gap-0.5"><CheckCircle2 className="w-3.5 h-3.5" /> Confirmed</span> : null}
                  {s.confirmed === false ? <span className="text-muted text-xs flex items-center gap-0.5"><XCircle className="w-3.5 h-3.5" /> Skipped</span> : null}
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'capital' && (
          <div className="space-y-2">
            {user?.capital_log?.map(entry => (
              <div key={entry.id} className="card p-3 flex justify-between text-sm">
                <div>
                  <div className="font-medium">{entry.change_type.replace('_', ' ')}</div>
                  <div className="text-xs text-muted">{new Date(entry.created_at).toLocaleDateString('en-IN')}</div>
                </div>
                <div className="text-right">
                  <div className={entry.amount >= 0 ? 'pnl-positive' : 'pnl-negative'}>
                    {entry.amount >= 0 ? '+' : ''}{rupee(entry.amount)}
                  </div>
                  <div className="text-xs text-muted">Bal: {rupee(entry.balance_after)}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}
