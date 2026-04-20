import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const traderTabs = [
  { to: '/dashboard',  icon: '🏠', label: 'Home' },
  { to: '/portfolio',  icon: '📊', label: 'Portfolio' },
  { to: '/watchlist',  icon: '🔍', label: 'Watchlist' },
  { to: '/backtest',   icon: '📈', label: 'Backtest' },
  { to: '/profile',    icon: '👤', label: 'Profile' },
]

const adminTabs = [
  { to: '/admin/users',   icon: '👥', label: 'Users' },
  { to: '/admin/system',  icon: '⚙️', label: 'System' },
  { to: '/admin/profile', icon: '👤', label: 'Profile' },
]

// Bottom tab bar — mobile only
export function BottomTabBar() {
  const { user } = useAuth()
  const tabs = user?.role === 'admin' ? adminTabs : traderTabs
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-border z-50 pb-safe md:hidden">
      <div className="flex items-stretch">
        {tabs.map(tab => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center py-2 text-xs font-medium transition-colors gap-1 min-h-[56px]
               ${isActive ? 'text-brand' : 'text-muted'}`
            }
          >
            <span className="text-lg leading-none">{tab.icon}</span>
            <span>{tab.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}

// Left sidebar — desktop only
export function Sidebar() {
  const { user, logout } = useAuth()
  const tabs = user?.role === 'admin' ? adminTabs : traderTabs
  return (
    <aside className="hidden md:flex flex-col w-60 min-h-screen bg-white border-r border-border fixed top-0 left-0 z-40">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="text-2xl">📊</span>
          <div>
            <div className="font-bold text-text text-sm leading-tight">Channel Breakout</div>
            <div className="text-muted text-xs">Courtney Smith</div>
          </div>
        </div>
      </div>
      {/* Nav items */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {tabs.map(tab => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-btn text-sm font-medium transition-colors
               ${isActive ? 'bg-brand text-white' : 'text-muted hover:bg-gray-50 hover:text-text'}`
            }
          >
            <span className="w-5 text-center">{tab.icon}</span>
            {tab.label}
          </NavLink>
        ))}
      </nav>
      {/* User + Logout */}
      <div className="px-3 py-4 border-t border-border">
        <div className="px-3 py-2 mb-2">
          <div className="text-sm font-medium text-text truncate">{user?.full_name}</div>
          <div className="text-xs text-muted truncate">{user?.email}</div>
        </div>
        <button onClick={logout} className="btn-ghost w-full text-left flex items-center gap-2">
          <span>🚪</span> Logout
        </button>
      </div>
    </aside>
  )
}

// Layout wrapper combining sidebar + bottom tab bar
export function Layout({ children, title }) {
  return (
    <div className="min-h-screen bg-bg">
      <Sidebar />
      <main className="md:ml-60 pb-20 md:pb-0">
        {children}
      </main>
      <BottomTabBar />
    </div>
  )
}
