import { Routes, Route, Navigate } from "react-router-dom"
import Login from "./pages/auth/Login"
import Dashboard from "./pages/dashboard/Dashboard"
import Employees from "./pages/employees/Employees"
import Recruitment from "./pages/recruitment/Recruitment"
import Leave from "./pages/leave/Leave"
import Payroll from "./pages/payroll/Payroll"
import AIChat from "./pages/ai-chat/AIChat"
import ProtectedRoute from "./components/ProtectedRoute"

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" />} />
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/employees" element={<ProtectedRoute><Employees /></ProtectedRoute>} />
      <Route path="/recruitment" element={<ProtectedRoute><Recruitment /></ProtectedRoute>} />
      <Route path="/leave" element={<ProtectedRoute><Leave /></ProtectedRoute>} />
      <Route path="/payroll" element={<ProtectedRoute><Payroll /></ProtectedRoute>} />
      <Route path="/ai-chat" element={<ProtectedRoute><AIChat /></ProtectedRoute>} />
    </Routes>
  )
}

export default App
