import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Layout } from '../components/Navigation'
import { StatCard, rupee, PnL, LoadingSpinner, GapRiskBadge } from '../components/UI'
import { getMe, getSignalsToday, getPositions, getDataStatus, triggerRefetch } from '../api/client'
import { useAuth } from '../hooks/useAuth'

export default function DashboardPage() {
  const { user } = useAuth()
  const [signals, setSignals]   = useState(null)
  const [positions, setPositions] = useState(null)
  const [dataStatus, setDataStatus] = useState(null)
  const [loading, setLoading]   = useState(true)
  const [refetching, setRefetching] = useState(false)

  useEffect(() => {
    Promise.all([getSignalsToday(), getPositions(), getDataStatus()])
      .then(([s, p, d]) => { setSignals(s); setPositions(p); setDataStatus(d) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const today = new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })

  const handleRefetch = async () => {
    setRefetching(true)
    try {
      await triggerRefetch()
      const d = await getDataStatus()
      setDataStatus(d)
    } finally {
      setRefetching(false)
    }
  }

  if (loading) return (
    <Layout>
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    </Layout>
  )

  const summary = positions?.summary || {}
  const buySignals  = signals?.buy_signals || []
  const exitSignals = signals?.exit_signals || []
  const unconfirmed = signals && !signals.submitted && signals.total_rows > 0
  const openPositions = positions?.open || []

  return (
    <Layout>
      {/* Holiday banner */}
      {dataStatus?.status === 'skipped_holiday' && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-3 flex items-center gap-2">
          <span>🏖️</span>
          <span className="text-sm text-amber-800 font-medium">Market holiday today — no signals generated</span>
        </div>
      )}

      <div className="px-4 pt-5 pb-2">
        <h1 className="text-xl font-bold text-text">Good morning, {user?.full_name?.split(' ')[0]} 👋</h1>
        <p className="text-muted text-sm">{today}</p>
      </div>

      {/* Capital summary cards */}
      <div className="px-4 py-2 grid grid-cols-2 gap-3">
        <StatCard label="Available Capital" value={rupee(summary.available_capital)} color="blue" />
        <StatCard label="Invested" value={rupee(summary.total_invested)} color="amber" />
        <StatCard label="Total P&L"
          value={<PnL amount={summary.total_pnl} percent={summary.total_pnl_percent} />}
          color={summary.total_pnl >= 0 ? 'green' : 'red'}
        />
        <StatCard label="Open Positions" value={`${openPositions.length} / ${summary.slots_used || 0}`} color="blue" />
      </div>

      {/* Signal action card */}
      {unconfirmed && (
        <div className="px-4 py-2">
          <Link to={`/confirm/${signals.session_token}`}>
            <div className="card p-4 border-l-4 border-brand bg-blue-50">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-bold text-brand">📬 New Signals Received</div>
                  <div className="text-sm text-muted mt-0.5">
                    {buySignals.length} BUY + {exitSignals.length} EXIT alerts — tap to confirm
                  </div>
                  <div className="text-xs text-muted mt-1">
                    {signals.actioned_rows} of {signals.total_rows} actioned
                  </div>
                </div>
                <span className="text-2xl">→</span>
              </div>
            </div>
          </Link>
        </div>
      )}

      {/* BUY SIGNALS card */}
      <div className="px-4 py-2">
        <div className="card overflow-hidden">
          <div className="bg-success px-4 py-3 flex items-center justify-between">
            <span className="font-semibold text-white">📈 BUY Signals Today</span>
            <span className="bg-white text-success text-sm font-bold rounded-full w-7 h-7 flex items-center justify-center">
              {buySignals.length}
            </span>
          </div>
          {buySignals.length === 0 ? (
            <div className="px-4 py-4 text-sm text-muted text-center">No buy signals today</div>
          ) : (
            <div className="divide-y divide-border">
              {buySignals.slice(0, 3).map(s => (
                <div key={s.id} className="px-4 py-3 flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-text text-sm">{s.stock?.ticker_nse}</div>
                    <div className="text-xs text-muted">{s.stock?.company_name}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-text">₹{s.trigger_price?.toFixed(2)}</div>
                    <div className="text-xs text-muted">Qty: {s.suggested_qty}</div>
                  </div>
                </div>
              ))}
              {buySignals.length > 3 && (
                <div className="px-4 py-2 text-center text-xs text-brand font-medium">
                  +{buySignals.length - 3} more →
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* EXIT ALERTS card */}
      <div className="px-4 py-2">
        <div className="card overflow-hidden">
          <div className="bg-danger px-4 py-3 flex items-center justify-between">
            <span className="font-semibold text-white">🚨 Exit Alerts Today</span>
            <span className="bg-white text-danger text-sm font-bold rounded-full w-7 h-7 flex items-center justify-center">
              {exitSignals.length}
            </span>
          </div>
          {exitSignals.length === 0 ? (
            <div className="px-4 py-4 text-sm text-muted text-center">No exit alerts today</div>
          ) : (
            <div className="divide-y divide-border">
              {exitSignals.slice(0, 3).map(s => (
                <div key={s.id} className="px-4 py-3 flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-text text-sm">{s.stock?.ticker_nse}</div>
                    <div className="text-xs text-muted">{s.signal_type?.replace('EXIT_', '').replace('_', ' ')}</div>
                    {s.gap_risk_warning && <GapRiskBadge pct={s.gap_down_pct} />}
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-text">₹{s.trigger_price?.toFixed(2)}</div>
                    <PnL amount={s.estimated_pnl} percent={s.estimated_pnl / (s.entry_value || 1) * 100} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Open positions preview */}
      {openPositions.length > 0 && (
        <div className="px-4 py-2">
          <div className="flex items-center justify-between mb-2">
            <span className="section-header">Open Positions</span>
            <Link to="/portfolio" className="text-brand text-xs font-medium">View all →</Link>
          </div>
          <div className="space-y-2">
            {openPositions.slice(0, 2).map(p => (
              <div key={p.id} className="card px-4 py-3 flex items-center justify-between">
                <div>
                  <div className="font-semibold text-sm text-text">{p.stock?.ticker_nse}</div>
                  <div className="text-xs text-muted">Qty: {p.quantity} · Avg: ₹{p.entry_price?.toFixed(2)}</div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-sm">{rupee(p.current_value)}</div>
                  <PnL amount={p.pnl_amount} percent={p.pnl_percent} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data feed status */}
      <div className="px-4 py-3 mb-2">
        <div className="card px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs font-medium text-muted">Data Feed</div>
              <div className="text-sm font-medium text-text capitalize">
                {dataStatus?.status || 'Unknown'} · {dataStatus?.source_used || '—'}
              </div>
              <div className="text-xs text-muted">{dataStatus?.stocks_scanned || 0} stocks scanned</div>
            </div>
            <button
              onClick={handleRefetch}
              disabled={refetching}
              className="btn-outline !w-auto px-3 py-2 text-xs"
            >
              {refetching ? '⏳' : '🔄'} Re-fetch
            </button>
          </div>
        </div>
      </div>
    </Layout>
  )
}
