import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  Car,
  Calendar,
  Wrench,
  FileText,
  ArrowLeft,
  Edit,
  CheckCircle,
  AlertTriangle,
  ShieldCheck,
} from 'lucide-react'
import { format } from 'date-fns'
import { clsx } from 'clsx'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'
import { vehicleService, policyService } from '../../services'
import { INCIDENT_TYPES, INCIDENT_SEVERITIES, POLICY_STATUSES, labelFor } from '../../constants/domain'
import { DocumentUpload } from '../../components/forms/DocumentUpload'
import { useAuth } from '../../context/useAuth'

const VEHICLE_DOCUMENT_TYPES = [
  { value: 'registration', label: 'Registration' },
  { value: 'inspection', label: 'Inspection Report' },
  { value: 'title', label: 'Title' },
  { value: 'bill_of_sale', label: 'Bill of Sale' },
  { value: 'insurance_card', label: 'Insurance Card' },
  { value: 'other', label: 'Other' },
]

const formatKm = (value) => (value != null && value !== '' ? `${Number(value).toLocaleString('en-IN')} km` : '—')
const describeClaim = (claim) => [labelFor(INCIDENT_TYPES, claim.incidentType, ''), labelFor(INCIDENT_SEVERITIES, claim.incidentSeverity, '')].filter(Boolean).join(' • ')
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { EmptyState } from '../../components/ui/EmptyState'
import { formatApiError } from '../../services/api'

const mapVehicle = (v) => ({
  id: v.id,
  make: v.make,
  model: v.model,
  year: v.year,
  vin: v.vin,
  color: v.color,
  licensePlate: v.license_plate,
  licenseState: v.license_state,
  registrationExpiry: v.registration_expiry,
  purchaseDate: v.purchase_date,
  purchasePrice: v.purchase_price,
  currentMileage: v.current_mileage,
  fuelType: v.fuel_type,
  transmission: v.transmission,
  status: v.status,
  customerId: v.customer,
  customerName: v.customer_name,
  customerEmail: v.customer_email,
  policyNumber: v.policy_number,
  policyId: v.policy,
  documents: (v.documents || []).map((d) => ({
    id: d.id,
    name: d.original_name,
    type: d.document_type,
    file: d.file,
    uploadedAt: d.uploaded_at,
  })),
  history: v.history || [],
})

const mapClaim = (c) => ({
  id: c.id,
  claimNumber: c.claim_number,
  incidentDate: c.incident_date,
  incidentType: c.incident_type,
  incidentSeverity: c.incident_severity,
  claimAmount: Number(c.claim_amount) || 0,
  status: c.status,
  submittedAt: c.submitted_at,
  location: c.location,
})

export function VehicleDetails() {
  const { id } = useParams()
  const [loading, setLoading] = useState(true)
  const [vehicle, setVehicle] = useState(null)
  const [claims, setClaims] = useState([])
  const [activeTab, setActiveTab] = useState('overview')
  const [error, setError] = useState('')
  const [notFound, setNotFound] = useState(false)
  const [policyStatus, setPolicyStatus] = useState(null)
  const [pendingRequest, setPendingRequest] = useState(null)
  const { user } = useAuth()
  const isCustomer = user?.role === 'customer'

  useEffect(() => {
    let cancelled = false
    const fetchData = async () => {
      setLoading(true)
      setError('')
      setNotFound(false)
      try {
        const [vehicleRes, claimsRes] = await Promise.all([
          vehicleService.getVehicle(id),
          vehicleService.getVehicleClaims(id),
        ])
        if (!cancelled) {
          setVehicle(mapVehicle(vehicleRes))
          const claimsData = Array.isArray(claimsRes) ? claimsRes : (claimsRes.results || [])
          setClaims(claimsData.map(mapClaim))
        }
      } catch (err) {
        if (!cancelled) {
          setNotFound(err.response?.status === 404)
          setError(formatApiError(err, 'Failed to load vehicle'))
          setVehicle(null)
          setClaims([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchData()
    return () => {
      cancelled = true
    }
  }, [id])

  const policyId = vehicle?.policyId
  const vehicleId = vehicle?.id
  // Customers without a policy see whether a request for this vehicle is already with staff.
  useEffect(() => {
    let active = true
    setPendingRequest(null)
    if (!isCustomer || !vehicleId || policyId) return () => { active = false }
    policyService.getPolicyApplications({ status: 'quoted' })
      .then((result) => {
        const items = Array.isArray(result) ? result : result.results || []
        if (active) setPendingRequest(items.find((item) => String(item.policy_terms?.vehicle) === String(vehicleId)) || null)
      })
      .catch(() => {})
    return () => { active = false }
  }, [isCustomer, vehicleId, policyId])

  useEffect(() => {
    let active = true
    setPolicyStatus(null)
    if (!policyId) return () => { active = false }
    policyService.getPolicy(policyId)
      .then((policy) => { if (active) setPolicyStatus(policy?.status || 'unknown') })
      .catch(() => { if (active) setPolicyStatus('unknown') })
    return () => { active = false }
  }, [policyId])

  if (loading) {
    return (
      <div className="page animate-pulse">
        <div className="page-header">
          <div className="h-8 bg-gray-200 rounded w-48 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-64"></div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="h-32 bg-gray-200 rounded-xl"></div>
            <div className="h-48 bg-gray-200 rounded-xl"></div>
          </div>
          <div className="space-y-6">
            <div className="h-32 bg-gray-200 rounded-xl"></div>
            <div className="h-32 bg-gray-200 rounded-xl"></div>
          </div>
        </div>
      </div>
    )
  }

  if (!vehicle) {
    return (
      <div className="page">
        <div className="page-header">
          <Link to="/vehicles" className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4">
            <ArrowLeft className="w-4 h-4" />
            Back to Vehicles
          </Link>
        </div>
        <Card>
          <EmptyState
            icon={<Car className="w-12 h-12" />}
            title={notFound ? 'Vehicle not found' : 'Could not load this vehicle'}
            description={notFound ? 'This vehicle does not exist or you do not have access to it.' : (error || 'Please try again in a moment.')}
            action={<Button asChild variant="outline"><Link to="/vehicles">Back to Vehicles</Link></Button>}
          />
        </Card>
      </div>
    )
  }

  const vehicleClaims = claims
  const today = format(new Date(), 'yyyy-MM-dd')
  const registrationExpired = Boolean(vehicle.registrationExpiry) && vehicle.registrationExpiry < today
  const policyActive = policyStatus === 'active'

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Car },
    { id: 'claims', label: 'Claims History', icon: FileText },
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'maintenance', label: 'Maintenance', icon: Wrench },
  ]

  return (
    <div className="page">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link to="/vehicles" className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-2">
            <ArrowLeft className="w-4 h-4" />
            Back to Vehicles
          </Link>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="page-title">{vehicle.year || ''} {vehicle.make || ''} {vehicle.model || ''}</h1>
            <StatusBadge status={vehicle.status} />
            {registrationExpired && <Badge variant="danger">Registration expired</Badge>}
          </div>
          <p className="page-subtitle">{[vehicle.color, vehicle.licensePlate, vehicle.vin && `VIN ending ${vehicle.vin.slice(-6)}`].filter(Boolean).join(' • ')}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="outline" size="sm" asChild>
            <Link to={`/vehicles/${vehicle.id}/edit`}>
              <Edit className="w-4 h-4 mr-2" />
              Edit
            </Link>
          </Button>
        </div>
      </div>

      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-1 overflow-x-auto" aria-label="Vehicle tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium rounded-t-lg border-b-2 whitespace-nowrap transition-colors',
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
              <Card>
                <CardHeader title="Vehicle Information" />
                <CardContent>
                  <dl className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <div>
                      <dt className="text-sm font-medium text-gray-500">VIN</dt>
                      <dd className="mt-1 text-gray-900 font-mono">{vehicle.vin || ''}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">License Plate</dt>
                      <dd className="mt-1 text-gray-900">{vehicle.licensePlate || ''}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Color</dt>
                      <dd className="mt-1 text-gray-900">{vehicle.color || ''}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Fuel Type</dt>
                      <dd className="mt-1 text-gray-900">{vehicle.fuelType ? vehicle.fuelType.replace(/_/g, ' ') : ''}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Transmission</dt>
                      <dd className="mt-1 text-gray-900">{vehicle.transmission ? vehicle.transmission.replace(/_/g, ' ') : ''}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Odometer</dt>
                      <dd className="mt-1 text-gray-900">{formatKm(vehicle.currentMileage)}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Registration Expiry</dt>
                      <dd className="mt-1 text-gray-900 flex flex-wrap items-center gap-1">
                        <Calendar className="w-4 h-4 text-gray-400" aria-hidden="true" />
                        {formatDate(vehicle.registrationExpiry)}
                        {registrationExpired && <Badge variant="danger" size="sm">Expired</Badge>}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Purchase Date</dt>
                      <dd className="mt-1 text-gray-900">{formatDate(vehicle.purchaseDate)}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Purchase Price</dt>
                      <dd className="mt-1 text-gray-900">{formatCurrency(vehicle.purchasePrice)}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Customer</dt>
                      <dd className="mt-1 text-gray-900">{vehicle.customerName || 'Customer details unavailable'}</dd>
                      {vehicle.customerEmail && <dd className="text-sm text-gray-500">{vehicle.customerEmail}</dd>}
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Linked Policy</dt>
                      <dd className="mt-1 text-gray-900">
                        {vehicle.policyId
                          ? <Link to={`/policies/${vehicle.policyId}`} className="text-primary hover:underline">{vehicle.policyNumber || `Policy #${vehicle.policyId}`}</Link>
                          : 'No policy'}
                      </dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>

              <Card>
                <CardHeader title="Claims History" subtitle={`${vehicleClaims.length} claim(s) on this vehicle`} />
                <CardContent>
                  {vehicleClaims.length > 0 ? (
                    <div className="space-y-4">
                      {vehicleClaims.map((claim) => (
                        <Link key={claim.id} to={`/claims/${claim.id}`} className="block p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                               <span className="font-medium text-gray-900">{claim.claimNumber || ''}</span>
                                 <StatusBadge status={claim.status} />
                                 <span className="text-sm text-gray-500">{formatDate(claim.incidentDate)}</span>
                               </div>
                               <p className="text-sm text-gray-600 mt-1">{describeClaim(claim)}</p>
                               <p className="text-sm text-gray-500 mt-0.5">{claim.location || ''}</p>
                             </div>
                             <div className="text-right flex-shrink-0">
                               <p className="font-semibold text-gray-900">{formatCurrency(claim.claimAmount)}</p>
                               <p className="text-xs text-gray-500">{formatRelativeTime(claim.submittedAt)}</p>
                            </div>
                          </div>
                        </Link>
                      ))}
                    </div>
                  ) : (
                    <EmptyState
                      icon={<FileText className="w-12 h-12" />}
                      title="No claims on this vehicle"
                      description="This vehicle has no claim history."
                    />
                  )}
                </CardContent>
              </Card>
            </>
          )}

          {activeTab === 'claims' && (
            <Card>
              <CardHeader title="Claims History" />
              <CardContent>
                {vehicleClaims.length > 0 ? (
                  <div className="space-y-4">
                    {vehicleClaims.map((claim) => (
                      <Link key={claim.id} to={`/claims/${claim.id}`} className="block p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-medium text-gray-900">{claim.claimNumber || ''}</span>
                              <StatusBadge status={claim.status} />
                              <span className="text-sm text-gray-500">{formatDate(claim.incidentDate)}</span>
                            </div>
                            <p className="text-sm text-gray-600 mt-1">{describeClaim(claim)}</p>
                            <p className="text-sm text-gray-500 mt-0.5">{claim.location || ''}</p>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <p className="font-semibold text-gray-900">{formatCurrency(claim.claimAmount)}</p>
                            <p className="text-xs text-gray-500">{formatRelativeTime(claim.submittedAt)}</p>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={<FileText className="w-12 h-12" />}
                    title="No claims on this vehicle"
                    description="This vehicle has no claim history."
                  />
                )}
              </CardContent>
            </Card>
          )}

          {activeTab === 'documents' && (
            <Card>
              <CardHeader title="Documents" />
              <CardContent className="space-y-6">
                <DocumentUpload
                  documentTypes={VEHICLE_DOCUMENT_TYPES}
                  onUpload={(formData) => vehicleService.uploadVehicleDocument(vehicle.id, formData)}
                  onUploaded={(doc) => {
                    if (!doc) return
                    setVehicle((current) => ({
                      ...current,
                      documents: [{ id: doc.id, name: doc.original_name, type: doc.document_type, file: doc.file, uploadedAt: doc.uploaded_at }, ...current.documents],
                    }))
                  }}
                />
                    {vehicle.documents && vehicle.documents.length > 0 ? (
                      <div className="space-y-3">
                        {vehicle.documents.map((doc, index) => (
                          <div key={doc.id || index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                                <FileText className="w-5 h-5 text-primary" />
                              </div>
                              <div>
                                <p className="font-medium text-gray-900">{doc.name || ''}</p>
                                <p className="text-sm text-gray-500">{labelFor(VEHICLE_DOCUMENT_TYPES, doc.type, '')} • {formatDate(doc.uploadedAt)}</p>
                              </div>
                            </div>
                            <Button variant="ghost" size="sm" asChild>
                              <a href={doc.file} target="_blank" rel="noopener noreferrer">View</a>
                            </Button>
                          </div>
                        ))}
                      </div>
                ) : (
                  <EmptyState
                    icon={<FileText className="w-12 h-12" />}
                    title="No documents uploaded"
                    description="Upload the registration, inspection report or other papers above."
                  />
                )}
              </CardContent>
            </Card>
          )}

          {activeTab === 'maintenance' && (
            <Card>
              <CardHeader title="Service History" />
              <CardContent>
                {vehicle.history.length > 0 ? (
                  <ul className="divide-y divide-gray-100">
                    {vehicle.history.map((event) => (
                      <li key={event.id} className="flex flex-wrap items-start justify-between gap-2 py-3">
                        <div className="min-w-0">
                          <p className="font-medium text-gray-900">{labelFor([], event.event_type)}</p>
                          {event.description && <p className="text-sm text-gray-600">{event.description}</p>}
                        </div>
                        <div className="text-right text-sm text-gray-500">
                          <p>{formatDate(event.date)}</p>
                          {event.mileage != null && <p>{formatKm(event.mileage)}</p>}
                          {event.cost != null && <p>{formatCurrency(event.cost)}</p>}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState
                    icon={<Wrench className="w-12 h-12" />}
                    title="No service history"
                    description="Service and maintenance events for this vehicle will appear here."
                  />
                )}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Quick Actions" />
            <CardContent>
              <div className="space-y-3">
                {isCustomer && !vehicle.policyId && (pendingRequest ? (
                  <Link to={`/vehicles/${vehicle.id}/insure`} className="block rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 hover:bg-amber-100">
                    <span className="font-semibold">Policy request waiting for review</span>
                    <span className="block text-xs">Quoted {formatCurrency(Number(pendingRequest.quoted_premium))} a year · sent {formatDate(pendingRequest.created_at)}</span>
                  </Link>
                ) : (
                  <Button variant="primary" className="w-full justify-start gap-3" asChild>
                    <Link to={`/vehicles/${vehicle.id}/insure`}>
                      <ShieldCheck className="w-4 h-4" />
                      Insure this vehicle
                    </Link>
                  </Button>
                ))}
                <Button variant="outline" className="w-full justify-start gap-3" asChild>
                  <Link to={`/vehicles/${vehicle.id}/edit`}>
                    <Edit className="w-4 h-4" />
                    Edit Vehicle
                  </Link>
                </Button>
                <Button variant="outline" className="w-full justify-start gap-3" asChild>
                  <Link to={`/claims/new?vehicle=${vehicle.id}`}>
                    <FileText className="w-4 h-4" />
                    File Claim
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Vehicle Status" />
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between gap-3 p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className={clsx('w-8 h-8 rounded-full flex items-center justify-center', policyActive ? 'bg-green-100' : 'bg-amber-100')}>
                      {policyActive
                        ? <CheckCircle className="w-4 h-4 text-green-500" aria-hidden="true" />
                        : <AlertTriangle className="w-4 h-4 text-amber-500" aria-hidden="true" />}
                    </div>
                    <span className="text-sm font-medium text-gray-900">Insurance</span>
                  </div>
                  {!vehicle.policyId ? (
                    <Badge variant="warning">No policy</Badge>
                  ) : policyStatus === null ? (
                    <span className="text-sm text-gray-500">Checking…</span>
                  ) : policyStatus === 'unknown' ? (
                    <span className="text-sm text-gray-500">{vehicle.policyNumber || 'Linked'}</span>
                  ) : (
                    <Badge variant={policyActive ? 'success' : 'warning'}>{labelFor(POLICY_STATUSES, policyStatus)}</Badge>
                  )}
                </div>
                <div className={clsx('flex items-center justify-between gap-3 p-3 rounded-lg', registrationExpired ? 'bg-red-50' : 'bg-gray-50')}>
                  <div className="flex items-center gap-3">
                    <div className={clsx('w-8 h-8 rounded-full flex items-center justify-center', registrationExpired ? 'bg-red-100' : 'bg-blue-100')}>
                      <Calendar className={clsx('w-4 h-4', registrationExpired ? 'text-red-600' : 'text-blue-500')} aria-hidden="true" />
                    </div>
                    <span className={clsx('text-sm font-medium', registrationExpired ? 'text-red-700' : 'text-gray-900')}>
                      {!vehicle.registrationExpiry ? 'Registration' : registrationExpired ? 'Registration expired' : 'Registration valid'}
                    </span>
                  </div>
                  <span className={clsx('text-sm', registrationExpired ? 'text-red-700' : 'text-gray-600')}>
                    {vehicle.registrationExpiry
                      ? `${registrationExpired ? 'Expired' : 'Expires'} ${formatDate(vehicle.registrationExpiry)}`
                      : 'Not recorded'}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Quick Stats" />
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Claims</span>
                  <span className="font-semibold text-gray-900">{vehicleClaims.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Claim Amount</span>
                  <span className="font-semibold text-gray-900">{formatCurrency(vehicleClaims.reduce((sum, c) => sum + (Number(c.claimAmount) || 0), 0))}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Vehicle Age</span>
                  <span className="font-semibold text-gray-900">{vehicle.year ? new Date().getFullYear() - vehicle.year : 0} years</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Odometer</span>
                  <span className="font-semibold text-gray-900">{formatKm(vehicle.currentMileage)}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default VehicleDetails
