import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ClaimDetails } from './ClaimDetails'

const api = vi.hoisted(() => ({
  getClaim: null,
}))

vi.mock('../../context/useAuth', () => ({
  useAuth: () => ({
    user: { id: 2, role: 'employee', email: 'emp@example.com', first_name: 'Asha', last_name: 'Nair' },
    isAuthenticated: true,
    loading: false,
    hasRole: () => true,
  }),
}))

vi.mock('../../services', () => ({
  claimService: {
    getClaim: (...args) => api.getClaim(...args),
    getClaimDocuments: vi.fn().mockResolvedValue([]),
    getClaimTimeline: vi.fn().mockResolvedValue([]),
  },
  policyService: {
    getPolicyFormOptions: vi.fn().mockResolvedValue({ agents: [], investigators: [] }),
  },
  investigationService: {
    getInvestigations: vi.fn().mockResolvedValue({ results: [] }),
    getVehicleChecks: vi.fn().mockResolvedValue({ checks: [], completed: 0, total: 10 }),
  },
}))

function claimFixture(overrides = {}) {
  return {
    id: 32894,
    claim_number: 'CLM-TEST-1',
    status: 'submitted',
    customer: 1,
    customer_name: 'Test Customer',
    policy: 5,
    policy_number: 'POL-TEST-5',
    vehicle: 9,
    incident_date: '2026-11-10',
    incident_type: 'collision',
    incident_severity: 'minor',
    location: 'Kochi, Kerala',
    claim_amount: '25000.00',
    priority: 'medium',
    description: 'Rear bumper hit while reversing in a parking lot.',
    documents: [],
    timeline: [],
    ...overrides,
  }
}

function renderClaim() {
  return render(
    <MemoryRouter initialEntries={['/claims/32894']}>
      <Routes>
        <Route path="/claims/:id" element={<ClaimDetails />} />
      </Routes>
    </MemoryRouter>,
  )
}

async function openIncidentTab() {
  // The claim number appears in several places on the page, so wait for at least one.
  await waitFor(() => expect(screen.getAllByText('CLM-TEST-1').length).toBeGreaterThan(0))
  fireEvent.click(screen.getByRole('button', { name: /Incident & Damage Details/i }))
}

describe('ClaimDetails incident narrative', () => {
  beforeEach(() => {
    api.getClaim = vi.fn().mockResolvedValue(claimFixture())
  })

  it('shows the customer description, not template text', async () => {
    renderClaim()
    await openIncidentTab()

    expect(await screen.findByText('Rear bumper hit while reversing in a parking lot.')).toBeInTheDocument()
    expect(screen.getByText(/Kochi, Kerala/)).toBeInTheDocument()
    expect(screen.queryByText(/Vehicle was operating under normal conditions/)).not.toBeInTheDocument()
  })

  it('shows a fallback only when the description is empty', async () => {
    api.getClaim = vi.fn().mockResolvedValue(claimFixture({ description: '   ' }))
    renderClaim()
    await openIncidentTab()

    await waitFor(() => {
      expect(screen.getByText('The customer did not write an incident description for this claim.')).toBeInTheDocument()
    })
  })
})
