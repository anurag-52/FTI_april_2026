import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Search, LineChart, LogOut, User, Users, TrendingUp, LayoutDashboard, Settings, BarChart3, Sun, Moon } from 'lucide-react'
import { useTheme } from '../hooks/useTheme'


const traderTabs = [
  { to: '/dashboard',  icon: LayoutDashboard, label: 'Home' },
  { to: '/portfolio',  icon: LineChart, label: 'Portfolio' },
  { to: '/watchlist',  icon: Search, label: 'Watchlist' },
  { to: '/backtest',   icon: TrendingUp, label: 'Backtest' },
  { to: '/profile',    icon: User, label: 'Profile' },
]

const adminTabs = [
  { to: '/admin/users',   icon: Users, label: 'Users' },
  { to: '/admin/system',  icon: Settings, label: 'System' },
  { to: '/admin/profile', icon: User, label: 'Profile' },
]

// Bottom tab bar — mobile only
export function BottomTabBar() {
  const { user, viewMode, setViewMode } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const tabs = viewMode === 'admin' ? adminTabs : traderTabs
  
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-border z-50 pb-safe md:hidden shadow-[0_-1px_10px_rgba(0,0,0,0.05)]">
      <div className="flex h-[64px]">
        {tabs.map(tab => {
          const active = pathname === tab.to
          return (
            <Link
              key={tab.to}
              to={tab.to}
              className={`flex-1 flex flex-col items-center justify-center text-[11px] font-medium transition-all gap-1
                         ${active ? 'text-brand' : 'text-muted hover:text-text'}`}
            >
              <tab.icon className="w-5 h-5" strokeWidth={active ? 2.5 : 1.5} />
              <span>{tab.label}</span>
            </Link>
          )
        })}
        {user?.role === 'admin' && (
          <button
            onClick={() => {
              const next = viewMode === 'admin' ? 'trader' : 'admin'
              setViewMode(next)
              navigate(next === 'admin' ? '/admin/users' : '/dashboard')
            }}
            className="flex-1 flex flex-col items-center justify-center text-[11px] font-medium text-brand/70 hover:text-brand gap-1"
          >
            <div className="w-5 h-5 flex items-center justify-center">
              <Settings className="w-4 h-4 animate-pulse" />
            </div>
            <span>Switch</span>
          </button>
        )}
      </div>
    </nav>
  )
}

// Left sidebar — desktop only
export function Sidebar() {
  const { user, logout, viewMode, setViewMode } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const tabs = viewMode === 'admin' ? adminTabs : traderTabs

  return (
    <aside className="hidden md:flex flex-col w-64 min-h-screen bg-white border-r border-border fixed top-0 left-0 z-40">
      {/* Logo */}
      <div className="px-6 py-6 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-brand/5 rounded-xl flex items-center justify-center text-brand">
            <BarChart3 className="w-6 h-6" strokeWidth={2} />
          </div>
          <div>
            <div className="font-bold text-text text-sm leading-tight">Channel Breakout</div>
            <div className="text-muted text-[11px] uppercase tracking-wider font-semibold">Courtney Smith</div>
          </div>
        </div>
      </div>
      {/* Nav items */}
      <nav className="flex-1 px-4 py-6 space-y-1.5">
        <div className="text-[10px] font-bold text-muted uppercase tracking-[0.1em] px-3 mb-2">
          {viewMode === 'admin' ? 'System Management' : 'Trading Dashboard'}
        </div>
        {tabs.map(tab => {
          const active = pathname === tab.to
          return (
            <Link
              key={tab.to}
              to={tab.to}
              className={`flex items-center gap-3 px-4 min-h-[44px] rounded-xl text-sm font-medium transition-all group
                         ${active ? 'bg-brand text-white shadow-md shadow-brand/20' : 'text-muted hover:bg-gray-50 hover:text-text'}`}
            >
              <tab.icon className={`w-5 h-5 ${active ? 'text-white' : 'text-muted group-hover:text-brand'} transition-colors`} strokeWidth={active ? 2.5 : 1.5} />
              {tab.label}
            </Link>
          )
        })}
      </nav>
      {/* User + Logout */}
      <div className="px-4 py-5 border-t border-border bg-gray-50/50">
        {user?.role === 'admin' && (
          <button 
            onClick={() => {
              const next = viewMode === 'admin' ? 'trader' : 'admin'
              setViewMode(next)
              navigate(next === 'admin' ? '/admin/users' : '/dashboard')
            }}
            className="w-full h-[40px] mb-4 bg-brand/5 hover:bg-brand/10 border border-brand/10 rounded-lg text-xs font-bold text-brand flex items-center justify-center gap-2 transition-colors"
          >
            <Settings className="w-3.5 h-3.5 animate-pulse" />
            Switch to {viewMode === 'admin' ? 'Trader' : 'Admin'} Mode
          </button>
        )}
        <div className="px-3 py-2 mb-3 flex items-center justify-between bg-white rounded-xl border border-border shadow-sm">
          <div className="overflow-hidden">
            <div className="text-sm font-bold text-text truncate">{user?.full_name}</div>
            <div className="text-[11px] text-muted truncate">{user?.email}</div>
          </div>
          <ThemeToggle />
        </div>
        <button onClick={logout} className="btn-ghost w-full justify-start gap-3 px-4 min-h-[44px] text-danger hover:bg-red-50 hover:text-danger">
          <LogOut className="w-5 h-5" /> 
          <span className="font-semibold">Logout</span>
        </button>
      </div>
    </aside>
  )
}

function ThemeToggle() {
  const { isDark, toggleTheme } = useTheme()
  return (
    <button onClick={toggleTheme} className="p-2 text-muted hover:text-text rounded-full hover:bg-gray-100 transition-colors">
      {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
    </button>
  )
}

// Layout wrapper combining sidebar + bottom tab bar
export function Layout({ children, title }) {
  return (
    <div className="min-h-screen bg-bg">
      <Sidebar />
      <main className="md:ml-64 pb-[64px] md:pb-0 page-enter">
        {children}
      </main>
      <BottomTabBar />
    </div>
  )
}
