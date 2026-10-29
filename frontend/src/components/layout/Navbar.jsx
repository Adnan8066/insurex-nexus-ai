import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Bell,
  Brain,
  Briefcase,
  ChevronDown,
  Cpu,
  FileText,
  Headphones,
  LayoutDashboard,
  LogOut,
  Moon,
  Settings,
  Sun,
  User,
  Users,
} from 'lucide-react'
import { useAuth } from '../../context/useAuth'
import { notificationService } from '../../services'
import { formatRelativeTime } from '../../utils/helpers'

const ALL_ROLES = ['customer', 'employee', 'investigator', 'admin']
const STAFF_ROLES = ['employee', 'investigator', 'admin']
const POLICY_ROLES = ['customer', 'employee', 'admin']

// A few top-level areas, ordered by everyday workflow. Related pages share a dropdown;
// a group with a single visible page renders as a plain link. Items that would duplicate
// a role's own dashboard are left out (the admin dashboard is Analytics; the investigator
// dashboard is the investigation cases page). Routing advice stays reachable by URL but
// is not listed until its model passes the evaluation gate.
const navItems = [
  { label: 'Dashboard', to: '/dashboard', Icon: LayoutDashboard, roles: ALL_ROLES },
  { label: 'Claims', to: '/claims', Icon: Briefcase, roles: ALL_ROLES },
  {
    label: 'Policies',
    Icon: FileText,
    children: [
      { label: 'Policies', to: '/policies', hint: 'Cover, premiums and endorsements', roles: POLICY_ROLES },
      { label: 'Vehicles', to: '/vehicles', hint: 'Insured vehicles and their documents', roles: POLICY_ROLES },
      { label: 'Policy requests', to: '/policies/requests', hint: 'Customer requests waiting to be issued', roles: ['employee', 'admin'] },
    ],
  },
  {
    label: 'Fraud',
    Icon: AlertTriangle,
    children: [
      { label: 'Fraud alerts', to: '/fraud', hint: 'Claims the fraud model flagged for review', roles: STAFF_ROLES },
      { label: 'Investigation cases', to: '/investigators', hint: 'Cases being worked by investigators', roles: ['employee', 'admin'] },
    ],
  },
  {
    label: 'AI Tools',
    Icon: Brain,
    children: [
      { label: 'Claim assessment', to: '/ai-assessment', hint: 'Repair cost, fraud and total-loss estimates', roles: STAFF_ROLES },
      { label: 'Automated review', to: '/ai-decision', hint: 'Step-by-step checks before a human decides', roles: STAFF_ROLES },
    ],
  },
  { label: 'Analytics', to: '/analytics', Icon: BarChart3, roles: ['employee', 'investigator'] },
  { label: 'Help & Support', to: '/support', Icon: Headphones, roles: ['customer'] },
]

// Housekeeping pages live in the user menu rather than the main navigation.
const accountItems = [
  { label: 'User management', to: '/admin/users', Icon: Users, roles: ['admin'] },
  { label: 'Model health', to: '/operations', Icon: Cpu, roles: STAFF_ROLES },
]

function visibleNavItems(role) {
  return navItems
    .map((item) => (item.children
      ? { ...item, children: item.children.filter((child) => child.roles.includes(role)) }
      : item))
    .filter((item) => (item.children ? item.children.length > 0 : item.roles.includes(role)))
    .map((item) => (item.children?.length === 1 ? { ...item.children[0], Icon: item.Icon } : item))
}

function pathMatches(pathname, to) {
  return pathname === to || (to !== '/dashboard' && pathname.startsWith(`${to}/`))
}

export function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [notificationError, setNotificationError] = useState('')
  const [darkMode, setDarkMode] = useState(() => {
    const savedTheme = window.localStorage.getItem('theme')
    return savedTheme ? savedTheme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches
  })
  const [openGroup, setOpenGroup] = useState(null)
  const moduleNavRef = useRef(null)
  const moduleLinkRefs = useRef([])
  const userMenuRef = useRef(null)
  const notificationsRef = useRef(null)
  const visibleModules = visibleNavItems(user?.role)
  const visibleAccountItems = accountItems.filter((item) => item.roles.includes(user?.role))
  const showModuleNavigation = Boolean(user)
  const isDashboardPage = location.pathname === '/dashboard'
  const roleLabels = { customer: 'Customer', employee: 'Employee', investigator: 'Investigator', admin: 'Admin' }
  const dashboardFirstName = user?.first_name || user?.firstName || user?.name?.trim().split(/\s+/)[0] || user?.email?.split('@')[0] || 'there'
  // Every reachable page with the top-level nav item it belongs to (-1 for user-menu pages).
  const pageLinks = [
    ...visibleModules.flatMap((item, index) => (item.children || [item]).map((link) => ({ ...link, index }))),
    ...visibleAccountItems.map((link) => ({ ...link, index: -1 })),
  ]
  const activePage = pageLinks.reduce((best, link) => (
    pathMatches(location.pathname, link.to) && (!best || link.to.length > best.to.length) ? link : best
  ), null)
  const activeModuleIndex = activePage ? activePage.index : -1
  const currentPageTitle = isDashboardPage
    ? `${roleLabels[user?.role] || 'User'} Dashboard`
    : (activePage
      ? activePage.label
      : location.pathname.split('/').filter(Boolean).at(-1)?.replace(/[-_]/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()))
  const [activeIndicator, setActiveIndicator] = useState({ left: 0, top: 0, width: 0, height: 0, ready: false })

  useEffect(() => {
    setOpenGroup(null)
  }, [location.pathname])

  useLayoutEffect(() => {
    const nav = moduleNavRef.current
    const activeLink = moduleLinkRefs.current[activeModuleIndex]
    if (!nav) {
      setActiveIndicator((current) => ({ ...current, ready: false }))
      return undefined
    }

    const updateLayout = () => {
      if (activeLink) {
        setActiveIndicator({
          left: activeLink.offsetLeft,
          top: activeLink.offsetTop,
          width: activeLink.offsetWidth,
          height: activeLink.offsetHeight,
          ready: true,
        })
      } else {
        setActiveIndicator((current) => ({ ...current, ready: false }))
      }
    }

    updateLayout()
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(updateLayout)
    observer?.observe(nav)
    moduleLinkRefs.current.forEach((link) => link && observer?.observe(link))
    window.addEventListener('resize', updateLayout)
    return () => {
      observer?.disconnect()
      window.removeEventListener('resize', updateLayout)
    }
  }, [activeModuleIndex, visibleModules.length])

  useEffect(() => {
    if (!user?.id) return undefined
    let cancelled = false
    const loadNotifications = async () => {
      try {
        const [listResult, countResult] = await Promise.all([
          notificationService.getNotifications({ page_size: 5 }),
          notificationService.getUnreadCount(),
        ])
        if (cancelled) return
        const rows = Array.isArray(listResult) ? listResult : (listResult.results || [])
        setNotifications(rows.slice(0, 5))
        setUnreadCount(Number(countResult.unread_count) || 0)
        setNotificationError('')
      } catch {
        if (!cancelled) setNotificationError('Could not load notifications.')
      }
    }
    loadNotifications()
    const interval = window.setInterval(loadNotifications, 30000)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [user?.id])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
    window.localStorage.setItem('theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) setShowUserMenu(false)
      if (notificationsRef.current && !notificationsRef.current.contains(event.target)) setShowNotifications(false)
      if (moduleNavRef.current && !moduleNavRef.current.contains(event.target)) setOpenGroup(null)
    }
    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setShowUserMenu(false)
        setShowNotifications(false)
        setOpenGroup(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [])

  const handleLogout = async () => {
    await logout()
    setShowUserMenu(false)
    navigate('/', { replace: true })
  }

  const markAllNotificationsRead = async () => {
    try {
      await notificationService.markAllRead()
      setNotifications((current) => current.map((notification) => ({ ...notification, is_read: true })))
      setUnreadCount(0)
    } catch {
      setNotificationError('Could not mark notifications as read.')
    }
  }

  const markNotificationRead = async (notification) => {
    if (notification.is_read) return
    try {
      await notificationService.markRead(notification.id)
      setNotifications((current) => current.map((item) => item.id === notification.id ? { ...item, is_read: true } : item))
      setUnreadCount((count) => Math.max(0, count - 1))
    } catch {
      setNotificationError('Could not update this notification.')
    }
  }

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/95 shadow-sm shadow-slate-900/[0.03] backdrop-blur" role="banner">
      <div className="mx-auto flex min-h-16 max-w-[1600px] items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
        {/* Brand and page title share one row; on phones the title drops beneath the brand. */}
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1 py-2">
          <Link to="/dashboard" className="flex shrink-0 items-center gap-2.5" aria-label="InsureX dashboard">
            <img src="/insurex-nexus-ai-logo.jpg" alt="InsureX Nexus AI logo" className="h-9 w-9 shrink-0 rounded-xl object-cover shadow-sm shadow-blue-600/20" />
            <span className="text-base font-extrabold tracking-tight text-slate-950 sm:text-lg">InsureX <span className="text-blue-600">Nexus AI</span></span>
          </Link>
          {user && currentPageTitle && (
            <>
              <span aria-hidden="true" className="hidden h-7 w-px bg-slate-200 sm:block" />
              <div className="min-w-0 basis-full sm:basis-auto">
                <h1 className="text-base font-bold leading-tight tracking-tight text-slate-900 sm:text-lg">{currentPageTitle}</h1>
                {user.role === 'customer' && isDashboardPage && (
                  <p className="text-xs leading-5 text-slate-500 sm:text-sm">Welcome back, {dashboardFirstName}! Here&apos;s an overview of your insurance portfolio.</p>
                )}
              </div>
            </>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1 sm:gap-2">
          <button onClick={() => setDarkMode((current) => !current)} className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900" aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}>
            {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>

          <div className="relative" ref={notificationsRef}>
            <button onClick={() => setShowNotifications((current) => !current)} className={`relative rounded-full p-2 transition ${showNotifications ? 'bg-blue-50 text-blue-700' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'}`} aria-label="Notifications" aria-expanded={showNotifications} aria-haspopup="true">
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">{unreadCount > 9 ? '9+' : unreadCount}</span>}
            </button>
            {showNotifications && (
              <div className="absolute right-0 z-50 mt-3 w-[min(24rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-900/10">
                <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                  <h2 className="font-bold text-slate-900">Notifications</h2>
                  {unreadCount > 0 && <button className="text-xs font-semibold text-blue-700 hover:underline" onClick={markAllNotificationsRead}>Mark all read</button>}
                </div>
                <div className="max-h-80 overflow-y-auto">
                  {notificationError && <p className="px-4 py-3 text-sm text-rose-600">{notificationError}</p>}
                  {!notificationError && notifications.length === 0 && <p className="px-4 py-6 text-center text-sm text-slate-500">No notifications yet.</p>}
                  {notifications.map((notification) => (
                    <Link key={notification.id} to={notification.link || '/notifications'} onClick={() => { markNotificationRead(notification); setShowNotifications(false) }} className={`block border-b border-slate-100 px-4 py-3 transition last:border-0 hover:bg-slate-50 ${!notification.is_read ? 'bg-blue-50/70' : ''}`}>
                      <p className="text-sm font-semibold text-slate-900">{notification.title}</p>
                      <p className="mt-0.5 text-sm text-slate-600">{notification.message}</p>
                      <p className="mt-1 text-xs text-slate-400">{formatRelativeTime(notification.sent_at)}</p>
                    </Link>
                  ))}
                </div>
                <Link to="/notifications" className="block border-t border-slate-100 px-4 py-3 text-center text-sm font-bold text-blue-700 hover:bg-slate-50" onClick={() => setShowNotifications(false)}>View all notifications</Link>
              </div>
            )}
          </div>

          <div className="relative" ref={userMenuRef}>
            <button onClick={() => setShowUserMenu((current) => !current)} className="flex items-center gap-1 rounded-full py-1 pl-1 pr-1.5 transition hover:bg-slate-100 sm:gap-2 sm:pr-2" aria-label="User menu" aria-expanded={showUserMenu} aria-haspopup="true">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-blue-700"><User className="h-4 w-4" /></span>
              <span className="hidden max-w-32 truncate text-sm font-semibold text-slate-700 sm:block">{user?.name}</span>
              <ChevronDown className="hidden h-4 w-4 text-slate-500 sm:block" />
            </button>
            {showUserMenu && <div className="absolute right-0 z-50 mt-3 w-52 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl shadow-slate-900/10">
              <div className="border-b border-slate-100 px-3 py-2"><p className="truncate text-sm font-bold text-slate-900">{user?.name}</p><p className="text-xs capitalize text-slate-500">{user?.role}</p></div>
              <Link to="/profile" className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50" onClick={() => setShowUserMenu(false)}><User className="h-4 w-4" />Profile</Link>
              {user && <Link to="/settings" className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50" onClick={() => setShowUserMenu(false)}><Settings className="h-4 w-4" />Settings</Link>}
              {visibleAccountItems.length > 0 && <div className="my-1 border-t border-slate-100 pt-1">
                <p className="px-3 pb-1 pt-1.5 text-[11px] font-bold uppercase tracking-wide text-slate-400">Administration</p>
                {visibleAccountItems.map(({ label, to, Icon }) => (
                  <Link key={to} to={to} className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50" onClick={() => setShowUserMenu(false)}><Icon className="h-4 w-4" />{label}</Link>
                ))}
              </div>}
              <button onClick={handleLogout} className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left text-sm font-semibold text-rose-600 hover:bg-rose-50"><LogOut className="h-4 w-4" />Sign out</button>
            </div>}
          </div>
        </div>
      </div>

      <div className="border-t border-slate-100">
        <div className="mx-auto flex max-w-[1600px] items-center px-1 sm:px-4 lg:px-6">
          <button
            onClick={() => navigate(window.history.length > 1 ? -1 : '/dashboard')}
            className="mr-1 shrink-0 rounded-full p-1.5 text-slate-500 transition hover:bg-slate-100 hover:text-blue-700"
            aria-label="Go back"
            title="Go back"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          {showModuleNavigation && (
          <nav
            ref={moduleNavRef}
            className="module-nav-track flex min-w-0 flex-1 flex-wrap items-center gap-1 px-2 py-2"
            aria-label="Dashboard modules"
            style={{
              '--module-active-left': `${activeIndicator.left}px`,
              '--module-active-top': `${activeIndicator.top}px`,
              '--module-active-width': `${activeIndicator.width}px`,
              '--module-active-height': `${activeIndicator.height}px`,
            }}
          >
            <span aria-hidden="true" className={`module-nav-active-indicator${activeIndicator.ready ? ' is-ready' : ''}`} />
            {visibleModules.map((item, index) => {
              const { label, to, Icon, children } = item
              const itemClass = (active) => `module-nav-link flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-xs font-bold transition sm:px-3.5 sm:text-sm ${active ? 'is-active' : 'text-slate-600 hover:bg-white/80 hover:text-slate-950'}`
              if (!children) {
                return (
                  <NavLink
                    key={label}
                    ref={(element) => { moduleLinkRefs.current[index] = element }}
                    to={to}
                    end={to === '/dashboard'}
                    title={label}
                    className={() => itemClass(index === activeModuleIndex)}
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span>{label}</span>
                  </NavLink>
                )
              }
              const isOpen = openGroup === label
              return (
                <div key={label} ref={(element) => { moduleLinkRefs.current[index] = element }} className={`relative shrink-0 ${isOpen ? 'z-50' : 'z-[1]'}`}>
                  <button
                    type="button"
                    onClick={() => setOpenGroup(isOpen ? null : label)}
                    className={itemClass(index === activeModuleIndex)}
                    aria-haspopup="menu"
                    aria-expanded={isOpen}
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span>{label}</span>
                    <ChevronDown className={`h-3.5 w-3.5 shrink-0 transition ${isOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
                  </button>
                  {isOpen && (
                    <div role="menu" className="absolute left-0 z-50 mt-2 w-72 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl shadow-slate-900/10">
                      {children.map((child) => (
                        <NavLink
                          key={child.to}
                          to={child.to}
                          role="menuitem"
                          onClick={() => setOpenGroup(null)}
                          className={({ isActive }) => `block rounded-xl px-3 py-2.5 transition ${isActive ? 'bg-blue-50' : 'hover:bg-slate-50'}`}
                        >
                          <span className="block text-sm font-semibold text-slate-900">{child.label}</span>
                          <span className="block text-xs text-slate-500">{child.hint}</span>
                        </NavLink>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </nav>
          )}
        </div>
      </div>
    </header>
  )
}

export default Navbar
