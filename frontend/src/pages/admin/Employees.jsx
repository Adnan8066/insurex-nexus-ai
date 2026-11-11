import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Briefcase, Users } from 'lucide-react'
import { workforceService } from '../../services'
import { formatApiError } from '../../services/api'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardContent, CardHeader } from '../../components/ui/Card'

export function Employees() {
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadEmployees = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setEmployees(await workforceService.getEmployees())
    } catch (err) {
      setError(formatApiError(err, 'Could not load employee profiles.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadEmployees() }, [loadEmployees])

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-blue-50 p-3 text-blue-700"><Users className="h-6 w-6" /></div>
        <div><h1 className="text-2xl font-bold text-gray-900">Employee Workforce</h1><p className="text-sm text-gray-500">Profiles, capacity, skills, and assignment eligibility</p></div>
      </div>
      <Card>
        <CardHeader title="Claims Adjusters" subtitle={`${employees.length} employee${employees.length === 1 ? '' : 's'}`} action={<Button variant="ghost" onClick={loadEmployees}>Refresh</Button>} />
        <CardContent>
          {error && <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}
          {loading ? <p className="py-8 text-center text-gray-500">Loading employee profiles…</p>
            : employees.length === 0 ? <p className="py-8 text-center text-gray-500">No employee accounts are available.</p>
              : <div className="divide-y divide-gray-100">
                {employees.map((employee) => (
                  <div key={employee.id} className="flex flex-col gap-4 py-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-3">
                      {employee.avatar ? <img src={employee.avatar} alt="" className="h-11 w-11 rounded-full object-cover" /> : <div className="rounded-full bg-gray-100 p-3 text-gray-500"><Briefcase className="h-5 w-5" /></div>}
                      <div><p className="font-semibold text-gray-900">{employee.name}</p><p className="text-sm text-gray-500">Employee #{employee.employee_id} · {employee.designation || 'Designation not set'} · {employee.department || 'Department not set'}</p></div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant={employee.employment_status === 'active' ? 'success' : 'neutral'}>{employee.employment_status}</Badge>
                      <Badge variant={employee.assignment_eligible ? 'success' : 'warning'}>{employee.assignment_eligible ? 'Eligible' : 'Unavailable'}</Badge>
                      <Button variant="secondary" size="sm" asChild><Link to={`/employees/${employee.id}`}>Profile <ArrowRight className="ml-2 h-4 w-4" /></Link></Button>
                    </div>
                  </div>
                ))}
              </div>}
        </CardContent>
      </Card>
    </div>
  )
}
