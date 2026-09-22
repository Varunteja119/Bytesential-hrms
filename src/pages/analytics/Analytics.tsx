import DashboardLayout from "@/components/layout/DashboardLayout"
import { useState, useEffect } from "react"
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts"
import axios from "axios"
import { apiHeaders } from "@/lib/auth"

const BASE = "http://localhost:8000/api/v1"
const COLORS = ["#2E5FA3", "#1A8FD1", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"]

export default function Analytics() {
  const [headcount, setHeadcount] = useState<any>(null)
  const [attendance, setAttendance] = useState<any>(null)
  const [leave, setLeave] = useState<any>(null)
  const [payroll, setPayroll] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { fetchAll() }, [])

  async function fetchAll() {
    try {
      const [hcRes, attRes, leaveRes, payrollRes] = await Promise.allSettled([
        axios.get(`${BASE}/analytics/headcount`, { headers: apiHeaders() }),
        axios.get(`${BASE}/analytics/attendance-summary`, { headers: apiHeaders() }),
        axios.get(`${BASE}/analytics/leave-utilization`, { headers: apiHeaders() }),
        axios.get(`${BASE}/analytics/payroll-cost-trend`, { headers: apiHeaders() }),
      ])
      if (hcRes.status === "fulfilled") setHeadcount(hcRes.value.data)
      if (attRes.status === "fulfilled") setAttendance(attRes.value.data)
      if (leaveRes.status === "fulfilled") setLeave(leaveRes.value.data)
      if (payrollRes.status === "fulfilled") setPayroll(payrollRes.value.data)
    } catch (err) {
      console.error("Failed to fetch analytics", err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-500 text-sm mt-1">Workforce insights and trends</p>
        </div>

        {loading ? (
          <div className="text-center py-20 text-gray-400">Loading analytics...</div>
        ) : (
          <>
            {headcount && (
              <div className="grid grid-cols-4 gap-4">
                {[
                  { label: "Total Employees", value: headcount.total ?? 0, color: "bg-blue-500" },
                  { label: "Active", value: headcount.active ?? 0, color: "bg-green-500" },
                  { label: "Pending Activation", value: headcount.pending_activation ?? 0, color: "bg-yellow-500" },
                  { label: "Inactive", value: headcount.inactive ?? 0, color: "bg-red-500" },
                ].map(s => (
                  <div key={s.label} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                    <div className={`w-8 h-8 ${s.color} rounded-lg mb-3`} />
                    <p className="text-2xl font-bold text-gray-900">{s.value}</p>
                    <p className="text-sm text-gray-500 mt-1">{s.label}</p>
                  </div>
                ))}
              </div>
            )}

            {headcount?.by_department && Object.keys(headcount.by_department).length > 0 && (
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
                <h2 className="font-semibold text-gray-800 mb-4">Headcount by Department</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={Object.entries(headcount.by_department).map(([dept, count]) => ({ dept, count }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="dept" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#2E5FA3" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            <div className="grid grid-cols-2 gap-6">
              {attendance && (
                <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
                  <h2 className="font-semibold text-gray-800 mb-4">Attendance Summary</h2>
                  <div className="space-y-3">
                    {Object.entries(attendance).map(([key, val]: any) => (
                      typeof val !== "object" && (
                        <div key={key} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                          <span className="text-sm text-gray-600 capitalize">{key.replace(/_/g, " ")}</span>
                          <span className="text-sm font-medium text-gray-900">{typeof val === "number" ? val.toFixed ? val.toFixed(1) : val : val}</span>
                        </div>
                      )
                    ))}
                  </div>
                </div>
              )}

              {leave && (
                <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
                  <h2 className="font-semibold text-gray-800 mb-4">Leave Utilization</h2>
                  {Array.isArray(leave) && leave.length > 0 ? (
                    <ResponsiveContainer width="100%" height={200}>
                      <PieChart>
                        <Pie data={leave} dataKey="used_days" nameKey="leave_type" cx="50%" cy="50%" outerRadius={80}
                          label={({ leave_type, used_days }) => `${leave_type}: ${used_days}`}>
                          {leave.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-sm text-gray-400">No leave data yet</p>
                  )}
                </div>
              )}
            </div>

            {payroll && Array.isArray(payroll) && payroll.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
                <h2 className="font-semibold text-gray-800 mb-4">Payroll Cost Trend</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={payroll}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(v: any) => [`₹${v.toLocaleString("en-IN")}`, "Net Payroll"]} />
                    <Line type="monotone" dataKey="total_net" stroke="#2E5FA3" strokeWidth={2} dot={{ fill: "#2E5FA3" }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {!headcount && !attendance && !leave && !payroll && (
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-12 text-center text-gray-400">
                No analytics data available yet
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  )
}
