import { Routes, Route, Navigate } from "react-router-dom"
import Login from "./pages/auth/Login"
import Dashboard from "./pages/dashboard/Dashboard"
import Employees from "./pages/employees/Employees"
import Recruitment from "./pages/recruitment/Recruitment"
import Leave from "./pages/leave/Leave"

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" />} />
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/employees" element={<Employees />} />
      <Route path="/recruitment" element={<Recruitment />} />
      <Route path="/leave" element={<Leave />} />
    </Routes>
  )
}

export default App
