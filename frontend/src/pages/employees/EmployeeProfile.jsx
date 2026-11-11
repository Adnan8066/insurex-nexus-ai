import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Activity, BriefcaseBusiness, Clock3, Gauge, Save, UserRound } from 'lucide-react'
import { workforceService } from '../../services'
import { formatApiError } from '../../services/api'
import { useAuth } from '../../context/useAuth'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardContent, CardHeader } from '../../components/ui/Card'
import { Input } from '../../components/forms/FormFields'

const AVAILABILITY = ['available', 'busy', 'on_leave', 'off_duty', 'temporarily_unavailable']
const LEVELS = ['beginner', 'intermediate', 'advanced', 'expert']
const DAYS = [['mon', 'Mon'], ['tue', 'Tue'], ['wed', 'Wed'], ['thu', 'Thu'], ['fri', 'Fri'], ['sat', 'Sat'], ['sun', 'Sun']]

function Stat({ icon: Icon, label, value, suffix = '' }) {
  return <Card><CardContent className="flex items-start gap-3 p-5"><div className="rounded-lg bg-blue-50 p-2 text-blue-700"><Icon className="h-5 w-5" /></div><div><p className="text-sm text-gray-500">{label}</p><p className="mt-1 text-2xl font-semibold text-gray-900">{value ?? '—'}{value != null ? suffix : ''}</p></div></CardContent></Card>
}

export function EmployeeProfile() {
  const { id } = useParams()
  const { user } = useAuth()
  const employeeId = id || user?.id
  const canEdit = user?.role === 'admin'
  const canEditSkills = canEdit || (user?.role === 'employee' && String(employeeId) === String(user?.id))
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const loadProfile = useCallback(async () => {
    if (!employeeId) return
    setLoading(true)
    setError('')
    try {
      const result = await workforceService.getEmployeeProfile(employeeId)
      setProfile(result)
      setForm({
        first_name: result.first_name || '', last_name: result.last_name || '', department: result.department || '', is_active: result.is_active,
        designation: result.designation || '', primary_specialization: result.primary_specialization || '',
        secondary_specialization: result.secondary_specialization || '', years_of_experience: result.years_of_experience ?? 0,
        max_claim_capacity: result.max_claim_capacity ?? 10, skill_tier: result.skill_tier ?? 3,
        availability_status: result.availability_status || 'available', working_days: result.working_days || [],
        shift_start_time: result.shift_start_time?.slice(0, 5) || '', shift_end_time: result.shift_end_time?.slice(0, 5) || '',
        leave_status: result.leave_status || '', skills: result.skills || [],
      })
    } catch (err) {
      setError(formatApiError(err, 'Could not load this employee profile.'))
    } finally {
      setLoading(false)
    }
  }, [employeeId])

  useEffect(() => { loadProfile() }, [loadProfile])

  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))
  const utilization = useMemo(() => profile?.capacity_utilization ?? 0, [profile])
  const addSkill = () => update('skills', [...(form?.skills || []), { name: '', level: 'beginner' }])
  const setSkill = (index, key, value) => update('skills', form.skills.map((skill, i) => i === index ? { ...skill, [key]: value } : skill))
  const removeSkill = (index) => update('skills', form.skills.filter((_, i) => i !== index))
  const cleanSkills = () => form.skills.filter((skill) => skill.name.trim()).map(({ name, level }) => ({ name: name.trim(), level }))

  const save = async (event) => {
    event.preventDefault()
    setSaving(true); setError(''); setSuccess('')
    try {
      const saved = await workforceService.updateEmployeeProfile(employeeId, { ...form, skills: cleanSkills() })
      setProfile(saved); setSuccess('Employee profile updated.')
    } catch (err) { setError(formatApiError(err, 'Could not save the employee profile.')) }
    finally { setSaving(false) }
  }

  const saveSkills = async () => {
    setSaving(true); setError(''); setSuccess('')
    try {
      const saved = await workforceService.updateEmployeeProfile(employeeId, { skills: cleanSkills() })
      setProfile(saved); setSuccess('Your expertise was updated.')
    } catch (err) { setError(formatApiError(err, 'Could not save your expertise.')) }
    finally { setSaving(false) }
  }

  if (loading) return <div className="mx-auto max-w-6xl p-8 text-center text-gray-500">Loading employee profile…</div>
  if (!profile) return <div className="mx-auto max-w-6xl p-8"><p className="text-red-700" role="alert">{error || 'Employee profile not found.'}</p></div>

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <Card><CardContent className="flex flex-col gap-5 p-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">{profile.avatar ? <img src={profile.avatar} alt="" className="h-16 w-16 rounded-full object-cover" /> : <div className="rounded-full bg-blue-50 p-4 text-blue-700"><UserRound className="h-8 w-8" /></div>}
          <div><h1 className="text-2xl font-bold text-gray-900">{profile.name}</h1><p className="text-sm text-gray-500">Employee #{profile.employee_id} · {profile.designation || 'Designation not set'} · {profile.role}</p><p className="mt-2 flex flex-wrap gap-2"><Badge variant={profile.employment_status === 'active' ? 'success' : 'neutral'}>{profile.employment_status}</Badge><Badge variant={profile.assignment_eligible ? 'success' : 'warning'}>{profile.availability_status.replaceAll('_', ' ')}</Badge></p></div>
        </div><p className="text-sm text-gray-500">{profile.department || 'Department not set'} · {profile.years_of_experience} years experience</p>
      </CardContent></Card>
      {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}{success && <p className="rounded-lg bg-green-50 p-3 text-sm text-green-700" role="status">{success}</p>}

      {canEdit && form && <form onSubmit={save} className="space-y-6"><Card><CardHeader title="Professional and availability settings" subtitle="Administrators can update employee expertise and assignment settings." /><CardContent className="grid gap-4 p-6 sm:grid-cols-2 lg:grid-cols-3">
        <Input label="First name" value={form.first_name} onChange={(e) => update('first_name', e.target.value)} />
        <Input label="Last name" value={form.last_name} onChange={(e) => update('last_name', e.target.value)} />
        <Input label="Department" value={form.department} onChange={(e) => update('department', e.target.value)} />
        <Input label="Designation" value={form.designation} onChange={(e) => update('designation', e.target.value)} />
        <Input label="Primary specialization" placeholder="e.g. collision" value={form.primary_specialization} onChange={(e) => update('primary_specialization', e.target.value)} />
        <Input label="Secondary specialization" placeholder="e.g. glass" value={form.secondary_specialization} onChange={(e) => update('secondary_specialization', e.target.value)} />
        <Input label="Years of experience" type="number" min="0" max="60" value={form.years_of_experience} onChange={(e) => update('years_of_experience', Number(e.target.value))} />
        <Input label="Maximum active claims" type="number" min="1" value={form.max_claim_capacity} onChange={(e) => update('max_claim_capacity', Number(e.target.value))} />
        <label className="input-group"><span className="input-label">Availability</span><select className="input-field" value={form.availability_status} onChange={(e) => update('availability_status', e.target.value)}>{AVAILABILITY.map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select></label>
        <Input label="Shift starts" type="time" value={form.shift_start_time} onChange={(e) => update('shift_start_time', e.target.value)} />
        <Input label="Shift ends" type="time" value={form.shift_end_time} onChange={(e) => update('shift_end_time', e.target.value)} />
        <Input label="Leave status" value={form.leave_status} onChange={(e) => update('leave_status', e.target.value)} />
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_active} onChange={(e) => update('is_active', e.target.checked)} />Employment active</label>
        <div className="sm:col-span-2 lg:col-span-3"><p className="input-label mb-2">Working days</p><div className="flex flex-wrap gap-3">{DAYS.map(([day, label]) => <label key={day} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.working_days.includes(day)} onChange={(e) => update('working_days', e.target.checked ? [...form.working_days, day] : form.working_days.filter((item) => item !== day))} />{label}</label>)}</div></div>
        <div className="sm:col-span-2 lg:col-span-3"><h3 className="font-semibold">RL skill tier</h3><select className="input-field mt-2 max-w-xs" value={form.skill_tier} onChange={(e) => update('skill_tier', Number(e.target.value))}>{[1, 2, 3, 4, 5].map((tier) => <option key={tier} value={tier}>Tier {tier}</option>)}</select></div>
        <div className="sm:col-span-2 lg:col-span-3"><Button type="submit" loading={saving} disabled={saving}><Save className="mr-2 h-4 w-4" />Save profile</Button></div>
      </CardContent></Card></form>}

      <section><h2 className="mb-3 text-lg font-semibold text-gray-900">Workload overview</h2><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Stat icon={BriefcaseBusiness} label="Active claims" value={profile.active_claims} /><Stat icon={Gauge} label="Maximum claim capacity" value={profile.max_claim_capacity} /><Stat icon={Clock3} label="Average processing time" value={profile.average_processing_time_days} suffix=" days" /><Stat icon={Activity} label="On-time completion rate" value={profile.on_time_completion_rate} suffix="%" /></div></section>

      <Card><CardHeader title="Capacity utilization" subtitle={`${profile.active_claims} of ${profile.max_claim_capacity} active claims`} /><CardContent className="p-6"><div className="h-3 overflow-hidden rounded-full bg-gray-100"><div className={`h-full rounded-full ${utilization >= 100 ? 'bg-red-500' : 'bg-blue-600'}`} style={{ width: `${Math.min(100, utilization)}%` }} /></div><p className="mt-2 text-sm text-gray-600">{utilization}% utilized</p></CardContent></Card>
      <div className="grid gap-6 lg:grid-cols-2"><Card><CardHeader title="Availability and schedule" /><CardContent className="grid grid-cols-2 gap-4 p-6 text-sm"><p><span className="text-gray-500">Working days</span><br />{profile.working_days.length ? profile.working_days.join(', ').toUpperCase() : 'Not configured'}</p><p><span className="text-gray-500">Shift</span><br />{profile.shift_start_time && profile.shift_end_time ? `${profile.shift_start_time}–${profile.shift_end_time}` : 'Not configured'}</p><p><span className="text-gray-500">Current shift</span><br />{profile.current_shift_status.replaceAll('_', ' ')}</p><p><span className="text-gray-500">Leave status</span><br />{profile.leave_status || 'No leave recorded'}</p></CardContent></Card>
        <Card><CardHeader title="Experience and performance" /><CardContent className="grid grid-cols-2 gap-4 p-6 text-sm"><p><span className="text-gray-500">Total claims assigned</span><br />{profile.total_claims_assigned}</p><p><span className="text-gray-500">Successfully completed</span><br />{profile.successfully_completed_claims}</p><p><span className="text-gray-500">Reassignment count</span><br />{profile.reassignment_count ?? 'No history available'}</p><p><span className="text-gray-500">Average processing time</span><br />{profile.average_processing_time_days == null ? 'No completed claim history' : `${profile.average_processing_time_days} days`}</p></CardContent></Card></div>

      <Card><CardHeader title="Professional expertise" subtitle="Skills and specialization levels" action={canEditSkills && form ? <Button type="button" variant="secondary" size="sm" onClick={addSkill}>Add skill</Button> : null} /><CardContent className="space-y-4 p-6">{canEditSkills && form ? <><div className="space-y-3">{form.skills.map((skill, index) => <div key={skill.id || `skill-${index}`} className="grid gap-3 sm:grid-cols-[1fr_12rem_auto]"><Input aria-label="Skill name" placeholder="e.g. Vehicle damage assessment" value={skill.name} onChange={(e) => setSkill(index, 'name', e.target.value)} /><select aria-label="Expertise level" className="input-field" value={skill.level} onChange={(e) => setSkill(index, 'level', e.target.value)}>{LEVELS.map((level) => <option key={level} value={level}>{level}</option>)}</select><Button type="button" variant="ghost" onClick={() => removeSkill(index)}>Remove</Button></div>)}</div><Button type="button" loading={saving} disabled={saving} onClick={saveSkills}><Save className="mr-2 h-4 w-4" />Save expertise</Button></> : profile.skills.length ? <div className="flex flex-wrap gap-3">{profile.skills.map((skill) => <div key={skill.id} className="rounded-xl border border-gray-200 px-4 py-3"><p className="font-medium text-gray-900">{skill.name}</p><p className="mt-1 text-xs capitalize text-gray-500">{skill.level}</p></div>)}</div> : <p className="text-sm text-gray-500">No expertise has been added yet.</p>}</CardContent></Card>
      <Card><CardContent className="flex items-center justify-between gap-4 p-5"><div><h2 className="font-semibold text-gray-900">Assignment eligibility</h2><p className="text-sm text-gray-500">{profile.assignment_ineligibility_reason || 'Within capacity and available for assignments.'}</p></div><Badge variant={profile.assignment_eligible ? 'success' : 'warning'}>{profile.assignment_eligible ? 'Eligible' : 'Not eligible'}</Badge></CardContent></Card>
    </div>
  )
}
