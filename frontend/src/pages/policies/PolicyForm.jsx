import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, FileText, Save, X, Car, Home, Building2 } from 'lucide-react'
import { Button } from '../../components/ui/Button'
import { Input, Select, Textarea } from '../../components/forms/FormFields'
import { policyService } from '../../services'

export function PolicyForm() {
  const navigate = useNavigate()
  const { id } = useParams()
  const isEdit = !!id

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
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData({ ...formData, [name]: type === 'checked' ? checked : value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      if (isEdit) {
        await policyService.updatePolicy(id, formData)
      } else {
        await policyService.createPolicy(formData)
      }
      navigate('/policies')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save policy')
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
                {value:'Liability Only',label:'Liability Only'},
                {value:'Homeowners',label:'Homeowners'},
                {value:'Renters',label:'Renters'},
                {value:'Life Insurance',label:'Life Insurance'},
                {value:'Commercial',label:'Commercial'},
              ]} />
            <Select label="Status" name="status" value={formData.status} onChange={handleChange}
              options={[{value:'active',label:'Active'},{value:'pending',label:'Pending'},{value:'expired',label:'Expired'},{value:'cancelled',label:'Cancelled'}]} />
            <Input label="Start Date" name="startDate" type="date" value={formData.startDate} onChange={handleChange} required />
            <Input label="End Date" name="endDate" type="date" value={formData.endDate} onChange={handleChange} required />
            <Input label="Annual Premium" name="premium" type="number" value={formData.premium} onChange={handleChange} placeholder="e.g., 1250" required />
            <Input label="Deductible" name="deductible" type="number" value={formData.deductible} onChange={handleChange} placeholder="e.g., 500" required />
            <Select label="Payment Frequency" name="paymentFrequency" value={formData.paymentFrequency} onChange={handleChange}
              options={[{value:'annual',label:'Annual'},{value:'semi-annual',label:'Semi-Annual'},{value:'quarterly',label:'Quarterly'},{value:'monthly',label:'Monthly'}]} />
            <Input label="Agent" name="agent" value={formData.agent} onChange={handleChange} placeholder="Agent name" />
            <div className="flex items-center gap-2">
              <input type="checkbox" id="autoRenew" name="autoRenew" checked={formData.autoRenew} onChange={handleChange} className="w-4 h-4" />
              <label htmlFor="autoRenew" className="text-sm text-gray-700">Auto Renew</label>
            </div>
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