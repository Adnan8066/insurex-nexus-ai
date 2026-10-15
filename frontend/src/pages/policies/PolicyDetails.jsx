import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  FileText,
  Shield,
  Calendar,
  Car,
  Home,
  ArrowLeft,
  Edit,
  Download,
  MoreVertical,
  CheckCircle,
  AlertTriangle,
  Clock,
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatDate } from '../../utils/helpers'
import { policyService } from '../../services'
import { useAuth } from '../../context/useAuth'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { EmptyState } from '../../components/ui/EmptyState'

const mapPolicy = (p) => ({
  id: p.id,
  policyNumber: p.policy_number,
  customerName: p.customer_name,
  customerEmail: p.customer_email,
  agent: p.agent_name,
  type: p.type,
  status: p.status,
  startDate: p.start_date,
  endDate: p.end_date,
  premium: p.premium,
  deductible: p.deductible,
  paymentFrequency: p.payment_frequency,
  autoRenew: p.auto_renew,
  policyPlan: p.coverage?.policy_plan || null,
  coverage: p.coverage_details || {},
  vehicle: p.vehicle_info || (p.vehicle ? {
    id: p.vehicle.id,
    make: p.vehicle.make,
    model: p.vehicle.model,
    year: p.vehicle.year,
    licensePlate: p.vehicle.license_plate,
    vin: p.vehicle.vin,
    color: p.vehicle.color,
  } : null),
  propertyAddress: p.property_address,
  propertyType: p.property_type,
  propertyYearBuilt: p.property_year_built,
  propertySquareFootage: p.property_square_footage,
  documents: p.documents || [],
  premiumHistory: p.premium_history || [],
  createdAt: p.created_at,
  updatedAt: p.updated_at,
})

export function PolicyDetails() {
  const { id } = useParams()
  const { user } = useAuth()
  const canEditPolicy = user?.role === 'admin'
  const canFileClaim = ['customer', 'employee', 'admin'].includes(user?.role)
  const [loading, setLoading] = useState(true)
  const [policy, setPolicy] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const fetchPolicy = async () => {
      setLoading(true)
      setError('')
      try {
        const res = await policyService.getPolicy(id)
        if (!cancelled) {
          setPolicy(mapPolicy(res))
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || 'Failed to load policy')
          setPolicy(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchPolicy()
    return () => {
      cancelled = true
    }
  }, [id])

  if (loading) {
    return (
      <div className="page animate-pulse">
        <div className="page-header">
          <div className="h-8 bg-gray-200 rounded w-48 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-64"></div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="card p-6 h-32"><div className="h-full bg-gray-100 rounded"></div></div>
            <div className="card p-6 h-48"><div className="h-full bg-gray-100 rounded"></div></div>
          </div>
          <div className="space-y-6">
            <div className="card p-6 h-32"><div className="h-full bg-gray-100 rounded"></div></div>
            <div className="card p-6 h-32"><div className="h-full bg-gray-100 rounded"></div></div>
          </div>
        </div>
      </div>
    )
  }

  if (!policy) {
    return (
      <div className="page">
        <div className="page-header">
          <Link to="/policies" className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4">
            <ArrowLeft className="w-4 h-4" />
            Back to Policies
          </Link>
        </div>
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
        )}
      </div>
    )
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'coverage', label: 'Coverage', icon: Shield },
    { id: 'vehicle', label: policy.vehicle ? 'Vehicle' : 'Property', icon: policy.vehicle ? Car : Home },
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'history', label: 'History', icon: Clock },
  ]

  return (
    <div className="page">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link to="/policies" className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-2">
            <ArrowLeft className="w-4 h-4" />
            Back to Policies
          </Link>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="page-title">{policy.policyNumber || ''}</h1>
            <StatusBadge status={policy.status} />
          </div>
          <p className="page-subtitle">{policy.policyPlan?.name || policy.type || ''} • {policy.customerName || ''}</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Download
          </Button>
          <Button variant="ghost" size="sm" className="relative">
            <MoreVertical className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-1" aria-label="Policy tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium rounded-t-lg border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              )}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {activeTab === 'overview' && (
            <>
              {policy.policyPlan && (
                <Card>
                  <CardHeader title="Selected Policy Tier" subtitle={`${policy.policyPlan.id} · ${policy.policyPlan.category}`} />
                  <CardContent>
                    <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                      The tier details and base premium are user-provided estimates, not a verified insurer quote or policy offer.
                    </p>
                    <dl className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      <div><dt className="text-sm font-medium text-gray-500">Coverage sections</dt><dd className="mt-1 text-gray-900">{(policy.policyPlan.coverage_sections || []).join('; ') || 'None listed'}</dd></div>
                      <div><dt className="text-sm font-medium text-gray-500">Mandatory covers</dt><dd className="mt-1 text-gray-900">{(policy.policyPlan.mandatory_covers || []).join('; ') || 'None listed'}</dd></div>
                      <div><dt className="text-sm font-medium text-gray-500">Available add-ons</dt><dd className="mt-1 text-gray-900">{(policy.policyPlan.addons || []).join(', ') || 'None listed'}</dd></div>
                      <div><dt className="text-sm font-medium text-gray-500">Base premium estimate</dt><dd className="mt-1 text-gray-900">{formatCurrency(policy.policyPlan.base_premium_estimate_inr, 'INR', 'en-IN')} per year</dd></div>
                    </dl>
                  </CardContent>
                </Card>
              )}
              <Card>
                <CardHeader title="Policy Information" />
                <CardContent>
                  <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Policy Type</dt>
                      <dd className="mt-1 text-gray-900 flex items-center gap-2">
                        <span className={clsx('text-gray-400', (policy.type || '').toLowerCase().includes('auto') && 'text-blue-500')}>
                          {(policy.type || '').toLowerCase().includes('auto') ? <Car className="w-4 h-4" /> : <Home className="w-4 h-4" />}
                        </span>
                        {policy.policyPlan?.name || policy.type || ''}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Agent</dt>
                      <dd className="mt-1 text-gray-900">{policy.agent || ''}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Effective Date</dt>
                      <dd className="mt-1 text-gray-900">{formatDate(policy.startDate)}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Expiration Date</dt>
                      <dd className="mt-1 text-gray-900">{formatDate(policy.endDate)}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Payment Frequency</dt>
                      <dd className="mt-1 text-gray-900 capitalize">{policy.paymentFrequency ? policy.paymentFrequency.replace(/_/g, ' ') : ''}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Auto Renewal</dt>
                      <dd className="mt-1 text-gray-900 flex items-center gap-2">
                        {policy.autoRenew ? (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-yellow-500" />
                        )}
                        {policy.autoRenew ? 'Enabled' : 'Disabled'}
                      </dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>

              <Card>
                <CardHeader title="Financial Summary" />
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <dt className="text-sm font-medium text-gray-500">Annual Premium</dt>
                      <dd className="mt-1 text-2xl font-bold text-gray-900">{formatCurrency(policy.premium, policy.policyPlan ? 'INR' : 'USD', policy.policyPlan ? 'en-IN' : 'en-US')}</dd>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <dt className="text-sm font-medium text-gray-500">Deductible</dt>
                      <dd className="mt-1 text-2xl font-bold text-gray-900">{formatCurrency(policy.deductible, policy.policyPlan ? 'INR' : 'USD', policy.policyPlan ? 'en-IN' : 'en-US')}</dd>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <dt className="text-sm font-medium text-gray-500">Payment per Period</dt>
                      <dd className="mt-1 text-2xl font-bold text-gray-900">
                        {formatCurrency((policy.paymentFrequency === 'monthly' ? (Number(policy.premium) || 0) / 12 : (Number(policy.premium) || 0)), policy.policyPlan ? 'INR' : 'USD', policy.policyPlan ? 'en-IN' : 'en-US')}
                      </dd>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}

          {activeTab === 'coverage' && (
            <Card>
              <CardHeader title="Coverage Details" subtitle="Coverage limits and inclusions" />
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 px-4 font-medium text-gray-500">Coverage</th>
                        <th className="text-right py-3 px-4 font-medium text-gray-500">Limit</th>
                        <th className="text-right py-3 px-4 font-medium text-gray-500">Deductible</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {Object.entries(policy.coverage || {}).map(([key, value]) => (
                        <tr key={key} className="hover:bg-gray-50">
                          <td className="py-3 px-4 text-gray-900 capitalize">{key.replace(/([A-Z])/g, ' $1').replace(/_/g, ' ')}</td>
                          <td className="py-3 px-4 text-right font-medium text-gray-900">{formatCurrency(value)}</td>
                          <td className="py-3 px-4 text-right text-gray-500">
                            {key === 'liability' || key === 'dwelling' || key === 'personalProperty' || key === 'personal_property' ? formatCurrency(policy.deductible) : 'N/A'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'vehicle' && policy.vehicle && (
            <Card>
              <CardHeader title="Vehicle Information" />
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <dl className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Make</dt>
                          <dd className="mt-1 text-gray-900">{policy.vehicle.make || ''} {policy.vehicle.model || ''}</dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Year</dt>
                          <dd className="mt-1 text-gray-900">{policy.vehicle.year || ''}</dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Color</dt>
                          <dd className="mt-1 text-gray-900">{policy.vehicle.color || ''}</dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">VIN</dt>
                          <dd className="mt-1 text-gray-900 font-mono">{policy.vehicle.vin || ''}</dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">License Plate</dt>
                          <dd className="mt-1 text-gray-900">{policy.vehicle.licensePlate || ''}</dd>
                        </div>
                      </div>
                    </dl>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'documents' && (
            <Card>
              <CardHeader title="Policy Documents" action={<Button variant="outline" size="sm">Upload</Button>} />
              <CardContent>
                <EmptyState
                  icon={<FileText className="w-12 h-12" />}
                  title="No documents uploaded"
                  description="Policy documents will appear here once uploaded."
                  action={<Button variant="outline" size="sm">Upload Document</Button>}
                />
              </CardContent>
            </Card>
          )}

          {activeTab === 'history' && (
            <Card>
              <CardHeader title="Policy History" />
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                    <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0">
                      <FileText className="w-4 h-4 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Policy Created</p>
                      <p className="text-sm text-gray-500">{formatDate(policy.startDate)}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                    <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Policy Activated</p>
                      <p className="text-sm text-gray-500">{formatDate(policy.startDate)}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Quick Actions" />
            <CardContent>
              <div className="space-y-3">
                {canEditPolicy && <Button variant="outline" className="w-full justify-start gap-3" asChild>
                  <Link to={`/policies/${policy.id}/edit`}>
                    <Edit className="w-4 h-4" />
                    Edit Policy
                  </Link>
                </Button>}
                <Button variant="outline" className="w-full justify-start gap-3">
                  <Download className="w-4 h-4" />
                  Download Certificate
                </Button>
                <Button variant="outline" className="w-full justify-start gap-3">
                  <Calendar className="w-4 h-4" />
                  View Payment Schedule
                </Button>
                {canFileClaim && <Button variant="outline" className="w-full justify-start gap-3" asChild>
                  <Link to={`/claims/new?policy=${policy.id}`}>
                    <Shield className="w-4 h-4" />
                    File a Claim
                  </Link>
                </Button>}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Policy Status" />
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-500">Days Remaining</span>
                    <span className="font-medium text-gray-900">
                       {Math.max(0, Math.ceil(((new Date(policy.endDate)) - new Date()) / (1000 * 60 * 60 * 24)))} days
                     </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-primary h-2 rounded-full transition-all"
                      style={{
                         width: `${Math.min(100, Math.max(0, (((new Date()) - new Date(policy.startDate || new Date())) / ((new Date(policy.endDate || new Date())) - new Date(policy.startDate || new Date())) || 0) * 100))}%`
                       }}
                    />
                  </div>
                </div>
                <div className="pt-4 border-t border-gray-200">
                  <p className="text-sm text-gray-600">
                    {policy.status === 'active' ? 'Policy is active and in force.' : 'Policy is not currently active.'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default PolicyDetails
