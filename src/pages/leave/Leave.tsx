import DashboardLayout from "@/components/layout/DashboardLayout"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import axios from "axios"
import { apiHeaders } from "@/lib/auth"

const BASE = "http://localhost:8000/api/v1"

interface LeaveRequest {
  id: string
  employee_id: string
  leave_type: string
  start_date: string
  end_date: string
  days_requested: number
  reason: string | null
  status: string
  decided_by_id: string | null
  decided_at: string | null
  decision_note: string | null
}

interface LeaveBalance {
  leave_type: string
  year: number
  allocated_days: number
  used_days: number
  remaining_days: number
}

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-600",
  cancelled: "bg-gray-100 text-gray-500",
}

export default function Leave() {
  const [requests, setRequests] = useState<LeaveRequest[]>([])
  const [balances, setBalances] = useState<LeaveBalance[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<"requests" | "balances">("requests")
  const [filter, setFilter] = useState("all")
  const [rejectId, setRejectId] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState("")

  // Apply leave form
  const [showApply, setShowApply] = useState(false)
  const [applyForm, setApplyForm] = useState({
    leave_type: "casual",
    start_date: "",
    end_date: "",
    reason: ""
  })
  const [applyLoading, setApplyLoading] = useState(false)
  const [applyError, setApplyError] = useState("")

  useEffect(() => {
    fetchData()
  }, [])

  async function fetchData() {
    try {
      const [reqRes, balRes] = await Promise.all([
        axios.get(`${BASE}/leave`, { headers: apiHeaders() }),
        axios.get(`${BASE}/leave/balance/me`, { headers: apiHeaders() })
      ])
      setRequests(reqRes.data)
      setBalances(balRes.data)
    } catch (err) {
      console.error("Failed to fetch leave data", err)
    } finally {
      setLoading(false)
    }
  }

  async function approveLeave(id: string) {
    try {
      await axios.post(`${BASE}/leave/${id}/approve`, {}, { headers: apiHeaders() })
      fetchData()
    } catch (err: any) {
      alert(err.response?.data?.error?.message || "Failed to approve")
    }
  }

  async function rejectLeave() {
    if (!rejectId || !rejectReason) return
    try {
      await axios.post(
        `${BASE}/leave/${rejectId}/reject`,
        { rejection_reason: rejectReason },
        { headers: apiHeaders() }
      )
      setRejectId(null)
      setRejectReason("")
      fetchData()
    } catch (err: any) {
      alert(err.response?.data?.error?.message || "Failed to reject")
    }
  }

  async function applyLeave() {
    if (!applyForm.start_date || !applyForm.end_date) {
      setApplyError("Please fill in all fields")
      return
    }
    setApplyLoading(true)
    setApplyError("")
    try {
      await axios.post(`${BASE}/leave/apply`, applyForm, { headers: apiHeaders() })
      setShowApply(false)
      setApplyForm({ leave_type: "casual", start_date: "", end_date: "", reason: "" })
      fetchData()
    } catch (err: any) {
      setApplyError(err.response?.data?.error?.message || "Failed to apply")
    } finally {
      setApplyLoading(false)
    }
  }

  const filtered = requests.filter(r => filter === "all" || r.status === filter)

  const pending = requests.filter(r => r.status === "pending").length
  const approved = requests.filter(r => r.status === "approved").length
  const rejected = requests.filter(r => r.status === "rejected").length

  return (
    <DashboardLayout>
      <div className="space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Leave Management</h1>
            <p className="text-gray-500 text-sm mt-1">Manage leave requests and balances</p>
          </div>
          <Button className="bg-blue-600 hover:bg-blue-700 text-white" onClick={() => setShowApply(!showApply)}>
            + Apply Leave
          </Button>
        </div>

        {/* Apply Form */}
        {showApply && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
            <h2 className="font-semibold text-gray-800">Apply for Leave</h2>
            {applyError && <div className="bg-red-50 text-red-600 text-sm p-3 rounded-md">{applyError}</div>}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Leave Type</label>
                <select
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  value={applyForm.leave_type}
                  onChange={e => setApplyForm({...applyForm, leave_type: e.target.value})}
                >
                  <option value="casual">Casual Leave</option>
                  <option value="sick">Sick Leave</option>
                  <option value="earned">Earned Leave</option>
                  <option value="unpaid">Unpaid Leave</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Reason</label>
                <input
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  value={applyForm.reason}
                  onChange={e => setApplyForm({...applyForm, reason: e.target.value})}
                  placeholder="Reason for leave"
                />
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Start Date</label>
                <input type="date" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  value={applyForm.start_date} onChange={e => setApplyForm({...applyForm, start_date: e.target.value})} />
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">End Date</label>
                <input type="date" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  value={applyForm.end_date} onChange={e => setApplyForm({...applyForm, end_date: e.target.value})} />
              </div>
            </div>
            <div className="flex gap-3">
              <Button onClick={applyLeave} disabled={applyLoading} className="bg-blue-600 text-white">
                {applyLoading ? "Submitting..." : "Submit Application"}
              </Button>
              <Button variant="outline" onClick={() => setShowApply(false)}>Cancel</Button>
            </div>
          </div>
        )}

        {/* Reject Modal */}
        {rejectId && (
          <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-96 space-y-4 shadow-xl">
              <h2 className="font-semibold text-gray-800">Reject Leave Request</h2>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Rejection Reason *</label>
                <textarea
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  rows={3}
                  value={rejectReason}
                  onChange={e => setRejectReason(e.target.value)}
                  placeholder="Provide a reason for rejection"
                />
              </div>
              <div className="flex gap-3">
                <Button onClick={rejectLeave} className="bg-red-600 hover:bg-red-700 text-white">Reject</Button>
                <Button variant="outline" onClick={() => { setRejectId(null); setRejectReason("") }}>Cancel</Button>
              </div>
            </div>
          </div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Total Requests", value: requests.length, color: "bg-blue-500" },
            { label: "Pending", value: pending, color: "bg-yellow-500" },
            { label: "Approved", value: approved, color: "bg-green-500" },
            { label: "Rejected", value: rejected, color: "bg-red-500" },
          ].map(s => (
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
            <button key={t} onClick={() => setTab(t as any)}
              className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                tab === t ? "bg-blue-600 text-white" : "bg-white border border-gray-200 text-gray-600"
              }`}>
              {t === "requests" ? "Leave Requests" : "Leave Balances"}
            </button>
          ))}
        </div>

        {/* Leave Requests */}
        {tab === "requests" && (
          <div className="space-y-4">
            <div className="flex gap-2">
              {["all", "pending", "approved", "rejected"].map(f => (
                <button key={f} onClick={() => setFilter(f)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                    filter === f ? "bg-blue-600 text-white" : "bg-white border border-gray-200 text-gray-600"
                  }`}>
                  {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
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
                  {loading ? (
                    <tr><td colSpan={7} className="px-6 py-12 text-center text-gray-400">Loading...</td></tr>
                  ) : filtered.length === 0 ? (
                    <tr><td colSpan={7} className="px-6 py-12 text-center text-gray-400">No leave requests found</td></tr>
                  ) : (
                    filtered.map(r => (
                      <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 text-sm font-medium text-gray-800 capitalize">{r.leave_type}</td>
                        <td className="px-6 py-4 text-sm text-gray-600">{r.start_date}</td>
                        <td className="px-6 py-4 text-sm text-gray-600">{r.end_date}</td>
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">{r.days_requested}</td>
                        <td className="px-6 py-4 text-sm text-gray-500 max-w-xs truncate">{r.reason || "—"}</td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[r.status]}`}>
                            {r.status}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          {r.status === "pending" ? (
                            <div className="flex gap-2">
                              <button onClick={() => approveLeave(r.id)} className="text-xs text-green-600 hover:underline font-medium">Approve</button>
                              <button onClick={() => setRejectId(r.id)} className="text-xs text-red-500 hover:underline">Reject</button>
                            </div>
                          ) : (
                            <span className="text-xs text-gray-400">—</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Leave Balances */}
        {tab === "balances" && (
          <div className="grid grid-cols-2 gap-4">
            {balances.length === 0 ? (
              <div className="col-span-2 bg-white rounded-xl p-8 text-center text-gray-400 border border-gray-100">
                No leave balance found — employee record required
              </div>
            ) : (
              balances.map(b => (
                <div key={b.leave_type} className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-gray-800 capitalize">{b.leave_type} Leave</h3>
                    <span className="text-sm text-gray-500">{b.remaining_days} remaining</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2 mb-3">
                    <div className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${b.allocated_days > 0 ? ((b.allocated_days - b.used_days) / b.allocated_days) * 100 : 0}%` }} />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Used: {b.used_days} days</span>
                    <span>Allocated: {b.allocated_days} days</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

      </div>
    </DashboardLayout>
  )
}
