import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '../context/useAuth'

const Login = lazy(() => import('../pages/auth/Login').then((module) => ({ default: module.Login })))
const Register = lazy(() => import('../pages/auth/Register').then((module) => ({ default: module.Register })))
const ForgotPassword = lazy(() => import('../pages/auth/ForgotPassword').then((module) => ({ default: module.ForgotPassword })))
const MainLayout = lazy(() => import('../layouts/MainLayout').then((module) => ({ default: module.MainLayout })))
const CustomerDashboard = lazy(() => import('../pages/dashboard/CustomerDashboard').then((module) => ({ default: module.CustomerDashboard })))
const EmployeeDashboard = lazy(() => import('../pages/dashboard/EmployeeDashboard').then((module) => ({ default: module.EmployeeDashboard })))
const PolicyList = lazy(() => import('../pages/policies/PolicyList').then((module) => ({ default: module.PolicyList })))
const PolicyDetails = lazy(() => import('../pages/policies/PolicyDetails').then((module) => ({ default: module.PolicyDetails })))
const PolicyForm = lazy(() => import('../pages/policies/PolicyForm').then((module) => ({ default: module.PolicyForm })))
const VehicleList = lazy(() => import('../pages/vehicles/VehicleList').then((module) => ({ default: module.VehicleList })))
const VehicleDetails = lazy(() => import('../pages/vehicles/VehicleDetails').then((module) => ({ default: module.VehicleDetails })))
const VehicleForm = lazy(() => import('../pages/vehicles/VehicleForm').then((module) => ({ default: module.VehicleForm })))
const ClaimList = lazy(() => import('../pages/claims/ClaimList').then((module) => ({ default: module.ClaimList })))
const ClaimDetails = lazy(() => import('../pages/claims/ClaimDetails').then((module) => ({ default: module.ClaimDetails })))
const SubmitClaim = lazy(() => import('../pages/claims/SubmitClaim').then((module) => ({ default: module.SubmitClaim })))
const ClaimTracking = lazy(() => import('../pages/claims/ClaimTracking').then((module) => ({ default: module.ClaimTracking })))
const AIAssessment = lazy(() => import('../pages/ai/AIAssessment').then((module) => ({ default: module.AIAssessment })))
const FraudDashboard = lazy(() => import('../pages/fraud/FraudDashboard').then((module) => ({ default: module.FraudDashboard })))
const InvestigatorDashboard = lazy(() => import('../pages/investigator/InvestigatorDashboard').then((module) => ({ default: module.InvestigatorDashboard })))
const RepairDashboard = lazy(() => import('../pages/repair/RepairDashboard').then((module) => ({ default: module.RepairDashboard })))
const SettlementDashboard = lazy(() => import('../pages/settlement/SettlementDashboard').then((module) => ({ default: module.SettlementDashboard })))
const AdminDashboard = lazy(() => import('../pages/admin/AdminDashboard').then((module) => ({ default: module.AdminDashboard })))
const AIDecisionCenter = lazy(() => import('../pages/decision/AIDecisionCenter').then((module) => ({ default: module.AIDecisionCenter })))
const AIOperations = lazy(() => import('../pages/operations/AIOperations').then((module) => ({ default: module.AIOperations })))
const Notifications = lazy(() => import('../pages/notifications/Notifications').then((module) => ({ default: module.Notifications })))
const Profile = lazy(() => import('../pages/profile/Profile').then((module) => ({ default: module.Profile })))
const Settings = lazy(() => import('../pages/settings/Settings').then((module) => ({ default: module.Settings })))

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
    <Suspense fallback={<div className="p-8 text-center text-gray-500" role="status">Loading page…</div>}>
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />

      <Route path="/" element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<RoleBasedDashboard />} />
        <Route path="policies" element={<PolicyList />} />
        <Route path="policies/new" element={<ProtectedRoute roles={['admin']}><PolicyForm /></ProtectedRoute>} />
        <Route path="policies/:id" element={<PolicyDetails />} />
        <Route path="policies/:id/edit" element={<PolicyForm />} />
        <Route path="vehicles" element={<VehicleList />} />
        <Route path="vehicles/new" element={<VehicleForm />} />
        <Route path="vehicles/:id" element={<VehicleDetails />} />
        <Route path="vehicles/:id/edit" element={<VehicleForm />} />
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
    </Suspense>
  )
}
