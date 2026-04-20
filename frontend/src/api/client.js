import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: BASE_URL })

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle 401 → redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// AUTH
export const login = (email, password) =>
  api.post('/auth/login', { email, password }).then(r => r.data)

export const changePassword = (new_password, confirm_password) =>
  api.post('/auth/change-password', { new_password, confirm_password }).then(r => r.data)

export const forgotPassword = (email) =>
  api.post('/auth/forgot-password', { email }).then(r => r.data)

// ME
export const getMe = () => api.get('/me').then(r => r.data)
export const updateMe = (data) => api.patch('/me', data).then(r => r.data)
export const addCapital = (amount, type) =>
  api.post('/me/capital', { amount, type }).then(r => r.data)
export const getCapitalLog = () => api.get('/me/capital-log').then(r => r.data)

// WATCHLIST
export const getWatchlist = () => api.get('/me/watchlist').then(r => r.data)
export const addToWatchlist = (stock_id) =>
  api.post('/me/watchlist', { stock_id }).then(r => r.data)
export const updateWatchlistItem = (stock_id, data) =>
  api.patch(`/me/watchlist/${stock_id}`, data).then(r => r.data)
export const searchStocks = (q) =>
  api.get(`/stocks/search?q=${q}`).then(r => r.data)

// SIGNALS
export const getSignalsToday = () => api.get('/me/signals/today').then(r => r.data)
export const getSignalHistory = () => api.get('/me/signals/history').then(r => r.data)
export const submitConfirmations = (session_token, confirmations) =>
  api.post('/me/signals/confirm', { session_token, confirmations }).then(r => r.data)

// POSITIONS
export const getPositions = () => api.get('/me/positions').then(r => r.data)
export const addManualBuy = (data) =>
  api.post('/me/positions/manual', data).then(r => r.data)
export const addManualSell = (data) =>
  api.post('/me/positions/manual-sell', data).then(r => r.data)

// BACKTEST
export const runBacktest = (data) =>
  api.post('/backtest', data).then(r => r.data)
export const getBacktestResult = (id) =>
  api.get(`/backtest/${id}`).then(r => r.data)

// DATA FEED
export const getDataStatus = () => api.get('/data/status').then(r => r.data)
export const triggerRefetch = (source) =>
  api.post('/data/refetch', { source }).then(r => r.data)

// CONFIRM via token (no-auth route)
export const getSessionByToken = (token) =>
  axios.get(`${BASE_URL}/confirm/${token}`).then(r => r.data)
export const submitByToken = (token, confirmations) =>
  axios.post(`${BASE_URL}/confirm/${token}/submit`, { confirmations }).then(r => r.data)

// ADMIN
export const getAdminUsers = () => api.get('/admin/users').then(r => r.data)
export const getAdminUser = (id) => api.get(`/admin/users/${id}`).then(r => r.data)
export const createUser = (data) => api.post('/admin/users', data).then(r => r.data)
export const updateAdminUser = (id, data) =>
  api.patch(`/admin/users/${id}`, data).then(r => r.data)
export const getAdminSystem = () => api.get('/admin/system').then(r => r.data)
export const getAdminNotifications = () =>
  api.get('/admin/notifications').then(r => r.data)

export default api
