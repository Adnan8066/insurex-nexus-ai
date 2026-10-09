import { useState } from 'react'
import {
  Settings as SettingsIcon,
  Server,
  Cpu,
  Brain,
  Sliders,
  Bell,
  Save,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'

export function Settings() {
  const [saved, setSaved] = useState(false)
  const [config, setConfig] = useState({
    apiBaseUrl: 'http://localhost:8000/api',
    fraudThreshold: 65,
    totalLossThreshold: 75,
    autoApproveLimit: 3000,
    activeModelVersion: 'claim-assessment-v2.3.1',
    rlLearningRate: '0.0003',
    notificationsEmail: true,
    notificationsWebhooks: true,
    enableExplainability: true,
  })

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setConfig((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleSave = (e) => {
    e.preventDefault()
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="page max-w-4xl mx-auto space-y-6">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Platform & System Settings</h1>
          <p className="page-subtitle">Configure backend API integration, AI inference thresholds, and reinforcement learning parameters</p>
        </div>

        <Button variant="primary" onClick={handleSave}>
          <Save className="w-4 h-4 mr-2" />
          Save Settings
        </Button>
      </div>

      {saved && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-sm font-medium flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          Configuration settings updated successfully.
        </div>
      )}

      {/* Backend API Configuration */}
      <Card>
        <CardHeader
          title="Backend API Integration (Django REST Framework)"
          subtitle="Axios service proxy endpoints and database bridge"
        />
        <CardContent className="p-6 space-y-4">
          <Input
            label="Django REST Framework API Base URL"
            name="apiBaseUrl"
            value={config.apiBaseUrl}
            onChange={handleChange}
            hint="Default development endpoint: http://localhost:8000/api"
          />
          <div className="p-3 bg-gray-50 rounded-xl text-xs text-gray-600 flex items-center justify-between">
            <span>Authentication Interceptors: <strong>JWT Bearer Token with auto-refresh</strong></span>
            <span className="text-emerald-600 font-semibold">Active & Ready</span>
          </div>
        </CardContent>
      </Card>

      {/* AI Inference Thresholds */}
      <Card>
        <CardHeader
          title="AI Inference & Risk Thresholds"
          subtitle="Automated routing and triage rules"
        />
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Fraud Risk Flag Threshold (%)"
              type="number"
              name="fraudThreshold"
              value={config.fraudThreshold}
              onChange={handleChange}
              hint="Claims scoring above this value are routed to SIU"
            />
            <Input
              label="Total Loss Threshold (%)"
              type="number"
              name="totalLossThreshold"
              value={config.totalLossThreshold}
              onChange={handleChange}
              hint="Vehicle repair cost vs actual cash value threshold"
            />
            <Input
              label="Straight-Through Auto-Approval Limit ($)"
              type="number"
              name="autoApproveLimit"
              value={config.autoApproveLimit}
              onChange={handleChange}
              hint="Maximum payout for low-risk fast-track approval"
            />
            <Select
              label="Production ML Model Version"
              name="activeModelVersion"
              value={config.activeModelVersion}
              onChange={handleChange}
              options={[
                { value: 'claim-assessment-v2.3.1', label: 'claim-assessment-v2.3.1 (Latest Stable)' },
                { value: 'claim-assessment-v2.2.0', label: 'claim-assessment-v2.2.0 (Legacy)' },
                { value: 'experimental-v3.0.0-rc', label: 'experimental-v3.0.0-rc (Transformer)' },
              ]}
            />
          </div>
        </CardContent>
      </Card>

      {/* RL Policy Settings */}
      <Card>
        <CardHeader
          title="Reinforcement Learning Policy Tuning"
          subtitle="PPO hyperparameters for triage and investigator dispatch"
        />
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="PPO Policy Learning Rate"
              name="rlLearningRate"
              value={config.rlLearningRate}
              onChange={handleChange}
            />
            <div className="space-y-3 pt-6">
              <label className="flex items-center gap-2 cursor-pointer text-sm font-medium text-gray-800">
                <input
                  type="checkbox"
                  name="enableExplainability"
                  checked={config.enableExplainability}
                  onChange={handleChange}
                  className="w-4 h-4 text-primary rounded"
                />
                Enforce Explainable AI (SHAP / Feature weights output)
              </label>
              <label className="flex items-center gap-2 cursor-pointer text-sm font-medium text-gray-800">
                <input
                  type="checkbox"
                  name="notificationsEmail"
                  checked={config.notificationsEmail}
                  onChange={handleChange}
                  className="w-4 h-4 text-primary rounded"
                />
                Enable High-Priority Incident Email Dispatches
              </label>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default Settings
