import { useState, useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Car, Save, X } from 'lucide-react'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'
import { vehicleService } from '../../services'
import { useAuth } from '../../context/AuthContext'

export function VehicleForm() {
  const navigate = useNavigate()
  const { id } = useParams()
  const { user } = useAuth()
  const isEdit = !!id

  const [formData, setFormData] = useState({
    make: '',
    model: '',
    year: new Date().getFullYear(),
    vin: '',
    licensePlate: '',
    licenseState: '',
    color: '',
    fuelType: 'gasoline',
    transmission: 'automatic',
    currentMileage: '',
    registrationExpiry: '',
    purchaseDate: '',
    purchasePrice: '',
    status: 'active',
    customer: user?.id || '',
    policy: '',
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Convert camelCase to snake_case for backend
  const toSnakeCase = (data) => {
    const result = {}
    for (const [key, value] of Object.entries(data)) {
      const snakeKey = key.replace(/([A-Z])/g, "_$1").toLowerCase()
      result[snakeKey] = value
    }
    return result
  }

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const payload = toSnakeCase(formData)
      if (isEdit) {
        await vehicleService.updateVehicle(id, payload)
      } else {
        await vehicleService.createVehicle(payload)
      }
      navigate('/vehicles')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save vehicle')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className='page max-w-3xl'>
      <div className='page-header'>
        <div>
          <Link to='/vehicles' className='inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-2'>
            <ArrowLeft className='w-4 h-4' />
            Back to Vehicles
          </Link>
          <h1 className='page-title'>{isEdit ? 'Edit Vehicle' : 'Add Vehicle'}</h1>
          <p className='page-subtitle'>{isEdit ? 'Update vehicle information' : 'Register a new insured vehicle'}</p>
        </div>
      </div>

      {error && (
        <div className='mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm'>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className='space-y-6'>
        <div className='card'>
          <div className='card-header'><h3 className='card-title'>Vehicle Information</h3></div>
          <div className='card-content grid grid-cols-1 md:grid-cols-2 gap-4'>
            <Input label='Make' name='make' value={formData.make} onChange={handleChange} placeholder='e.g., Toyota' required />
            <Input label='Model' name='model' value={formData.model} onChange={handleChange} placeholder='e.g., Camry' required />
            <Input label='Year' name='year' type='number' value={formData.year} onChange={handleChange} required />
            <Input label='VIN' name='vin' value={formData.vin} onChange={handleChange} placeholder='17-character VIN' required />
            <Input label='License Plate' name='licensePlate' value={formData.licensePlate} onChange={handleChange} required />
            <Input label='License State' name='licenseState' value={formData.licenseState} onChange={handleChange} placeholder='e.g., CA' required />
            <Input label='Color' name='color' value={formData.color} onChange={handleChange} required />
            <Select label='Fuel Type' name='fuelType' value={formData.fuelType} onChange={handleChange}
              options={[{value:'gasoline',label:'Gasoline'},{value:'diesel',label:'Diesel'},{value:'hybrid',label:'Hybrid'},{value:'electric',label:'Electric'}]} />
            <Select label='Transmission' name='transmission' value={formData.transmission} onChange={handleChange}
              options={[{value:'automatic',label:'Automatic'},{value:'manual',label:'Manual'},{value:'cvt',label:'CVT'}]} />
            <Input label='Current Mileage' name='currentMileage' type='number' value={formData.currentMileage} onChange={handleChange} />
            <Input label='Registration Expiry' name='registrationExpiry' type='date' value={formData.registrationExpiry} onChange={handleChange} />
            <Input label='Purchase Date' name='purchaseDate' type='date' value={formData.purchaseDate} onChange={handleChange} />
            <Input label='Purchase Price' name='purchasePrice' type='number' value={formData.purchasePrice} onChange={handleChange} />
            <Select label='Status' name='status' value={formData.status} onChange={handleChange}
              options={[{value:'active',label:'Active'},{value:'inactive',label:'Inactive'},{value:'sold',label:'Sold'},{value:'total_loss',label:'Total Loss'}]} />
          </div>
        </div>

        <div className='flex items-center justify-end gap-3'>
          <Link to='/vehicles'><Button variant='ghost'>Cancel</Button></Link>
          <Button type='submit' disabled={loading}>
            <Save className='w-4 h-4 mr-2' />
            {loading ? 'Saving...' : 'Save Vehicle'}
          </Button>
        </div>
      </form>
    </div>
  )
}

export default VehicleForm


