import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  Car,
  Calendar,
  DollarSign,
  Wrench,
  FileText,
  ArrowLeft,
  Edit,
  Download,
  MoreVertical,
  ChevronRight,
  Clock,
  CheckCircle,
  AlertTriangle,
  MapPin,
  Gauge,
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'
import { mockVehicles } from '../../data/vehicles'
import { mockClaims } from '../../data/claims'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { EmptyState } from '../../components/ui/EmptyState'
import { LoadingSpinner } from '../../components/ui/LoadingSpinner'

export function VehicleDetails() {
  const { id } = useParams()
  const [loading, setLoading] = useState(true)
  const [vehicle, setVehicle] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    const timer = setTimeout(() => {
      const found = mockVehicles.find((v) => v.id === parseInt(id))
      setVehicle(found || null)
      setLoading(false)
    }, 400)
    return () => clearTimeout(timer)
  }, [id])

  if (loading) {
    return (
      <div className="page animate-pulse">
        <div className="page-header">
          <div className="h-8 bg-gray-200 rounded w-48 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-64"></div>
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
        <EmptyState
          icon={<Car className="w-12 h-12" />}
          title="Vehicle not found"
          description="The vehicle you're looking for doesn't exist or has been removed."
          action={<Button asChild><Link to="/vehicles">Browse Vehicles</Link></Button>}
        />
      </div>
    )
  }

  const vehicleClaims = mockClaims.filter((c) => c.vehicleId === vehicle.id)

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
          <div className="flex items-center gap-3">
            <h1 className="page-title">{vehicle.year} {vehicle.make} {vehicle.model}</h1>
            <StatusBadge status={vehicle.status} />
          </div>
          <p className="page-subtitle">{vehicle.color} • {vehicle.licensePlate} • VIN: {vehicle.vin.slice(-6)}</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
          <Button variant="ghost" size="sm" className="relative">
            <MoreVertical className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-1" aria-label="Vehicle tabs">
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
              <Card>
                <CardHeader title="Vehicle Information" />
                <CardContent>
                  <dl className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <div>
                      <dt className="text-sm font-medium text-gray-500">VIN</dt>
                      <dd className="mt-1 text-gray-900 font-mono">{vehicle.vin}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">License Plate</dt>
                      <dd className="mt-1 text-gray-900">{vehicle.licensePlate}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Color</dt>
                      <dd className="mt-1 text-gray-900">{vehicle.color}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Fuel Type</dt>
                      <dd className="mt-1 text-gray-900">{vehicle.fuelType}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Transmission</dt>
                      <dd className="mt-1 text-gray-900">{vehicle.transmission}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Current Mileage</dt>
                      <dd className="mt-1 text-gray-900">{vehicle.currentMileage.toLocaleString()} mi</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Registration Expiry</dt>
                      <dd className="mt-1 text-gray-900 flex items-center gap-1">
                        <Calendar className="w-4 h-4 text-gray-400" />
                        {formatDate(vehicle.registrationExpiry)}
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
                      <dt className="text-sm font-medium text-gray-500">Linked Policy</dt>
                      <dd className="mt-1 text-gray-900">{vehicle.policyId}</dd>
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
                                <span className="font-medium text-gray-900">{claim.claimNumber}</span>
                                <StatusBadge status={claim.status} />
                                <span className="text-sm text-gray-500">{formatDate(claim.incidentDate)}</span>
                              </div>
                              <p className="text-sm text-gray-600 mt-1">{claim.incidentType} • {claim.incidentSeverity}</p>
                              <p className="text-sm text-gray-500 mt-0.5">{claim.location}</p>
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
                              <span className="font-medium text-gray-900">{claim.claimNumber}</span>
                              <StatusBadge status={claim.status} />
                              <span className="text-sm text-gray-500">{formatDate(claim.incidentDate)}</span>
                            </div>
                            <p className="text-sm text-gray-600 mt-1">{claim.incidentType} • {claim.incidentSeverity}</p>
                            <p className="text-sm text-gray-500 mt-0.5">{claim.location}</p>
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
              <CardHeader title="Documents" action={<Button variant="outline" size="sm">Upload</Button>} />
              <CardContent>
                {vehicle.documents.length > 0 ? (
                  <div className="space-y-3">
                    {vehicle.documents.map((doc, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                            <FileText className="w-5 h-5 text-primary" />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{doc.name}</p>
                            <p className="text-sm text-gray-500">{doc.type} • {formatDate(doc.uploadedAt)}</p>
                          </div>
                        </div>
                        <Button variant="ghost" size="sm">View</Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={<FileText className="w-12 h-12" />}
                    title="No documents uploaded"
                    description="Vehicle documents will appear here once uploaded."
                    action={<Button variant="outline" size="sm">Upload Document</Button>}
                  />
                )}
              </CardContent>
            </Card>
          )}

          {activeTab === 'maintenance' && (
            <Card>
              <CardHeader title="Maintenance Records" action={<Button variant="outline" size="sm">Add Record</Button>} />
              <CardContent>
                <EmptyState
                  icon={<Wrench className="w-12 h-12" />}
                  title="No maintenance records"
                  description="Maintenance records will appear here once added."
                  action={<Button variant="outline" size="sm">Add Maintenance Record</Button>}
                />
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Quick Actions" />
            <CardContent>
              <div className="space-y-3">
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
                <Button variant="outline" className="w-full justify-start gap-3">
                  <Calendar className="w-4 h-4" />
                  Registration Reminder
                </Button>
                <Button variant="outline" className="w-full justify-start gap-3">
                  <Gauge className="w-4 h-4" />
                  Schedule Inspection
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Vehicle Status" />
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    </div>
                    <span className="text-sm font-medium text-gray-900">Active Policy</span>
                  </div>
                  <Badge variant="success">Active</Badge>
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <Calendar className="w-4 h-4 text-blue-500" />
                    </div>
                    <span className="text-sm font-medium text-gray-900">Registration Valid</span>
                  </div>
                  <span className="text-sm text-gray-600">Expires {formatDate(vehicle.registrationExpiry)}</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                      <Gauge className="w-4 h-4 text-purple-500" />
                    </div>
                    <span className="text-sm font-medium text-gray-900">Last Inspection</span>
                  </div>
                  <span className="text-sm text-gray-600">Not recorded</span>
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
                  <span className="font-semibold text-gray-900">{formatCurrency(vehicleClaims.reduce((sum, c) => sum + c.claimAmount, 0))}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Vehicle Age</span>
                  <span className="font-semibold text-gray-900">{new Date().getFullYear() - vehicle.year} years</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Mileage</span>
                  <span className="font-semibold text-gray-900">{vehicle.currentMileage.toLocaleString()} mi</span>
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