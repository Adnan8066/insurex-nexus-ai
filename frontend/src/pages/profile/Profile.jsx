import { useState } from 'react'
import {
  User,
  Mail,
  Phone,
  Shield,
  Building,
  Key,
  CheckCircle2,
  AlertCircle,
  Save,
  Lock,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/forms/FormFields'

export function Profile() {
  const { user, updateProfile, changePassword } = useAuth()

  const [formData, setFormData] = useState({
    name: user?.name || 'John Anderson',
    email: user?.email || 'customer@demo.com',
    phone: user?.phone || '+1 (555) 123-4567',
    department: user?.department || 'Policyholder',
  })

  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  })

  const [savingProfile, setSavingProfile] = useState(false)
  const [profileSuccess, setProfileSuccess] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')
  const [passwordError, setPasswordError] = useState('')

  const handleProfileChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setSavingProfile(true)
    setProfileSuccess('')
    const res = await updateProfile(formData)
    setSavingProfile(false)
    if (res.success) {
      setProfileSuccess('Profile details updated successfully.')
      setTimeout(() => setProfileSuccess(''), 3000)
    }
  }

  const handlePasswordSubmit = async (e) => {
    e.preventDefault()
    setPasswordError('')
    setPasswordSuccess('')

    if (passwordData.newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters long.')
      return
    }
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setPasswordError('New passwords do not match.')
      return
    }

    const res = await changePassword(passwordData)
    if (res.success) {
      setPasswordSuccess('Password changed successfully.')
      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' })
      setTimeout(() => setPasswordSuccess(''), 3000)
    } else {
      setPasswordError(res.error || 'Failed to update password')
    }
  }

  return (
    <div className="page max-w-4xl mx-auto space-y-6">
      <div className="page-header">
        <h1 className="page-title">User Profile & Account</h1>
        <p className="page-subtitle">Manage your personal credentials, contact information, and security settings</p>
      </div>

      {/* User Overview Card */}
      <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm flex items-center gap-5">
        <div className="w-16 h-16 rounded-2xl bg-primary text-white flex items-center justify-center font-bold text-2xl shadow-md">
          {user?.name ? user.name.split(' ').map((n) => n[0]).join('') : 'U'}
        </div>
        <div>
          <h2 className="text-xl font-bold text-gray-900">{user?.name || 'User'}</h2>
          <p className="text-sm text-gray-500">{user?.email}</p>
          <div className="flex gap-2 mt-2">
            <span className="text-xs uppercase font-bold bg-primary/10 text-primary px-2.5 py-0.5 rounded-full">
              {user?.role || 'Customer'}
            </span>
            <span className="text-xs bg-gray-100 text-gray-700 px-2.5 py-0.5 rounded-full font-medium">
              {user?.department || 'Policyholder'}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Profile Information */}
        <Card>
          <CardHeader title="Personal Information" />
          <CardContent className="p-6">
            <form onSubmit={handleSaveProfile} className="space-y-4">
              {profileSuccess && (
                <div className="p-3 bg-emerald-50 text-emerald-800 rounded-lg text-xs font-medium flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  {profileSuccess}
                </div>
              )}

              <Input
                label="Full Name"
                name="name"
                value={formData.name}
                onChange={handleProfileChange}
                required
              />

              <Input
                label="Email Address"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleProfileChange}
                required
              />

              <Input
                label="Phone Number"
                name="phone"
                value={formData.phone}
                onChange={handleProfileChange}
              />

              <Input
                label="Department / Unit"
                name="department"
                value={formData.department}
                onChange={handleProfileChange}
              />

              <Button type="submit" variant="primary" loading={savingProfile}>
                <Save className="w-4 h-4 mr-2" />
                Save Profile
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Change Password */}
        <Card>
          <CardHeader title="Security & Password" />
          <CardContent className="p-6">
            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              {passwordSuccess && (
                <div className="p-3 bg-emerald-50 text-emerald-800 rounded-lg text-xs font-medium flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  {passwordSuccess}
                </div>
              )}
              {passwordError && (
                <div className="p-3 bg-red-50 text-red-800 rounded-lg text-xs font-medium flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {passwordError}
                </div>
              )}

              <Input
                label="Current Password"
                type="password"
                placeholder="••••••••"
                value={passwordData.currentPassword}
                onChange={(e) => setPasswordData({ ...passwordData, currentPassword: e.target.value })}
                required
              />

              <Input
                label="New Password"
                type="password"
                placeholder="At least 8 characters"
                value={passwordData.newPassword}
                onChange={(e) => setPasswordData({ ...passwordData, newPassword: e.target.value })}
                required
              />

              <Input
                label="Confirm New Password"
                type="password"
                placeholder="Re-enter new password"
                value={passwordData.confirmPassword}
                onChange={(e) => setPasswordData({ ...passwordData, confirmPassword: e.target.value })}
                required
              />

              <Button type="submit" variant="secondary">
                <Lock className="w-4 h-4 mr-2" />
                Change Password
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default Profile
