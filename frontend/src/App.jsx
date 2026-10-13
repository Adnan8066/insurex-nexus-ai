import AppRoutes from './routes/AppRoutes'
import { ToastProvider } from './components/ui/Toast'

function App() {
  return (
    <ToastProvider position="top-right">
      <AppRoutes />
    </ToastProvider>
  )
}

export default App