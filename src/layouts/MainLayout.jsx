import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from '../components/layout/Sidebar'
import { Navbar } from '../components/layout/Navbar'
import { clsx } from 'clsx'

export function MainLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <div className={clsx('flex-1 transition-all duration-300 min-w-0 flex flex-col', sidebarCollapsed ? 'lg:pl-20' : 'lg:pl-72')}>
        <Navbar sidebarCollapsed={sidebarCollapsed} onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)} />
        <main
          className="pt-16 min-h-screen w-full flex-1"
          role="main"
        >
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export function AuthLayout({ children }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {children}
      </div>
    </div>
  )
}

export default { MainLayout, AuthLayout }