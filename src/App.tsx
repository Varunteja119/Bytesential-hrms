import { Routes, Route, Navigate } from "react-router-dom"
import Login from "./pages/auth/Login"
import Dashboard from "./pages/dashboard/Dashboard"
import Employees from "./pages/employees/Employees"

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" />} />
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/employees" element={<Employees />} />
    </Routes>
  )
}

export default App
