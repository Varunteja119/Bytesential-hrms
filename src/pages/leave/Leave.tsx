import DashboardLayout from "@/components/layout/DashboardLayout"
import { useState } from "react"
import { Button } from "@/components/ui/button"

const leaveRequests = [
  { id: 1, employee: "Rahul Sharma", type: "Earned Leave", from: "Jun 15, 2025", to: "Jun 17, 2025", days: 3, reason: "Family function", status: "pending" },
  { id: 2, employee: "Priya Patel", type: "Sick Leave", from: "Jun 10, 2025", to: "Jun 11, 2025", days: 2, reason: "Fever and rest", status: "approved" },
  { id: 3, employee: "Amit Kumar", type: "Casual Leave", from: "Jun 20, 2025", to: "Jun 20, 2025", days: 1, reason: "Personal work", status: "approved" },
  { id: 4, employee: "Sneha Reddy", type: "Earned Leave", from: "Jun 25, 2025", to: "Jun 27, 2025", days: 3, reason: "Vacation", status: "pending" },
  { id: 5, employee: "Vikram Singh", type: "Loss of Pay", from: "Jun 5, 2025", to: "Jun 6, 2025", days: 2, reason: "Personal", status: "rejected" },
]

const balances = [
  { type: "Earned Leave", allocated: 15, used: 4, remaining: 11, color: "bg-blue-500" },
  { type: "Sick Leave", allocated: 7, used: 2, remaining: 5, color: "bg-green-500" },
  { type: "Casual Leave", allocated: 7, used: 1, remaining: 6, color: "bg-yellow-500" },
  { type: "Loss of Pay", allocated: 0, used: 2, remaining: 0, color: "bg-red-500" },
]

const statusConfig: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
}

export default function Leave() {
  const [filter, setFilter] = useState("all")
  const [tab, setTab] = useState<"requests" | "balances">("requests")

  const filtered = leaveRequests.filter(l =>
    filter === "all" || l.status === filter
  )

  return (
    <DashboardLayout>
      <div className="space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Leave Management</h1>
            <p className="text-gray-500 text-sm mt-1">Manage leave requests and balances</p>
          </div>
          <Button className="bg-blue-600 hover:bg-blue-700 text-white">
            + Apply Leave
          </Button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Total Requests", value: leaveRequests.length, color: "bg-blue-500" },
            { label: "Pending", value: leaveRequests.filter(l => l.status === "pending").length, color: "bg-yellow-500" },
            { label: "Approved", value: leaveRequests.filter(l => l.status === "approved").length, color: "bg-green-500" },
            { label: "Rejected", value: leaveRequests.filter(l => l.status === "rejected").length, color: "bg-red-500" },
          ].map((s) => (
            <div key={s.label} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
              <div className={`w-8 h-8 ${s.color} rounded-lg mb-3`} />
              <p className="text-2xl font-bold text-gray-900">{s.value}</p>
              <p className="text-sm text-gray-500 mt-1">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex gap-2">
          {["requests", "balances"].map(t => (
            <button
              key={t}
              onClick={() => setTab(t as any)}
              className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                tab === t ? "bg-blue-600 text-white" : "bg-white border border-gray-200 text-gray-600"
              }`}
            >
              {t === "requests" ? "Leave Requests" : "Leave Balances"}
            </button>
          ))}
        </div>

        {/* Leave Requests Tab */}
        {tab === "requests" && (
          <div className="space-y-4">
            {/* Filter */}
            <div className="flex gap-2">
              {["all", "pending", "approved", "rejected"].map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                    filter === f ? "bg-blue-600 text-white" : "bg-white border border-gray-200 text-gray-600"
                  }`}
                >
                  {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Employee</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Type</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">From</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">To</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Days</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Reason</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Status</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filtered.map((l) => (
                    <tr key={l.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center text-white text-sm font-bold">
                            {l.employee.charAt(0)}
                          </div>
                          <p className="text-sm font-medium text-gray-900">{l.employee}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{l.type}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{l.from}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{l.to}</td>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">{l.days}</td>
                      <td className="px-6 py-4 text-sm text-gray-500 max-w-xs truncate">{l.reason}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusConfig[l.status]}`}>
                          {l.status.charAt(0).toUpperCase() + l.status.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {l.status === "pending" ? (
                          <div className="flex gap-2">
                            <button className="text-xs text-green-600 hover:underline font-medium">Approve</button>
                            <button className="text-xs text-red-500 hover:underline">Reject</button>
                          </div>
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Leave Balances Tab */}
        {tab === "balances" && (
          <div className="grid grid-cols-2 gap-4">
            {balances.map((b) => (
              <div key={b.type} className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-800">{b.type}</h3>
                  <span className="text-sm text-gray-500">{b.remaining} remaining</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2 mb-3">
                  <div
                    className={`${b.color} h-2 rounded-full`}
                    style={{ width: b.allocated > 0 ? `${((b.allocated - b.used) / b.allocated) * 100}%` : "0%" }}
                  />
                </div>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Used: {b.used} days</span>
                  <span>Allocated: {b.allocated} days</span>
                </div>
              </div>
            ))}
          </div>
        )}

      </div>
    </DashboardLayout>
  )
}
