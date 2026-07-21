import DashboardLayout from "@/components/layout/DashboardLayout"
import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

const employees = [
  { id: "BS-2025-001", name: "Rahul Sharma", email: "rahul@bytesentinel.com", department: "Engineering", designation: "Senior Developer", status: "active", joining: "Jan 2024" },
  { id: "BS-2025-002", name: "Priya Patel", email: "priya@bytesentinel.com", department: "HR", designation: "HR Manager", status: "active", joining: "Mar 2024" },
  { id: "BS-2025-003", name: "Amit Kumar", email: "amit@bytesentinel.com", department: "Finance", designation: "Finance Analyst", status: "active", joining: "Jun 2024" },
  { id: "BS-2025-004", name: "Sneha Reddy", email: "sneha@bytesentinel.com", department: "Engineering", designation: "Frontend Developer", status: "on_notice", joining: "Aug 2024" },
  { id: "BS-2025-005", name: "Vikram Singh", email: "vikram@bytesentinel.com", department: "Sales", designation: "Sales Executive", status: "active", joining: "Oct 2024" },
  { id: "BS-2025-006", name: "Ananya Das", email: "ananya@bytesentinel.com", department: "Engineering", designation: "AI Engineer", status: "active", joining: "Nov 2024" },
]

function statusBadge(status: string) {
  if (status === "active") return <Badge className="bg-green-100 text-green-700 hover:bg-green-100">Active</Badge>
  if (status === "on_notice") return <Badge className="bg-yellow-100 text-yellow-700 hover:bg-yellow-100">On Notice</Badge>
  return <Badge className="bg-red-100 text-red-700 hover:bg-red-100">Inactive</Badge>
}

export default function Employees() {
  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState("all")

  const filtered = employees.filter(emp => {
    const matchSearch = emp.name.toLowerCase().includes(search.toLowerCase()) ||
      emp.email.toLowerCase().includes(search.toLowerCase()) ||
      emp.department.toLowerCase().includes(search.toLowerCase())
    const matchFilter = filter === "all" || emp.status === filter
    return matchSearch && matchFilter
  })

  return (
    <DashboardLayout>
      <div className="space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Employees</h1>
            <p className="text-gray-500 text-sm mt-1">{employees.length} total employees</p>
          </div>
          <Button className="bg-blue-600 hover:bg-blue-700 text-white">
            + Add Employee
          </Button>
        </div>

        {/* Filters */}
        <div className="flex gap-3">
          <Input
            placeholder="Search by name, email, department..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-sm"
          />
          <div className="flex gap-2">
            {["all", "active", "on_notice"].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filter === f
                    ? "bg-blue-600 text-white"
                    : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
                }`}
              >
                {f === "all" ? "All" : f === "active" ? "Active" : "On Notice"}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-100">
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Employee</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Department</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Designation</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Joining</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map((emp) => (
                <tr key={emp.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold">
                        {emp.name.charAt(0)}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{emp.name}</p>
                        <p className="text-xs text-gray-500">{emp.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{emp.department}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{emp.designation}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{emp.joining}</td>
                  <td className="px-6 py-4">{statusBadge(emp.status)}</td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      <button className="text-xs text-blue-600 hover:underline">View</button>
                      <button className="text-xs text-gray-500 hover:underline">Edit</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filtered.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              No employees found
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}
