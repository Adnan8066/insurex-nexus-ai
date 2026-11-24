import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { Login } from './Login'

const mocks = vi.hoisted(() => ({
  requestCustomerCode: vi.fn(),
  customerCodeLogin: vi.fn(),
  customerLogin: vi.fn(),
}))

vi.mock('../../context/useAuth', () => ({
  useAuth: () => ({ customerCodeLogin: mocks.customerCodeLogin, customerLogin: mocks.customerLogin }),
}))

vi.mock('../../services', () => ({
  authService: { requestCustomerCode: (...args) => mocks.requestCustomerCode(...args) },
}))

vi.mock('../../components/auth/BrandArtwork', () => ({
  AuthLayout: ({ children }) => <div>{children}</div>,
}))

function renderLogin() {
  render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<div>PAGE:Dashboard</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Customer sign-in with an emailed code', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.requestCustomerCode.mockResolvedValue({ expires_in_minutes: 10 })
  })

  it('requests a code, then signs in with it', async () => {
    mocks.customerCodeLogin.mockResolvedValue({ success: true })
    renderLogin()

    fireEvent.change(screen.getByPlaceholderText('you@example.com'), { target: { value: 'pat@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: 'Email me a sign-in code' }))

    await waitFor(() => expect(mocks.requestCustomerCode).toHaveBeenCalledWith('pat@example.com'))
    expect(await screen.findByRole('status')).toHaveTextContent('expires in 10 minutes')

    fireEvent.change(screen.getByPlaceholderText('123456'), { target: { value: '482913' } })
    fireEvent.click(screen.getByRole('button', { name: 'Verify code and sign in' }))

    await waitFor(() =>
      expect(mocks.customerCodeLogin).toHaveBeenCalledWith({ email: 'pat@example.com', code: '482913' }),
    )
    expect(await screen.findByText('PAGE:Dashboard')).toBeInTheDocument()
  })

  it('does not submit a code that is not 6 digits', async () => {
    renderLogin()
    fireEvent.change(screen.getByPlaceholderText('you@example.com'), { target: { value: 'pat@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: 'Email me a sign-in code' }))
    await screen.findByPlaceholderText('123456')

    fireEvent.change(screen.getByPlaceholderText('123456'), { target: { value: '12ab' } })
    fireEvent.click(screen.getByRole('button', { name: 'Verify code and sign in' }))

    expect(await screen.findByText('Enter the 6-digit code')).toBeInTheDocument()
    expect(mocks.customerCodeLogin).not.toHaveBeenCalled()
  })

  it('shows the error when the code is rejected', async () => {
    mocks.customerCodeLogin.mockResolvedValue({ success: false, error: 'That code is incorrect or has expired.' })
    renderLogin()
    fireEvent.change(screen.getByPlaceholderText('you@example.com'), { target: { value: 'pat@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: 'Email me a sign-in code' }))
    fireEvent.change(await screen.findByPlaceholderText('123456'), { target: { value: '000000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Verify code and sign in' }))

    expect(await screen.findByText('That code is incorrect or has expired.')).toBeInTheDocument()
    expect(screen.queryByText('PAGE:Dashboard')).not.toBeInTheDocument()
  })

  it('still offers password sign-in', async () => {
    mocks.customerLogin.mockResolvedValue({ success: true })
    renderLogin()
    fireEvent.click(screen.getByRole('button', { name: 'Sign in with a password instead' }))

    fireEvent.change(screen.getByPlaceholderText('you@example.com'), { target: { value: 'pat@example.com' } })
    fireEvent.change(document.querySelector('input[name="password"]'), { target: { value: 'secret-pass' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() =>
      expect(mocks.customerLogin).toHaveBeenCalledWith({ email: 'pat@example.com', password: 'secret-pass' }),
    )
    expect(mocks.requestCustomerCode).not.toHaveBeenCalled()
  })
})
