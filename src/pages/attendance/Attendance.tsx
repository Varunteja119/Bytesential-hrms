import DashboardLayout from "@/components/layout/DashboardLayout"
import { useMemo, useState } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

const attendanceData = [
  {
    id: "BS-2025-001",
    name: "Rahul Sharma",
    department: "Engineering",
    checkIn: "09:02 AM",
    checkOut: "06:11 PM",
    hours: "9h 09m",
    status: "Present",
  },
  {
    id: "BS-2025-002",
    name: "Priya Patel",
    department: "HR",
    checkIn: "09:18 AM",
    checkOut: "06:03 PM",
    hours: "8h 45m",
    status: "Late",
  },
  {
    id: "BS-2025-003",
    name: "Amit Kumar",
    department: "Finance",
    checkIn: "--",
    checkOut: "--",
    hours: "--",
    status: "Leave",
  },
  {
    id: "BS-2025-004",
    name: "Sneha Reddy",
    department: "Engineering",
    checkIn: "--",
    checkOut: "--",
    hours: "--",
    status: "Absent",
  },
  {
    id: "BS-2025-005",
    name: "Vikram Singh",
    department: "Sales",
    checkIn: "08:57 AM",
    checkOut: "06:09 PM",
    hours: "9h 12m",
    status: "Present",
  },
  {
    id: "BS-2025-006",
    name: "Ananya Das",
    department: "Engineering",
    checkIn: "09:05 AM",
    checkOut: "06:15 PM",
    hours: "9h 10m",
    status: "Present",
  },
]

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    Present: "bg-green-100 text-green-700",
    Late: "bg-yellow-100 text-yellow-700",
    Leave: "bg-blue-100 text-blue-700",
    Absent: "bg-red-100 text-red-700",
  }

  return (
    <span
      className={`px-3 py-1 rounded-full text-xs font-medium ${
        styles[status]
      }`}
    >
      {status}
    </span>
  )
}

export default function Attendance() {
  const [search, setSearch] = useState("")
  const [department, setDepartment] = useState("All")

  const filtered = useMemo(() => {
    return attendanceData.filter((emp) => {
      const searchMatch =
        emp.name.toLowerCase().includes(search.toLowerCase()) ||
        emp.department.toLowerCase().includes(search.toLowerCase())

      const deptMatch =
        department === "All" || emp.department === department

      return searchMatch && deptMatch
    })
  }, [search, department])

  const stats = {
    total: attendanceData.length,
    present: attendanceData.filter((e) => e.status === "Present").length,
    late: attendanceData.filter((e) => e.status === "Late").length,
    leave: attendanceData.filter((e) => e.status === "Leave").length,
    absent: attendanceData.filter((e) => e.status === "Absent").length,
  }

  const attendanceRate = Math.round(
    ((stats.present + stats.late) / stats.total) * 100
  )

  return (
    <DashboardLayout>
      <div className="space-y-6">

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Attendance
            </h1>

            <p className="text-sm text-gray-500 mt-1">
              Daily employee attendance overview
            </p>
          </div>

          <div className="flex gap-3">
            <Button className="bg-white border border-gray-200 text-gray-700 hover:bg-gray-50">
              Export
            </Button>

            <Button className="bg-blue-600 hover:bg-blue-700 text-white">
              + Mark Attendance
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-6 gap-4">

          {[
            {
              label: "Employees",
              value: stats.total,
              color: "bg-indigo-500",
            },
            {
              label: "Present",
              value: stats.present,
              color: "bg-green-500",
            },
            {
              label: "Late",
              value: stats.late,
              color: "bg-yellow-500",
            },
            {
              label: "Leave",
              value: stats.leave,
              color: "bg-blue-500",
            },
            {
              label: "Absent",
              value: stats.absent,
              color: "bg-red-500",
            },
            {
              label: "Attendance %",
              value: `${attendanceRate}%`,
              color: "bg-purple-500",
            },
          ].map((card) => (
            <div
              key={card.label}
              className="bg-white rounded-xl border border-gray-100 shadow-sm p-5"
            >
              <div
                className={`w-8 h-8 rounded-lg ${card.color} mb-3`}
              />

              <p className="text-2xl font-bold text-gray-900">
                {card.value}
              </p>

              <p className="text-sm text-gray-500 mt-1">
                {card.label}
              </p>
            </div>
          ))}

        </div>

        <div className="flex gap-3">

          <Input
            placeholder="Search employee..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-sm"
          />

          <select
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            className="border rounded-lg px-4 py-2 bg-white"
          >
            <option>All</option>
            <option>Engineering</option>
            <option>HR</option>
            <option>Finance</option>
            <option>Sales</option>
          </select>

        </div>
                {/* Attendance Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-100">
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Employee
                </th>

                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Department
                </th>

                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Check In
                </th>

                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Check Out
                </th>

                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Working Hours
                </th>

                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Status
                </th>

                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-gray-50">
              {filtered.map((emp) => (
                <tr
                  key={emp.id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold">
                        {emp.name.charAt(0)}
                      </div>

                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {emp.name}
                        </p>

                        <p className="text-xs text-gray-500">
                          {emp.id}
                        </p>
                      </div>
                    </div>
                  </td>

                  <td className="px-6 py-4 text-sm text-gray-600">
                    {emp.department}
                  </td>

                  <td className="px-6 py-4 text-sm text-gray-600">
                    {emp.checkIn}
                  </td>

                  <td className="px-6 py-4 text-sm text-gray-600">
                    {emp.checkOut}
                  </td>

                  <td className="px-6 py-4 text-sm font-medium text-gray-800">
                    {emp.hours}
                  </td>

                  <td className="px-6 py-4">
                    <StatusBadge status={emp.status} />
                  </td>

                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      <button className="text-xs text-blue-600 hover:underline">
                        View
                      </button>

                      <button className="text-xs text-gray-500 hover:underline">
                        Edit
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filtered.length === 0 && (
            <div className="py-12 text-center text-gray-400">
              No employees found
            </div>
          )}
        </div>

      </div>
    </DashboardLayout>
  )
}