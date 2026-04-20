import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getSessionByToken, submitByToken } from '../api/client'
import { CircuitBadge, GapRiskBadge, LoadingSpinner, ErrorMsg, rupee } from '../components/UI'
import { TrendingUp, TrendingDown, XCircle, CheckCircle2, AlertTriangle, ArrowUp, RefreshCw, OctagonX } from 'lucide-react'

// CRITICAL SCREEN — Confirmation page (accessible via permanent WhatsApp link)
export default function ConfirmPage() {
  const { token } = useParams()
  const [session, setSession] = useState(null)
  const [loading, setLoading]  = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError]   = useState('')
  const [confirmations, setConfirmations] = useState({})

  useEffect(() => {
    getSessionByToken(token)
      .then(data => {
        setSession(data)
        // Pre-fill: don't pre-fill — user must actively choose
        if (data.submitted) setSubmitted(true)
      })
      .catch(e => setError(e.response?.data?.detail || 'Session not found or expired'))
      .finally(() => setLoading(false))
  }, [token])

  const setConfirm = (signalId, actioned, qty, price) => {
    setConfirmations(prev => ({ ...prev, [signalId]: { actioned, qty, price } }))
  }

  const allSignals = session ? [...(session.buy_signals || []), ...(session.exit_signals || [])] : []
  const totalRows  = allSignals.length
  const actionedRows = Object.keys(confirmations).length
  const allActioned = actionedRows >= totalRows && totalRows > 0
  const remaining = totalRows - actionedRows

  const handleSubmit = async () => {
    if (!allActioned) return
    setError('')
    setSubmitting(true)
    try {
      const conf = allSignals.map(s => {
        const c = confirmations[s.id] || {}
        return {
          signal_id: s.id,
          actioned: c.actioned ?? false,
          qty: c.qty || null,
          price: c.price || null,
        }
      })
      await submitByToken(token, conf)
      setSubmitted(true)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to submit. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-bg">
      <LoadingSpinner size="lg" />
    </div>
  )

  if (error && !session) return (
    <div className="min-h-screen flex items-center justify-center px-6 text-center bg-bg">
      <div>
        <XCircle className="w-12 h-12 text-danger mx-auto mb-4" />
        <h2 className="font-bold text-text mb-2">Session Not Found</h2>
        <p className="text-muted text-sm">{error}</p>
      </div>
    </div>
  )

  if (submitted) return (
    <div className="min-h-screen flex items-center justify-center px-6 text-center bg-bg">
      <div>
        <CheckCircle2 className="w-14 h-14 text-success mx-auto mb-4" />
        <h2 className="text-xl font-bold text-text mb-2">Confirmation Submitted</h2>
        <p className="text-muted text-sm">
          Your signal confirmations for {session?.signal_date} have been recorded.
          {session?.submitted_at ? (
            <><br />Submitted at: {new Date(session.submitted_at).toLocaleTimeString('en-IN')}</>
          ) : null}
        </p>
        <p className="text-xs text-muted mt-4">You can close this page. Tomorrow's signals will arrive via WhatsApp/Email.</p>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-bg pb-28">
      {/* Header */}
      <div className="bg-white border-b border-border px-4 py-4 sticky top-0 z-10">
        <h1 className="font-bold text-text">Signal Confirmation</h1>
        <p className="text-xs text-muted">{session?.signal_date} · {session?.user_name}</p>
        {/* Progress bar */}
        <div className="mt-2">
          <div className="flex justify-between text-xs text-muted mb-1">
            <span>{actionedRows} of {totalRows} actioned</span>
            {remaining > 0 ? <span className="text-danger">{remaining} still need input</span> : null}
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand rounded-full transition-all"
              style={{ width: `${totalRows ? (actionedRows / totalRows * 100) : 0}%` }}
            />
          </div>
        </div>
      </div>

      <div className="px-4 py-4 space-y-4">
        {/* BUY SIGNALS */}
        {session?.buy_signals?.length > 0 ? (
          <div>
            <h2 className="section-header text-success">
              <TrendingUp className="w-5 h-5" /> BUY Signals ({session.buy_signals.length})
            </h2>
            <div className="space-y-4">
              {session.buy_signals.map(signal => (
                <BuySignalCard
                  key={signal.id}
                  signal={signal}
                  confirmation={confirmations[signal.id]}
                  onConfirm={setConfirm}
                />
              ))}
            </div>
          </div>
        ) : null}

        {/* EXIT SIGNALS */}
        {session?.exit_signals?.length > 0 ? (
          <div>
            <h2 className="section-header text-danger mt-4">
              <OctagonX className="w-5 h-5" /> Exit Alerts ({session.exit_signals.length})
            </h2>
            <div className="space-y-4">
              {session.exit_signals.map(signal => (
                <ExitSignalCard
                  key={signal.id}
                  signal={signal}
                  confirmation={confirmations[signal.id]}
                  onConfirm={setConfirm}
                />
              ))}
            </div>
          </div>
        ) : null}

        <ErrorMsg msg={error} />
      </div>

      {/* FIXED SUBMIT BUTTON — sticky above bottom tab bar on mobile */}
      <div className="fixed bottom-16 md:bottom-0 left-0 right-0 md:left-60 bg-white border-t border-border p-4 pb-safe z-30">
        {!allActioned ? (
          <p className="text-center text-xs text-danger mb-2 font-medium flex items-center justify-center gap-1">
            <AlertTriangle className="w-4 h-4" /> Action all {remaining} remaining signal{remaining !== 1 ? 's' : ''} to submit
          </p>
        ) : null}
        <button
          id="submit-signals-btn"
          onClick={handleSubmit}
          disabled={!allActioned || submitting}
          className={`min-h-[48px] ${allActioned ? 'btn-success flex items-center justify-center gap-2' : 'btn-primary !bg-gray-300 !text-gray-500 cursor-not-allowed flex items-center justify-center gap-2'}`}
        >
          {submitting ? <LoadingSpinner size="sm" /> : null}
          {submitting ? 'Submitting...' : allActioned ? (
            <><CheckCircle2 className="w-5 h-5" /> Submit All Confirmations</>
          ) : `Submit (${remaining} remaining)`}
        </button>
      </div>
    </div>
  )
}

function BuySignalCard({ signal, confirmation, onConfirm }) {
  const [qty, setQty] = useState(signal.suggested_qty?.toString() || '')
  const actioned = confirmation !== undefined

  const handleBuy = () => {
    onConfirm(signal.id, true, parseFloat(qty), signal.trigger_price)
  }
  const handleNoBuy = () => {
    onConfirm(signal.id, false, null, null)
  }

  return (
    <div className={`card overflow-hidden border-l-4 ${actioned ? (confirmation.actioned ? 'border-success' : 'border-gray-300') : 'border-brand'}`}>
      <div className="bg-green-50 px-4 py-3 flex items-center justify-between border-b border-green-100">
        <div>
          <div className="font-bold text-text">{signal.stock?.ticker_nse}</div>
          <div className="text-xs text-muted">{signal.stock?.company_name}</div>
        </div>
        <div className="text-right">
          <div className="font-bold text-xl text-text font-mono">₹{signal.trigger_price?.toFixed(2)}</div>
          <div className="text-xs text-muted">Trigger Price</div>
        </div>
      </div>
      <div className="px-4 py-3 space-y-2">
        <div className="grid grid-cols-3 gap-2 text-sm">
          <div><span className="text-muted text-xs">55D High</span><br /><span className="font-medium font-mono">₹{signal.ch55_high_at_signal?.toFixed(2)}</span></div>
          <div><span className="text-muted text-xs">20D Low</span><br /><span className="font-medium font-mono">₹{signal.ch20_low_at_signal?.toFixed(2)}</span></div>
          <div><span className="text-muted text-xs">ADX</span><br /><span className="font-medium font-mono">{signal.adx_at_signal?.toFixed(1)} <ArrowUp className="w-3 h-3 inline text-success" /></span></div>
          <div><span className="text-muted text-xs">Flat Days</span><br /><span className="font-medium font-mono">{signal.flat_days}d</span></div>
          <div><span className="text-muted text-xs">Suggested Qty</span><br /><span className="font-medium font-mono">{signal.suggested_qty}</span></div>
          <div><span className="text-muted text-xs">Est. Cost</span><br /><span className="font-medium font-mono">{rupee(signal.suggested_cost)}</span></div>
        </div>
        {signal.circuit_warning ? <CircuitBadge type={signal.circuit_type} /> : null}

        {/* Qty input */}
        <div>
          <label className="label text-xs">Quantity to Buy</label>
          <input
            type="number"
            inputMode="numeric"
            pattern="[0-9]*"
            className="input text-lg font-bold text-center font-mono"
            value={qty}
            onChange={e => setQty(e.target.value)}
            disabled={actioned && !confirmation.actioned}
          />
        </div>

        {/* Action buttons */}
        {!actioned ? (
          <div className="grid grid-cols-2 gap-2 pt-1">
            <button id={`buy-yes-${signal.id}`} onClick={handleBuy} className="btn-success min-h-[48px] flex items-center justify-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> I Bought It
            </button>
            <button id={`buy-no-${signal.id}`} onClick={handleNoBuy} className="btn-outline !text-danger !border-danger min-h-[48px] flex items-center justify-center gap-1.5">
              <XCircle className="w-4 h-4" /> Didn't Buy
            </button>
          </div>
        ) : (
          <div className={`flex items-center justify-center gap-2 py-2 rounded-btn text-sm font-medium ${confirmation.actioned ? 'bg-green-100 text-success' : 'bg-gray-100 text-muted'}`}>
            {confirmation.actioned ? <><CheckCircle2 className="w-4 h-4" /> Bought {confirmation.qty} shares</> : <><XCircle className="w-4 h-4" /> Did not buy</>}
          </div>
        )}
      </div>
    </div>
  )
}

function ExitSignalCard({ signal, confirmation, onConfirm }) {
  const actioned = confirmation !== undefined

  const exitLabels = {
    EXIT_REJECTION: { icon: RefreshCw, text: 'Rejection Rule' },
    EXIT_TRAILING:  { icon: OctagonX, text: 'Trailing Stop' },
    EXIT_ADX:       { icon: TrendingDown, text: 'ADX Reversal' },
  }
  const exitInfo = exitLabels[signal.signal_type] || { icon: AlertTriangle, text: signal.signal_type }
  const ExitIcon = exitInfo.icon

  return (
    <div className={`card overflow-hidden border-l-4 ${actioned ? (confirmation.actioned ? 'border-success' : 'border-gray-300') : 'border-danger'}`}>
      <div className="bg-red-50 px-4 py-3 flex items-center justify-between border-b border-red-100">
        <div>
          <div className="font-bold text-text">{signal.stock?.ticker_nse}</div>
          <div className="text-xs text-danger font-medium flex items-center gap-1">
            <ExitIcon className="w-3.5 h-3.5" /> {exitInfo.text}
          </div>
        </div>
        <div className="text-right">
          <div className="font-bold text-xl text-text font-mono">₹{signal.trigger_price?.toFixed(2)}</div>
          <div className="text-xs text-muted">Exit Price</div>
        </div>
      </div>
      <div className="px-4 py-3 space-y-2">
        {signal.gap_risk_warning ? <GapRiskBadge pct={signal.gap_down_pct} /> : null}
        {signal.circuit_warning ? <CircuitBadge type={signal.circuit_type} /> : null}

        {/* Positions to exit */}
        <div className="space-y-1.5">
          <div className="text-xs text-muted font-medium">Positions to exit ({signal.open_positions?.length} lots):</div>
          {signal.open_positions?.map((p, i) => (
            <div key={i} className="flex justify-between text-sm bg-gray-50 rounded-btn px-3 py-2">
              <span>Entry {p.entry_date} · <span className="font-mono">{p.qty}</span> shares @ <span className="font-mono">₹{p.entry_price}</span></span>
            </div>
          ))}
          <div className="flex justify-between text-sm font-medium border-t border-border pt-2">
            <span>Total: <span className="font-mono">{signal.total_qty}</span> shares</span>
            <span className={signal.estimated_pnl >= 0 ? 'pnl-positive font-mono' : 'pnl-negative font-mono'}>
              {signal.estimated_pnl >= 0 ? '+' : ''}{rupee(signal.estimated_pnl)}
            </span>
          </div>
        </div>

        {/* Action buttons */}
        {!actioned ? (
          <div className="grid grid-cols-2 gap-2 pt-1">
            <button id={`exit-yes-${signal.id}`}
              onClick={() => onConfirm(signal.id, true, signal.total_qty, signal.trigger_price)}
              className="btn-danger min-h-[48px] flex items-center justify-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> I Sold It
            </button>
            <button id={`exit-no-${signal.id}`}
              onClick={() => onConfirm(signal.id, false, null, null)}
              className="btn-outline !text-gray-600 !border-gray-300 min-h-[48px] flex items-center justify-center gap-1.5">
              <XCircle className="w-4 h-4" /> Didn't Sell
            </button>
          </div>
        ) : (
          <div className={`flex items-center justify-center gap-2 py-2 rounded-btn text-sm font-medium ${confirmation.actioned ? 'bg-green-100 text-success' : 'bg-gray-100 text-muted'}`}>
            {confirmation.actioned ? <><CheckCircle2 className="w-4 h-4" /> Sold all positions</> : <><XCircle className="w-4 h-4" /> Did not sell</>}
          </div>
        )}
      </div>
    </div>
  )
}
