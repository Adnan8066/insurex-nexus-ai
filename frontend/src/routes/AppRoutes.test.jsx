import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AppRoutes from './AppRoutes'

// Signed-in user for each test. Set by the tests below.
const auth = vi.hoisted(() => ({ user: null }))

vi.mock('../context/useAuth', () => ({
  useAuth: () => ({
    user: auth.user,
    isAuthenticated: Boolean(auth.user),
    loading: false,
    hasRole: (roles) => Boolean(auth.user) && roles.includes(auth.user.role),
  }),
}))

// Replace the layout and the pages with simple stubs, so the test checks only the route guards.
vi.mock('../layouts/MainLayout', async () => {
  const { Outlet } = await import('react-router-dom')
  return { MainLayout: () => <Outlet /> }
})
vi.mock('../pages/LandingPage', () => ({ LandingPage: () => <div>PAGE:Landing</div> }))
vi.mock('../pages/auth/Login', () => ({ Login: () => <div>PAGE:Login</div> }))
vi.mock('../pages/dashboard/CustomerDashboard', () => ({ CustomerDashboard: () => <div>PAGE:CustomerDashboard</div> }))
vi.mock('../pages/dashboard/EmployeeDashboard', () => ({ EmployeeDashboard: () => <div>PAGE:EmployeeDashboard</div> }))
vi.mock('../pages/admin/AdminDashboard', () => ({ AdminDashboard: () => <div>PAGE:AdminDashboard</div> }))
vi.mock('../pages/investigator/InvestigatorDashboard', () => ({ InvestigatorDashboard: () => <div>PAGE:InvestigatorDashboard</div> }))
vi.mock('../pages/policies/PolicyList', () => ({ PolicyList: () => <div>PAGE:PolicyList</div> }))
vi.mock('../pages/vehicles/VehicleList', () => ({ VehicleList: () => <div>PAGE:VehicleList</div> }))
vi.mock('../pages/claims/SubmitClaim', () => ({ SubmitClaim: () => <div>PAGE:SubmitClaim</div> }))

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  )
}

const RESTRICTED_FOR_INVESTIGATORS = [
  { path: '/claims/new', page: 'PAGE:SubmitClaim' },
  { path: '/policies', page: 'PAGE:PolicyList' },
  { path: '/vehicles', page: 'PAGE:VehicleList' },
]

describe('route guards for investigators', () => {
  beforeEach(() => {
    auth.user = { id: 7, role: 'investigator', email: 'inv@example.com' }
  })

  it.each(RESTRICTED_FOR_INVESTIGATORS)('does not show the page at $path and sends the investigator to their case list', async ({ path, page }) => {
    renderAt(path)
    expect(await screen.findByText('PAGE:InvestigatorDashboard')).toBeInTheDocument()
    expect(screen.queryByText(page)).not.toBeInTheDocument()
  })

  it('still lets an investigator open their case list', async () => {
    renderAt('/investigators')
    expect(await screen.findByText('PAGE:InvestigatorDashboard')).toBeInTheDocument()
  })
})

describe('route guards for other roles', () => {
  it('lets a customer open policies, vehicles and claim submission', async () => {
    auth.user = { id: 1, role: 'customer', email: 'cust@example.com' }
    renderAt('/policies')
    expect(await screen.findByText('PAGE:PolicyList')).toBeInTheDocument()
  })

  it('lets a customer open claim submission', async () => {
    auth.user = { id: 1, role: 'customer', email: 'cust@example.com' }
    renderAt('/claims/new')
    expect(await screen.findByText('PAGE:SubmitClaim')).toBeInTheDocument()
  })

  it('lets an employee open the vehicle list', async () => {
    auth.user = { id: 2, role: 'employee', email: 'emp@example.com' }
    renderAt('/vehicles')
    expect(await screen.findByText('PAGE:VehicleList')).toBeInTheDocument()
  })

  it('keeps a customer out of the investigator case list and sends them to the dashboard', async () => {
    auth.user = { id: 1, role: 'customer', email: 'cust@example.com' }
    renderAt('/investigators')
    expect(await screen.findByText('PAGE:CustomerDashboard')).toBeInTheDocument()
    expect(screen.queryByText('PAGE:InvestigatorDashboard')).not.toBeInTheDocument()
  })
})
