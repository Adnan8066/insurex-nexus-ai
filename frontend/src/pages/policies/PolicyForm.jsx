import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, FileText, Save, X, Car, Home, Building2 } from 'lucide-react'
import { Button } from '../../components/ui/Button'
import { Input, Select, Textarea } from '../../components/forms/FormFields'
import { policyService } from '../../services'
import { useAuth } from '../../context/AuthContext'

const typeMap = {
  'Comprehensive Auto': 'auto_comprehensive',
  'Collision Auto': 'auto_collision',
  'Liability Auto': 'auto_liability',
  'Homeowners': 'homeowners',
  'Renters': 'renters',
  'Umbrella': 'umbrella',
}

const frequencyMap = {
  'annual': 'annual',
  'semi-annual': 'semi_annual',
  'quarterly': 'quarterly',
  'monthly': 'monthly',
}

export function PolicyForm() {
  const navigate = useNavigate()
  const { id } = useParams()
  const isEdit = !!id
  const { user } = useAuth()

  const [formData, setFormData] = useState({
    type: 'Comprehensive Auto',
    status: 'active',
    startDate: new Date().toISOString().split('T')[0],
    endDate: new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toISOString().split('T')[0],
    premium: '',
    deductible: '500',
    paymentFrequency: 'annual',
    autoRenew: true,
    agent: '',
    propertyAddress: '',
    propertyType: '',
    propertyYearBuilt: '',
    propertySquareFootage: '',
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData({ ...formData, [name]: type === 'checkbox' ? checked : value })
  }

  const buildPayload = () => {
    const payload = {
      customer: user?.id || null,
      agent: null,
      type: typeMap[formData.type] || 'auto_comprehensive',
      status: formData.status,
      start_date: formData.startDate,
      end_date: formData.endDate,
      premium: Number(formData.premium),
      deductible: Number(formData.deductible),
      payment_frequency: frequencyMap[formData.paymentFrequency] || 'annual',
      auto_renew: formData.autoRenew,
      property_address: formData.propertyAddress || '',
      property_type: formData.propertyType || '',
      property_year_built: Number(formData.propertyYearBuilt) || null,
      property_square_footage: Number(formData.propertySquareFootage) || null,
    }
    return payload
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const payload = buildPayload()
      if (isEdit) {
        await policyService.updatePolicy(id, payload)
      } else {
        await policyService.createPolicy(payload)
      }
      navigate('/policies')
    } catch (err) {
      const details = err.response?.data
      if (details && typeof details === 'object') {
        const messages = Object.entries(details)
          .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
          .join('; ')
        setError(messages || 'Failed to save policy')
      } else {
        setError(err.response?.data?.detail || err.response?.data?.error?.message || 'Failed to save policy')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page max-w-3xl">
      <div className="page-header">
        <div>
          <Link to="/policies" className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-2">
            <ArrowLeft className="w-4 h-4" />
            Back to Policies
          </Link>
          <h1 className="page-title">{isEdit ? 'Edit Policy' : 'Create Policy'}</h1>
          <p className="page-subtitle">{isEdit ? 'Update policy details' : 'Issue a new insurance policy'}</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="card">
          <div className="card-header"><h3 className="card-title">Policy Details</h3></div>
          <div className="card-content grid grid-cols-1 md:grid-cols-2 gap-4">
            <Select label="Policy Type" name="type" value={formData.type} onChange={handleChange}
              options={[
                {value:'Comprehensive Auto',label:'Comprehensive Auto'},
                {value:'Collision Auto',label:'Collision Auto'},
                {value:'Liability Auto',label:'Liability Auto'},
                {value:'Homeowners',label:'Homeowners'},
                {value:'Renters',label:'Renters'},
                {value:'Umbrella',label:'Umbrella'},
              ]} />
            <Select label="Status" name="status" value={formData.status} onChange={handleChange}
              options={[{value:'active',label:'Active'},{value:'pending',label:'Pending'},{value:'expired',label:'Expired'},{value:'cancelled',label:'Cancelled'}]} />
            <Input label="Start Date" name="startDate" type="date" value={formData.startDate} onChange={handleChange} required />
            <Input label="End Date" name="endDate" type="date" value={formData.endDate} onChange={handleChange} required />
            <Input label="Annual Premium" name="premium" type="number" value={formData.premium} onChange={handleChange} placeholder="e.g., 1250" required />
            <Input label="Deductible" name="deductible" type="number" value={formData.deductible} onChange={handleChange} placeholder="e.g., 500" required />
            <Select label="Payment Frequency" name="paymentFrequency" value={formData.paymentFrequency} onChange={handleChange}
              options={[{value:'annual',label:'Annual'},{value:'semi-annual',label:'Semi-Annual'},{value:'quarterly',label:'Quarterly'},{value:'monthly',label:'Monthly'}]} />
            <div className="flex items-center gap-2">
              <input type="checkbox" id="autoRenew" name="autoRenew" checked={formData.autoRenew} onChange={handleChange} className="w-4 h-4" />
              <label htmlFor="autoRenew" className="text-sm text-gray-700">Auto Renew</label>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><h3 className="card-title">Property Details (if applicable)</h3></div>
          <div className="card-content grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input label="Property Address" name="propertyAddress" value={formData.propertyAddress} onChange={handleChange} placeholder="Street address" />
            <Input label="Property Type" name="propertyType" value={formData.propertyType} onChange={handleChange} placeholder="e.g., Single Family" />
            <Input label="Year Built" name="propertyYearBuilt" type="number" value={formData.propertyYearBuilt} onChange={handleChange} />
            <Input label="Square Footage" name="propertySquareFootage" type="number" value={formData.propertySquareFootage} onChange={handleChange} />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3">
          <Link to="/policies"><Button variant="ghost">Cancel</Button></Link>
          <Button type="submit" disabled={loading}>
            <Save className="w-4 h-4 mr-2" />
            {loading ? 'Saving...' : 'Save Policy'}
          </Button>
        </div>
      </form>
    </div>
  )
}

export default PolicyForm