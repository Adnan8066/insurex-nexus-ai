import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Car, Save, X } from 'lucide-react'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'
import { vehicleService } from '../../services'

export function VehicleForm() {
  const navigate = useNavigate()
  const { id } = useParams()
  const isEdit = !!id

  const [formData, setFormData] = useState({
    make: '',
    model: '',
    year: new Date().getFullYear(),
    vin: '',
    licensePlate: '',
    color: '',
    fuelType: 'Gasoline',
    transmission: 'Automatic',
    currentMileage: '',
    registrationExpiry: '',
    purchaseDate: '',
    purchasePrice: '',
    status: 'active',
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      if (isEdit) {
        await vehicleService.updateVehicle(id, formData)
      } else {
        await vehicleService.createVehicle(formData)
      }
      navigate('/vehicles')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save vehicle')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page max-w-3xl">
      <div className="page-header">
        <div>
          <Link to="/vehicles" className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-2">
            <ArrowLeft className="w-4 h-4" />
            Back to Vehicles
          </Link>
          <h1 className="page-title">{isEdit ? 'Edit Vehicle' : 'Add Vehicle'}</h1>
          <p className="page-subtitle">{isEdit ? 'Update vehicle information' : 'Register a new insured vehicle'}</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="card">
          <div className="card-header"><h3 className="card-title">Vehicle Information</h3></div>
          <div className="card-content grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input label="Make" name="make" value={formData.make} onChange={handleChange} placeholder="e.g., Toyota" required />
            <Input label="Model" name="model" value={formData.model} onChange={handleChange} placeholder="e.g., Camry" required />
            <Input label="Year" name="year" type="number" value={formData.year} onChange={handleChange} required />
            <Input label="VIN" name="vin" value={formData.vin} onChange={handleChange} placeholder="17-character VIN" required />
            <Input label="License Plate" name="licensePlate" value={formData.licensePlate} onChange={handleChange} required />
            <Input label="Color" name="color" value={formData.color} onChange={handleChange} required />
            <Select label="Fuel Type" name="fuelType" value={formData.fuelType} onChange={handleChange}
              options={[{value:'Gasoline',label:'Gasoline'},{value:'Diesel',label:'Diesel'},{value:'Hybrid',label:'Hybrid'},{value:'Electric',label:'Electric'}]} />
            <Select label="Transmission" name="transmission" value={formData.transmission} onChange={handleChange}
              options={[{value:'Automatic',label:'Automatic'},{value:'Manual',label:'Manual'},{value:'CVT',label:'CVT'}]} />
            <Input label="Current Mileage" name="currentMileage" type="number" value={formData.currentMileage} onChange={handleChange} />
            <Input label="Registration Expiry" name="registrationExpiry" type="date" value={formData.registrationExpiry} onChange={handleChange} />
            <Input label="Purchase Date" name="purchaseDate" type="date" value={formData.purchaseDate} onChange={handleChange} />
            <Input label="Purchase Price" name="purchasePrice" type="number" value={formData.purchasePrice} onChange={handleChange} />
            <Select label="Status" name="status" value={formData.status} onChange={handleChange}
              options={[{value:'active',label:'Active'},{value:'inactive',label:'Inactive'},{value:'sold',label:'Sold'},{value:'totaled',label:'Totaled'}]} />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3">
          <Link to="/vehicles"><Button variant="ghost">Cancel</Button></Link>
          <Button type="submit" disabled={loading}>
            <Save className="w-4 h-4 mr-2" />
            {loading ? 'Saving...' : 'Save Vehicle'}
          </Button>
        </div>
      </form>
    </div>
  )
}

export default VehicleForm