import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Login } from '../pages/auth/Login'
import { Register } from '../pages/auth/Register'
import { ForgotPassword } from '../pages/auth/ForgotPassword'
import { MainLayout } from '../layouts/MainLayout'
import { CustomerDashboard } from '../pages/dashboard/CustomerDashboard'
import { EmployeeDashboard } from '../pages/dashboard/EmployeeDashboard'
import { PolicyList } from '../pages/policies/PolicyList'
import { PolicyDetails } from '../pages/policies/PolicyDetails'
import { VehicleList } from '../pages/vehicles/VehicleList'
import { VehicleDetails } from '../pages/vehicles/VehicleDetails'
import { ClaimList } from '../pages/claims/ClaimList'
import { ClaimDetails } from '../pages/claims/ClaimDetails'
import { SubmitClaim } from '../pages/claims/SubmitClaim'
import { ClaimTracking } from '../pages/claims/ClaimTracking'
import { AIAssessment } from '../pages/ai/AIAssessment'
import { FraudDashboard } from '../pages/fraud/FraudDashboard'
import { InvestigatorDashboard } from '../pages/investigator/InvestigatorDashboard'
import { RepairDashboard } from '../pages/repair/RepairDashboard'
import { SettlementDashboard } from '../pages/settlement/SettlementDashboard'
import { AdminDashboard } from '../pages/admin/AdminDashboard'
import { AIDecisionCenter } from '../pages/decision/AIDecisionCenter'
import { AIOperations } from '../pages/operations/AIOperations'
import { Notifications } from '../pages/notifications/Notifications'
import { Profile } from '../pages/profile/Profile'
import { Settings } from '../pages/settings/Settings'

function ProtectedRoute({ children, roles }) {
  const { isAuthenticated, user, hasRole } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (roles && !hasRole(roles)) return <Navigate to="/dashboard" replace />
  return children
}

function RoleBasedDashboard() {
  const { user } = useAuth()
  if (!user) return <CustomerDashboard />
  if (user.role === 'employee') return <EmployeeDashboard />
  if (user.role === 'admin') return <AdminDashboard />
  if (user.role === 'investigator') return <InvestigatorDashboard />
  if (user.role === 'repair') return <RepairDashboard />
  return <CustomerDashboard />
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />

      <Route path="/" element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<RoleBasedDashboard />} />
        <Route path="policies" element={<PolicyList />} />
        <Route path="policies/:id" element={<PolicyDetails />} />
        <Route path="vehicles" element={<VehicleList />} />
        <Route path="vehicles/:id" element={<VehicleDetails />} />
        <Route path="claims" element={<ClaimList />} />
        <Route path="claims/:id" element={<ClaimDetails />} />
        <Route path="claims/new" element={<SubmitClaim />} />
        <Route path="claims/:id/tracking" element={<ClaimTracking />} />
        <Route path="ai-assessment" element={<AIAssessment />} />
        <Route path="fraud" element={<FraudDashboard />} />
        <Route path="investigators" element={<InvestigatorDashboard />} />
        <Route path="repair-shops" element={<RepairDashboard />} />
        <Route path="settlements" element={<SettlementDashboard />} />
        <Route path="analytics" element={<AdminDashboard />} />
        <Route path="ai-decision" element={<AIDecisionCenter />} />
        <Route path="operations" element={<AIOperations />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="profile" element={<Profile />} />
        <Route path="settings" element={<Settings />} />
      </Route>

      {/* Fallback route */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}