import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from '@/components/Navbar'
import AOSSizingPage from '@/pages/AOSSizing'

export default function App() {
  return (
    <div className="min-h-screen bg-bg">
      <Navbar />
      <Routes>
        <Route path="/provisioned/log-analytics" element={<AOSSizingPage />} />
        <Route path="*" element={<Navigate to="/provisioned/log-analytics" replace />} />
      </Routes>
    </div>
  )
}
