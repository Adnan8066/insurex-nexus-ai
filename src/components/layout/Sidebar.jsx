import { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard,
  FileText,
  Car,
  Briefcase,
  Brain,
  AlertTriangle,
  Users,
  Wrench,
  Gavel,
  GitBranch,
  BarChart3,
  Bell,
  User,
  Settings,
  ChevronLeft,
  ChevronRight,
  Shield,
  Zap,
  Scale,
  Search,
  FileCheck,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, roles: ['customer', 'employee', 'investigator', 'repair', 'admin'] },
  { name: 'Policies', href: '/policies', icon: FileText, roles: ['customer', 'employee', 'admin'] },
  { name: 'Vehicles', href: '/vehicles', icon: Car, roles: ['customer', 'employee', 'admin'] },
  { name: 'Claims', href: '/claims', icon: Briefcase, roles: ['customer', 'employee', 'investigator', 'admin'] },
  { name: 'AI Assessment', href: '/ai-assessment', icon: Brain, roles: ['employee', 'investigator', 'admin'] },
  { name: 'Fraud Investigation', href: '/fraud', icon: AlertTriangle, roles: ['employee', 'investigator', 'admin'] },
  { name: 'Investigators', href: '/investigators', icon: Users, roles: ['employee', 'admin'] },
  { name: 'Repair Shops', href: '/repair-shops', icon: Wrench, roles: ['employee', 'repair', 'admin'] },
  { name: 'Settlements', href: '/settlements', icon: Gavel, roles: ['employee', 'admin'] },
  { name: 'AI Decision Center', href: '/ai-decision', icon: GitBranch, roles: ['employee', 'admin'] },
  { name: 'Analytics', href: '/analytics', icon: BarChart3, roles: ['employee', 'admin'] },
  { name: 'Notifications', href: '/notifications', icon: Bell, roles: ['customer', 'employee', 'investigator', 'repair', 'admin'] },
  { name: 'Profile', href: '/profile', icon: User, roles: ['customer', 'employee', 'investigator', 'repair', 'admin'] },
  { name: 'Settings', href: '/settings', icon: Settings, roles: ['admin'] },
]

const roleIcons = {
  customer: Shield,
  employee: Zap,
  investigator: Search,
  repair: Wrench,
  admin: FileCheck,
}

export function Sidebar({ collapsed, onToggle }) {
  const { user, hasRole } = useAuth()
  const location = useLocation()
  const [hovered, setHovered] = useState(null)

  const filteredNav = navigation.filter((item) =>
    user && hasRole(item.roles)
  )

  const getIcon = (item) => {
    const Icon = item.icon
    return <Icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
  }

  if (!user) return null

  return (
    <aside
      className={clsx(
        'fixed inset-y-0 left-0 z-40 bg-white border-r border-gray-200 transition-all duration-300 ease-in-out flex flex-col',
        collapsed ? 'w-20' : 'w-72'
      )}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      aria-label="Main navigation"
    >
      <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
        {!collapsed && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-gray-900">InsureX Nexus AI</span>
          </div>
        )}
        <button
          onClick={onToggle}
          className={clsx(
            'p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors',
            collapsed && 'ml-auto'
          )}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={!collapsed}
        >
          {collapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <ChevronLeft className="w-5 h-5" />
          )}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1" role="navigation" aria-label="Main menu">
        {filteredNav.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + '/')
          const badge = item.badge

          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive: active }) => clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                active
                  ? 'bg-primary/10 text-primary'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
                collapsed && 'justify-center'
              )}
              title={collapsed ? item.name : undefined}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon className={clsx('w-5 h-5 flex-shrink-0', isActive && 'text-primary')} aria-hidden="true" />
              {!collapsed && (
                <>
                  <span className="truncate">{item.name}</span>
                  {badge && (
                    <span className="ml-auto px-2 py-0.5 text-xs font-semibold rounded-full bg-primary/10 text-primary">
                      {badge}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          )
        })}
      </nav>

      {!collapsed && user && (
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center gap-3 p-2 rounded-lg bg-gray-50">
            <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
              {(() => {
                const RoleIcon = roleIcons[user.role] || Shield
                return <RoleIcon className="w-4 h-4 text-primary" />
              })()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{user.name}</p>
              <p className="text-xs text-gray-500 capitalize">{user.role}</p>
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}

export default Sidebar