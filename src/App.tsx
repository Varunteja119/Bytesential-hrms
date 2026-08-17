import { Routes, Route, Navigate } from "react-router-dom"
import Login from "./pages/auth/Login"
import ChangePassword from "./pages/auth/ChangePassword"
import Dashboard from "./pages/dashboard/Dashboard"
import Employees from "./pages/employees/Employees"
import Recruitment from "./pages/recruitment/Recruitment"
import Leave from "./pages/leave/Leave"
import Payroll from "./pages/payroll/Payroll"
import AIChat from "./pages/ai-chat/AIChat"
import Attendance from "./pages/attendance/Attendance"
import VerificationQueue from "./pages/hr/VerificationQueue"
import ProtectedRoute from "./components/ProtectedRoute"

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" />} />
      <Route path="/login" element={<Login />} />
      <Route path="/change-password" element={<ProtectedRoute><ChangePassword /></ProtectedRoute>} />

      {/* HR/Admin only */}
      <Route path="/dashboard" element={<ProtectedRoute roles={["hr_manager", "admin"]}><Dashboard /></ProtectedRoute>} />
      <Route path="/employees" element={<ProtectedRoute roles={["hr_manager", "admin"]}><Employees /></ProtectedRoute>} />
      <Route path="/recruitment" element={<ProtectedRoute roles={["hr_manager", "admin"]}><Recruitment /></ProtectedRoute>} />
      <Route path="/leave" element={<ProtectedRoute roles={["hr_manager", "admin"]}><Leave /></ProtectedRoute>} />
      <Route path="/payroll" element={<ProtectedRoute roles={["hr_manager", "admin"]}><Payroll /></ProtectedRoute>} />
      <Route path="/ai-chat" element={<ProtectedRoute roles={["hr_manager", "admin"]}><AIChat /></ProtectedRoute>} />
      <Route path="/attendance" element={<ProtectedRoute roles={["hr_manager", "admin"]}><Attendance /></ProtectedRoute>} />
      <Route path="/analytics" element={<ProtectedRoute roles={["hr_manager", "admin"]}><div className="p-8"><h1 className="text-2xl font-bold">Analytics — Coming Soon</h1></div></ProtectedRoute>} />
      <Route path="/finance" element={<ProtectedRoute roles={["hr_manager", "admin"]}><div className="p-8"><h1 className="text-2xl font-bold">Finance — Coming Soon</h1></div></ProtectedRoute>} />
      <Route path="/hr/verification" element={<ProtectedRoute roles={["hr_manager", "admin"]}><VerificationQueue /></ProtectedRoute>} />

      {/* Employee only */}
      <Route path="/onboarding" element={<ProtectedRoute><div className="p-8"><h1 className="text-2xl font-bold">Onboarding Portal — Coming Soon</h1></div></ProtectedRoute>} />
    </Routes>
  )
}

export default App
