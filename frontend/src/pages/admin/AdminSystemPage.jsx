import { useState, useEffect } from 'react'
import { Layout } from '../../components/Navigation'
import { PageHeader, LoadingSpinner, rupee, ErrorMsg } from '../../components/UI'
import { getDataStatus, triggerRefetch, getAdminUsers, getAdminSystem, getSystemSettings, updateSystemSettings } from '../../api/client'
import { RefreshCw, Hourglass, LineChart, AlertTriangle, CheckCircle2, Radio, KeyRound, Save } from 'lucide-react'


export default function AdminSystemPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refetching, setRefetching] = useState('')
  const [keys, setKeys] = useState({ resend_api_key: '', msg91_api_key: '', resend_from_email: '', msg91_sender_id: '' })
  const [savingKeys, setSavingKeys] = useState(false)
  const [keySuccess, setKeySuccess] = useState('')
  const [keyError, setKeyError] = useState('')

  const load = async () => {
    Promise.all([getDataStatus(), getAdminUsers(), getSystemSettings()])
      .then(([d, users, settings]) => {
        setData({ ...d, users })
        setKeys(settings)
      })
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

  const handleSaveKeys = async () => {
    setSavingKeys(true); setKeyError(''); setKeySuccess('')
    try {
      await updateSystemSettings(keys)
      setKeySuccess('API keys updated successfully')
      setTimeout(() => setKeySuccess(''), 3000)
    } catch (e) {
      setKeyError(e.response?.data?.detail || 'Failed to update keys')
    } finally {
      setSavingKeys(false)
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
            <h2 className="font-semibold text-text mb-3"><Radio className="w-5 h-5 inline-block" /> Data Feed</h2>
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
                  className={`w-full btn-outline text-sm py-2 flex items-center justify-center gap-1.5 cursor-pointer ${refetching === src ? 'opacity-50' : ''}`}>
                  {refetching === src ? <><Hourglass className="w-4 h-4 animate-spin" /> Fetching...</> : <><RefreshCw className="w-4 h-4" /> Fetch from {src.replace('_', ' ')}</>}
                </button>
              ))}
            </div>
          </div>

          {/* Pending confirmations */}
          <div className="card p-4">
            <h2 className="font-semibold text-text mb-3"><Hourglass className="w-5 h-5 inline-block" /> Pending Confirmations ({pending.length})</h2>
            {pending.length === 0 ? (
              <p className="text-muted text-sm flex items-center gap-1"><CheckCircle2 className="w-4 h-4 text-success" /> All traders have confirmed today's signals</p>
            ) : (
              <div className="space-y-2">
                {pending.map(u => (
                  <div key={u.id} className="flex justify-between text-sm py-2 border-b border-border">
                    <div>
                      <div className="font-medium">{u.full_name}</div>
                      <div className="text-xs text-muted">{u.email}</div>
                    </div>
                    {u.inactivity_days > 0 && (
                      <span className="text-xs text-danger"><AlertTriangle className="w-5 h-5 inline-block" /> Day {u.inactivity_days}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Inactivity summary */}
          <div className="card p-4">
            <h2 className="font-semibold text-text mb-3"><LineChart className="w-5 h-5 inline-block" /> Trader Status</h2>
            <div className="space-y-2 text-sm">
              {data?.users?.filter(u => u.role === 'trader').map(u => (
                <div key={u.id} className="flex justify-between py-1.5 border-b border-border">
                  <div>
                    <span className="font-medium">{u.full_name}</span>
                    {u.inactivity_days >= 5 && <span className="text-danger text-xs ml-2"><AlertTriangle className="w-5 h-5 inline-block" /> {u.inactivity_days}d</span>}
                  </div>
                  <span className={`text-xs font-medium ${u.status === 'active' ? 'text-success' : u.status === 'paused' ? 'text-warning' : 'text-danger'}`}>
                    {u.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Integrations & API Keys */}
          <div className="card p-4">
            <h2 className="font-semibold text-text mb-3 flex items-center gap-2"><KeyRound className="w-5 h-5" /> Integrations & API Keys</h2>
            {keySuccess && <div className="bg-success/10 text-success border border-success/30 px-3 py-2 rounded-lg text-sm mb-3">{keySuccess}</div>}
            <ErrorMsg msg={keyError} />
            <div className="space-y-4">
              <div>
                <label className="label text-sm">Resend API Key (Email)</label>
                <input type="password" placeholder="re_..." className="input !h-10 text-sm" value={keys.resend_api_key || ''} onChange={e => setKeys({ ...keys, resend_api_key: e.target.value })} />
              </div>
              <div>
                <label className="label text-sm">Resend From Email</label>
                <input type="text" placeholder="signals@yourdomain.com" className="input !h-10 text-sm" value={keys.resend_from_email || ''} onChange={e => setKeys({ ...keys, resend_from_email: e.target.value })} />
              </div>
              <div className="border-t border-border pt-4">
                <label className="label text-sm">MSG91 Auth Key (WhatsApp)</label>
                <input type="password" placeholder="Auth key..." className="input !h-10 text-sm" value={keys.msg91_api_key || ''} onChange={e => setKeys({ ...keys, msg91_api_key: e.target.value })} />
              </div>
              <button disabled={savingKeys} onClick={handleSaveKeys} className="btn-primary !w-auto flex items-center gap-2 mt-2">
                {savingKeys ? <Hourglass className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Save Keys
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  )
}
