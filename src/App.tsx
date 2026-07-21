import { Routes, Route, Navigate } from "react-router-dom"

import Login from "./pages/auth/Login"
import Dashboard from "./pages/dashboard/Dashboard"
import Employees from "./pages/employees/Employees"
import Recruitment from "./pages/recruitment/Recruitment"
import Attendance from "./pages/attendance/Attendance"
import Leave from "./pages/leave/Leave"
import Payroll from "./pages/payroll/Payroll"
import AIChat from "./pages/ai-chat/AIChat"
import Analytics from "./pages/analytics/Analytics"
import Finance from "./pages/finance/Finance"

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" />} />
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/employees" element={<Employees />} />
      <Route path="/recruitment" element={<Recruitment />} />
      <Route path="/attendance" element={<Attendance />} />
      <Route path="/leave" element={<Leave />} />
      <Route path="/payroll" element={<Payroll />} />
      <Route path="/ai-chat" element={<AIChat />} />
      <Route path="/analytics" element={<Analytics />} />
      <Route path="/finance" element={<Finance />} />
    </Routes>
  )
}

export default App
