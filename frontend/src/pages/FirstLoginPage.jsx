import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { changePassword, updateMe, addCapital } from '../api/client'
import { ErrorMsg, LoadingSpinner } from '../components/UI'

export default function FirstLoginPage() {
  const { refreshUser } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Step 1: Password
  const [newPwd, setNewPwd]     = useState('')
  const [confirmPwd, setConfirmPwd] = useState('')
  const [showPwd, setShowPwd]   = useState(false)

  // Step 2: Capital
  const [capital, setCapital]   = useState('')
  const [risk, setRisk]         = useState('1.0')

  const handleStep1 = async () => {
    setError('')
    if (!newPwd || newPwd.length < 8) return setError('Password must be at least 8 characters')
    if (newPwd !== confirmPwd) return setError('Passwords do not match')
    setLoading(true)
    try {
      await changePassword(newPwd, confirmPwd)
      setStep(2)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to change password')
    } finally {
      setLoading(false)
    }
  }

  const handleStep2 = async () => {
    setError('')
    const cap = parseFloat(capital)
    const r = parseFloat(risk)
    if (!cap || cap < 10000) return setError('Minimum starting capital is ₹10,000')
    if (!r || r < 0.5 || r > 5.0) return setError('Risk % must be between 0.5 and 5.0')
    setLoading(true)
    try {
      await addCapital(cap, 'DEPOSIT')
      await updateMe({ risk_percent: r, first_login_complete: true, capital_entered: true })
      await refreshUser()
      navigate('/dashboard')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to save settings')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center px-4">
      <div className="w-full max-w-[400px]">
        <div className="text-center mb-6">
          <h1 className="text-xl font-bold text-text">Welcome — Setup Your Account</h1>
          <p className="text-muted text-sm mt-1">Complete in 2 steps to start receiving signals</p>
        </div>

        {/* Progress dots */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {[1, 2].map(s => (
            <div key={s} className={`w-3 h-3 rounded-full transition-colors ${step >= s ? 'bg-brand' : 'bg-gray-200'}`} />
          ))}
        </div>

        <div className="card p-6">
          {step === 1 && (
            <div className="space-y-4">
              <h2 className="font-semibold text-text">Step 1 — Set New Password</h2>
              <div>
                <label className="label">New Password</label>
                <div className="relative">
                  <input
                    type={showPwd ? 'text' : 'password'}
                    className="input pr-10"
                    placeholder="Minimum 8 characters"
                    value={newPwd}
                    onChange={e => setNewPwd(e.target.value)}
                  />
                  <button type="button" onClick={() => setShowPwd(!showPwd)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted">
                    {showPwd ? '🙈' : '👁️'}
                  </button>
                </div>
              </div>
              <div>
                <label className="label">Confirm New Password</label>
                <input
                  type="password"
                  className="input"
                  placeholder="Re-enter password"
                  value={confirmPwd}
                  onChange={e => setConfirmPwd(e.target.value)}
                />
              </div>
              <ErrorMsg msg={error} />
              <button id="set-password-btn" onClick={handleStep1} disabled={loading} className="btn-primary flex items-center justify-center gap-2">
                {loading ? <LoadingSpinner size="sm" /> : null}
                Continue →
              </button>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <h2 className="font-semibold text-text">Step 2 — Set Starting Capital</h2>
              <div>
                <label className="label">Starting Capital (₹)</label>
                <input
                  type="number"
                  inputMode="numeric"
                  className="input"
                  placeholder="e.g. 200000"
                  value={capital}
                  min="10000"
                  onChange={e => setCapital(e.target.value)}
                />
                <p className="text-xs text-muted mt-1">Minimum ₹10,000</p>
              </div>
              <div>
                <label className="label">Risk Per Trade (%)</label>
                <input
                  type="number"
                  inputMode="decimal"
                  step="0.5"
                  min="0.5"
                  max="5.0"
                  className="input"
                  placeholder="1.0"
                  value={risk}
                  onChange={e => setRisk(e.target.value)}
                />
                <p className="text-xs text-muted mt-1">0.5% to 5.0% — recommended: 1%</p>
              </div>
              <ErrorMsg msg={error} />
              <button id="save-capital-btn" onClick={handleStep2} disabled={loading} className="btn-primary flex items-center justify-center gap-2">
                {loading ? <LoadingSpinner size="sm" /> : null}
                Start Trading →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
