import { useState, useEffect } from 'react'
import { Layout } from '../components/Navigation'
import { PageHeader, ErrorMsg, LoadingSpinner, Toggle, rupee } from '../components/UI'
import { getMe, updateMe, addCapital, getCapitalLog, changePassword } from '../api/client'
import { useAuth } from '../hooks/useAuth'

export default function ProfilePage() {
  const { user, refreshUser, logout } = useAuth()
  const [loading, setLoading]  = useState(false)
  const [success, setSuccess]  = useState('')
  const [error, setError]      = useState('')
  const [capitalLog, setCapitalLog] = useState([])
  const [tab, setTab]          = useState('profile')

  // Profile fields
  const [name, setName]         = useState(user?.full_name || '')
  const [mobile, setMobile]     = useState(user?.mobile || '')
  const [risk, setRisk]         = useState(user?.risk_percent?.toString() || '1.0')
  const [notifyEmail, setNotifyEmail] = useState(user?.notify_email ?? true)
  const [notifyWA, setNotifyWA]       = useState(user?.notify_whatsapp ?? false)

  // Capital fields
  const [capitalAmount, setCapitalAmount] = useState('')
  const [capitalType, setCapitalType]     = useState('DEPOSIT')

  // Password fields
  const [newPwd, setNewPwd]       = useState('')
  const [confirmPwd, setConfirmPwd] = useState('')

  useEffect(() => {
    getCapitalLog().then(setCapitalLog).catch(console.error)
  }, [])

  const showSuccess = (msg) => { setSuccess(msg); setTimeout(() => setSuccess(''), 3000) }

  const saveProfile = async () => {
    setError(''); setLoading(true)
    try {
      await updateMe({ full_name: name, mobile, risk_percent: parseFloat(risk), notify_email: notifyEmail, notify_whatsapp: notifyWA })
      await refreshUser()
      showSuccess('Profile updated ✅')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to update')
    } finally {
      setLoading(false)
    }
  }

  const handleCapital = async () => {
    setError('')
    const amt = parseFloat(capitalAmount)
    if (!amt || amt <= 0) return setError('Enter a valid amount')
    setLoading(true)
    try {
      await addCapital(amt, capitalType)
      await refreshUser()
      setCapitalAmount('')
      const log = await getCapitalLog()
      setCapitalLog(log)
      showSuccess(`${capitalType === 'DEPOSIT' ? 'Deposit' : 'Withdrawal'} recorded ✅`)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed')
    } finally {
      setLoading(false)
    }
  }

  const handlePassword = async () => {
    setError('')
    if (!newPwd || newPwd.length < 8) return setError('Minimum 8 characters')
    if (newPwd !== confirmPwd) return setError('Passwords do not match')
    setLoading(true)
    try {
      await changePassword(newPwd, confirmPwd)
      setNewPwd(''); setConfirmPwd('')
      showSuccess('Password changed ✅')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed')
    } finally {
      setLoading(false)
    }
  }

  const tabs = ['profile', 'capital', 'password']

  return (
    <Layout>
      <PageHeader title="My Profile" subtitle={user?.email} />

      {/* Tabs */}
      <div className="px-4 py-3 flex gap-2 overflow-x-auto">
        {tabs.map(t => (
          <button key={t} onClick={() => { setTab(t); setError(''); setSuccess('') }}
            className={`flex-shrink-0 px-4 py-1.5 rounded-full text-sm font-medium transition-colors
              ${tab === t ? 'bg-brand text-white' : 'bg-white border border-border text-muted'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      <div className="px-4 space-y-4">
        {success && <div className="bg-green-50 border border-success rounded-btn px-3 py-2 text-sm text-success">{success}</div>}
        <ErrorMsg msg={error} />

        {/* Profile tab */}
        {tab === 'profile' && (
          <div className="space-y-4">
            <div>
              <label className="label">Full Name</label>
              <input className="input" value={name} onChange={e => setName(e.target.value)} />
            </div>
            <div>
              <label className="label">Email</label>
              <input className="input bg-gray-50" value={user?.email} disabled />
              <p className="text-xs text-muted mt-1">Email cannot be changed</p>
            </div>
            <div>
              <label className="label">Mobile</label>
              <input className="input" type="tel" value={mobile} onChange={e => setMobile(e.target.value)} placeholder="+91..." />
            </div>
            <div>
              <label className="label">Risk Per Trade (%)</label>
              <input className="input" type="number" step="0.5" min="0.5" max="5" value={risk} onChange={e => setRisk(e.target.value)} />
              <p className="text-xs text-muted mt-1">0.5% to 5.0% — affects position sizing</p>
            </div>
            <div className="card p-4 space-y-4">
              <h3 className="font-semibold text-text text-sm">Notifications</h3>
              <Toggle label="Email Notifications" checked={notifyEmail} onChange={setNotifyEmail} />
              <Toggle label="WhatsApp Notifications" checked={notifyWA} onChange={setNotifyWA} />
            </div>
            <button onClick={saveProfile} disabled={loading} className="btn-primary flex items-center justify-center gap-2">
              {loading ? <LoadingSpinner size="sm" /> : null} Save Changes
            </button>
            <button onClick={logout} className="btn-outline !border-danger !text-danger hover:!bg-red-50">
              🚪 Logout
            </button>
          </div>
        )}

        {/* Capital tab */}
        {tab === 'capital' && (
          <div className="space-y-4">
            <div className="card p-4">
              <div className="text-sm text-muted">Available Capital</div>
              <div className="text-2xl font-bold text-brand mt-1">{rupee(user?.available_capital)}</div>
            </div>
            <div className="flex gap-2">
              {['DEPOSIT', 'WITHDRAWAL'].map(t => (
                <button key={t} onClick={() => setCapitalType(t)}
                  className={`flex-1 py-2 rounded-btn text-sm font-medium border transition-colors
                    ${capitalType === t ? (t === 'DEPOSIT' ? 'bg-success text-white border-success' : 'bg-danger text-white border-danger') : 'bg-white border-border text-muted'}`}>
                  {t === 'DEPOSIT' ? '↑ Add Funds' : '↓ Withdraw'}
                </button>
              ))}
            </div>
            <div>
              <label className="label">Amount (₹)</label>
              <input type="number" inputMode="numeric" className="input text-xl font-bold"
                placeholder="0" value={capitalAmount} onChange={e => setCapitalAmount(e.target.value)} />
            </div>
            <button onClick={handleCapital} disabled={loading} className={capitalType === 'DEPOSIT' ? 'btn-success flex items-center justify-center gap-2' : 'btn-danger flex items-center justify-center gap-2'}>
              {loading ? <LoadingSpinner size="sm" /> : null}
              {capitalType === 'DEPOSIT' ? 'Add Capital' : 'Withdraw Capital'}
            </button>

            {/* Capital log */}
            {capitalLog.length > 0 && (
              <div>
                <h3 className="font-semibold text-text text-sm mb-2">History</h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {capitalLog.map(entry => (
                    <div key={entry.id} className="flex items-center justify-between py-2 border-b border-border text-sm">
                      <div>
                        <div className="font-medium">{entry.change_type.replace('_', ' ')}</div>
                        <div className="text-xs text-muted">{new Date(entry.created_at).toLocaleDateString('en-IN')}</div>
                      </div>
                      <div className="text-right">
                        <div className={entry.amount >= 0 ? 'pnl-positive' : 'pnl-negative'}>
                          {entry.amount >= 0 ? '+' : ''}{rupee(entry.amount)}
                        </div>
                        <div className="text-xs text-muted">Balance: {rupee(entry.balance_after)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Password tab */}
        {tab === 'password' && (
          <div className="space-y-4">
            <div>
              <label className="label">New Password</label>
              <input type="password" className="input" placeholder="Minimum 8 characters" value={newPwd} onChange={e => setNewPwd(e.target.value)} />
            </div>
            <div>
              <label className="label">Confirm New Password</label>
              <input type="password" className="input" value={confirmPwd} onChange={e => setConfirmPwd(e.target.value)} />
            </div>
            <button onClick={handlePassword} disabled={loading} className="btn-primary flex items-center justify-center gap-2">
              {loading ? <LoadingSpinner size="sm" /> : null} Change Password
            </button>
          </div>
        )}
      </div>
    </Layout>
  )
}
