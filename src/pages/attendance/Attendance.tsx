import DashboardLayout from "@/components/layout/DashboardLayout"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import axios from "axios"
import { apiHeaders } from "@/lib/auth"

const BASE = "http://localhost:8000/api/v1"

interface AttendanceRecord {
  id: string
  employee_id: string
  date: string
  check_in_time: string | null
  check_out_time: string | null
  status: string
  work_hours: number | null
  is_late: boolean
  notes: string | null
}

const statusColors: Record<string, string> = {
  present: "bg-green-100 text-green-700",
  absent: "bg-red-100 text-red-600",
  half_day: "bg-yellow-100 text-yellow-700",
  on_leave: "bg-blue-100 text-blue-600",
  holiday: "bg-purple-100 text-purple-700",
  weekend: "bg-gray-100 text-gray-500",
}

function formatTime(dt: string | null) {
  if (!dt) return "—"
  return new Date(dt).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
}

export default function Attendance() {
  const [records, setRecords] = useState<AttendanceRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [checkingIn, setCheckingIn] = useState(false)
  const [checkingOut, setCheckingOut] = useState(false)
  const [message, setMessage] = useState("")
  const [messageType, setMessageType] = useState<"success" | "error">("success")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")

  useEffect(() => {
    fetchAttendance()
  }, [])

  async function fetchAttendance() {
    try {
      let url = `${BASE}/attendance/me`
      const params = []
      if (startDate) params.push(`start_date=${startDate}`)
      if (endDate) params.push(`end_date=${endDate}`)
      if (params.length) url += `?${params.join("&")}`

      const res = await axios.get(url, { headers: apiHeaders() })
      setRecords(res.data.sort((a: AttendanceRecord, b: AttendanceRecord) =>
        new Date(b.date).getTime() - new Date(a.date).getTime()
      ))
    } catch (err) {
      console.error("Failed to fetch attendance", err)
    } finally {
      setLoading(false)
    }
  }

  async function checkIn() {
    setCheckingIn(true)
    setMessage("")
    try {
      await axios.post(`${BASE}/attendance/check-in`, {}, { headers: apiHeaders() })
      setMessage("✅ Checked in successfully!")
      setMessageType("success")
      fetchAttendance()
    } catch (err: any) {
      setMessage(`❌ ${err.response?.data?.error?.message || "Check-in failed"}`)
      setMessageType("error")
    } finally {
      setCheckingIn(false)
    }
  }

  async function checkOut() {
    setCheckingOut(true)
    setMessage("")
    try {
      await axios.post(`${BASE}/attendance/check-out`, {}, { headers: apiHeaders() })
      setMessage("✅ Checked out successfully!")
      setMessageType("success")
      fetchAttendance()
    } catch (err: any) {
      setMessage(`❌ ${err.response?.data?.error?.message || "Check-out failed"}`)
      setMessageType("error")
    } finally {
      setCheckingOut(false)
    }
  }

  const todayRecord = records.find(r => r.date === new Date().toISOString().split("T")[0])

  const present = records.filter(r => r.status === "present").length
  const absent = records.filter(r => r.status === "absent").length
  const late = records.filter(r => r.is_late).length
  const onLeave = records.filter(r => r.status === "on_leave").length

  return (
    <DashboardLayout>
      <div className="space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Attendance</h1>
            <p className="text-gray-500 text-sm mt-1">Track your daily attendance</p>
          </div>
          <div className="flex gap-3">
            <Button
              onClick={checkIn}
              disabled={checkingIn || !!todayRecord?.check_in_time}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              {checkingIn ? "Checking in..." : "✓ Check In"}
            </Button>
            <Button
              onClick={checkOut}
              disabled={checkingOut || !todayRecord?.check_in_time || !!todayRecord?.check_out_time}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {checkingOut ? "Checking out..." : "→ Check Out"}
            </Button>
          </div>
        </div>

        {/* Message */}
        {message && (
          <div className={`p-3 rounded-lg text-sm ${messageType === "success" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-600"}`}>
            {message}
          </div>
        )}

        {/* Today's Status */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
          <h2 className="font-semibold text-gray-800 mb-4">Today's Status</h2>
          {todayRecord ? (
            <div className="grid grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-400">Status</p>
                <span className={`inline-block mt-1 px-2 py-1 rounded-full text-xs font-medium ${statusColors[todayRecord.status]}`}>
                  {todayRecord.status.replace("_", " ")}
                </span>
              </div>
              <div>
                <p className="text-xs text-gray-400">Check In</p>
                <p className="text-sm font-medium text-gray-800 mt-1">{formatTime(todayRecord.check_in_time)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Check Out</p>
                <p className="text-sm font-medium text-gray-800 mt-1">{formatTime(todayRecord.check_out_time)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Work Hours</p>
                <p className="text-sm font-medium text-gray-800 mt-1">
                  {todayRecord.work_hours !== null ? `${todayRecord.work_hours.toFixed(1)}h` : "In progress"}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400">No attendance record for today — click Check In to start.</p>
          )}
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Present", value: present, color: "bg-green-500" },
            { label: "Absent", value: absent, color: "bg-red-500" },
            { label: "Late", value: late, color: "bg-yellow-500" },
            { label: "On Leave", value: onLeave, color: "bg-blue-500" },
          ].map(s => (
            <div key={s.label} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
              <div className={`w-8 h-8 ${s.color} rounded-lg mb-3`} />
              <p className="text-2xl font-bold text-gray-900">{s.value}</p>
              <p className="text-sm text-gray-500 mt-1">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Filter */}
        <div className="flex gap-3 items-center">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-500">From</label>
            <Input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="w-40" />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-500">To</label>
            <Input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="w-40" />
          </div>
          <Button onClick={fetchAttendance} variant="outline">Filter</Button>
          <Button onClick={() => { setStartDate(""); setEndDate(""); fetchAttendance() }} variant="outline">Clear</Button>
        </div>

        {/* Attendance Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-100">
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Date</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Check In</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Check Out</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Hours</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Late</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {loading ? (
                <tr><td colSpan={6} className="px-6 py-12 text-center text-gray-400">Loading...</td></tr>
              ) : records.length === 0 ? (
                <tr><td colSpan={6} className="px-6 py-12 text-center text-gray-400">No attendance records found</td></tr>
              ) : (
                records.map(r => (
                  <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 text-sm text-gray-800">{formatDate(r.date)}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[r.status]}`}>
                        {r.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{formatTime(r.check_in_time)}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{formatTime(r.check_out_time)}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {r.work_hours !== null ? `${r.work_hours.toFixed(1)}h` : "—"}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {r.is_late ? <span className="text-yellow-600">Late</span> : <span className="text-gray-400">—</span>}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

      </div>
    </DashboardLayout>
  )
}
