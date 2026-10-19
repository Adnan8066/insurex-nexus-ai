import { useCallback, useEffect, useState } from 'react'
import { UserPlus, Users, RefreshCw } from 'lucide-react'
import { adminUserService } from '../../services'
import { Button } from '../../components/ui/Button'
import { Card, CardContent, CardHeader } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Input, Select } from '../../components/forms/FormFields'

const initialForm = {
  first_name: '',
  last_name: '',
  email: '',
  role: 'customer',
  phone: '',
  department: '',
  password: '',
  password_confirm: '',
}

const roleLabels = {
  customer: 'Customer',
  investigator: 'Investigator',
  employee: 'Insurance Employee',
  repair: 'Repair Shop',
}

const roleOptions = Object.entries(roleLabels).map(([value, label]) => ({ value, label }))

export function UserManagement() {
  const [users, setUsers] = useState([])
  const [form, setForm] = useState(initialForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const loadUsers = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setUsers(await adminUserService.getUsers())
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load users. Confirm you are signed in as an administrator.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadUsers() }, [loadUsers])

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    setError('')
    setSuccess('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      const created = await adminUserService.createUser(form)
      setSuccess(`${created.first_name} ${created.last_name} (${created.email}) was created as ${roleLabels[created.role]}.`)
      setForm(initialForm)
      await loadUsers()
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.error?.message || 'Could not create this account.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page mx-auto max-w-6xl space-y-6">
      <div className="page-header">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-blue-50 p-3 text-blue-700"><Users className="h-6 w-6" /></div>
          <div>
            <h1 className="page-title">User Management</h1>
            <p className="page-subtitle">Create customer, investigator, employee, and repair shop accounts.</p>
          </div>
        </div>
      </div>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</div>}
      {success && <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800" role="status">{success}</div>}

      <Card>
        <CardHeader title="Create an Account" subtitle="Administrators can assign one of the supported operational roles." />
        <CardContent>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Input label="First name" name="first_name" value={form.first_name} onChange={handleChange} required />
            <Input label="Last name" name="last_name" value={form.last_name} onChange={handleChange} />
            <Input label="Email" name="email" type="email" autoComplete="email" value={form.email} onChange={handleChange} required />
            <Select label="Role" name="role" value={form.role} onChange={handleChange} options={roleOptions} required />
            {form.role === 'repair' && <p className="md:col-span-2 -mt-2 text-sm text-amber-800">Use the same email address registered on the repair shop record so the account can access jobs assigned to that shop.</p>}
            <Input label="Phone (optional)" name="phone" type="tel" value={form.phone} onChange={handleChange} />
            {form.role !== 'customer' && <Input label="Department (optional)" name="department" value={form.department} onChange={handleChange} />}
            <Input label="Initial password" name="password" type="password" autoComplete="new-password" value={form.password} onChange={handleChange} hint="Use a strong password that meets the account security rules." required />
            <Input label="Confirm password" name="password_confirm" type="password" autoComplete="new-password" value={form.password_confirm} onChange={handleChange} required />
            <div className="md:col-span-2 flex flex-col gap-3 border-t border-gray-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="max-w-2xl text-sm text-gray-500">Share the initial password securely. Users can change it after signing in.</p>
              <Button type="submit" disabled={saving}>
                <UserPlus className="mr-2 h-4 w-4" />{saving ? 'Creating…' : 'Create account'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader
          title="Managed Accounts"
          subtitle={`${users.length} managed account${users.length === 1 ? '' : 's'}`}
          action={<Button variant="outline" size="sm" onClick={loadUsers} disabled={loading}><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>}
        />
        <CardContent>
          {loading ? <p className="py-8 text-center text-sm text-gray-500">Loading accounts…</p> : users.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-500">No managed accounts yet. Create one above.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead><tr className="border-b border-gray-200 text-gray-500"><th className="py-3 pr-4 font-medium">Name</th><th className="py-3 pr-4 font-medium">Email</th><th className="py-3 pr-4 font-medium">Role</th><th className="py-3 pr-4 font-medium">Department</th><th className="py-3 font-medium">Status</th></tr></thead>
                <tbody className="divide-y divide-gray-100">
                  {users.map((account) => (
                    <tr key={account.id}>
                      <td className="py-3 pr-4 font-medium text-gray-900">{account.full_name || account.name}</td>
                      <td className="py-3 pr-4 text-gray-600">{account.email}</td>
                      <td className="py-3 pr-4"><Badge variant="info">{roleLabels[account.role] || account.role}</Badge></td>
                      <td className="py-3 pr-4 text-gray-600">{account.department || '—'}</td>
                      <td className="py-3"><Badge variant={account.is_active ? 'success' : 'neutral'}>{account.is_active ? 'Active' : 'Inactive'}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default UserManagement
