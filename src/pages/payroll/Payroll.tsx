import DashboardLayout from "@/components/layout/DashboardLayout"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import axios from "axios"
import { apiHeaders } from "@/lib/auth"

const BASE = "http://localhost:8000/api/v1"

interface PayrollRun {
  id: string
  period_year: number
  period_month: number
  status: string
  hr_approved_by_id: string | null
  finance_approved_by_id: string | null
  paid_at: string | null
  payslip_count: number
}

interface Payslip {
  id: string
  employee_id: string
  basic: number
  hra: number
  other_allowances: number
  overtime_amount: number
  bonus_amount: number
  gross_salary: number
  days_in_period: number
  days_present: number
  days_on_leave: number
  days_lop: number
  pf_deduction: number
  esi_deduction: number
  pt_deduction: number
  tds_amount: number
  net_salary: number
}

const statusConfig: Record<string, { label: string, color: string }> = {
  draft: { label: "Draft", color: "bg-yellow-100 text-yellow-700" },
  hr_approved: { label: "HR Approved", color: "bg-blue-100 text-blue-700" },
  finance_approved: { label: "Finance Approved", color: "bg-purple-100 text-purple-700" },
  paid: { label: "Paid", color: "bg-green-100 text-green-700" },
}

const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

const fmt = (n: number) => `₹${n.toLocaleString("en-IN")}`

export default function Payroll() {
  const [runs, setRuns] = useState<PayrollRun[]>([])
  const [selectedRun, setSelectedRun] = useState<PayrollRun | null>(null)
  const [payslips, setPayslips] = useState<Payslip[]>([])
  const [loading, setLoading] = useState(true)
  const [payslipsLoading, setPayslipsLoading] = useState(false)

  // Create run form
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({
    period_year: new Date().getFullYear(),
    period_month: new Date().getMonth() + 1
  })
  const [createLoading, setCreateLoading] = useState(false)
  const [createError, setCreateError] = useState("")

  useEffect(() => {
    fetchRuns()
  }, [])

  async function fetchRuns() {
    try {
      const res = await axios.get(`${BASE}/payroll/runs`, { headers: apiHeaders() })
      setRuns(res.data)
    } catch (err) {
      console.error("Failed to fetch payroll runs", err)
    } finally {
      setLoading(false)
    }
  }

  async function fetchPayslips(runId: string) {
    setPayslipsLoading(true)
    try {
      const res = await axios.get(`${BASE}/payroll/runs/${runId}/payslips`, { headers: apiHeaders() })
      setPayslips(res.data)
    } catch (err) {
      console.error("Failed to fetch payslips", err)
    } finally {
      setPayslipsLoading(false)
    }
  }

  async function createRun() {
    setCreateLoading(true)
    setCreateError("")
    try {
      await axios.post(`${BASE}/payroll/runs`, createForm, { headers: apiHeaders() })
      setShowCreate(false)
      fetchRuns()
    } catch (err: any) {
      setCreateError(err.response?.data?.error?.message || "Failed to create payroll run")
    } finally {
      setCreateLoading(false)
    }
  }

  async function approveHR(runId: string) {
    try {
      await axios.post(`${BASE}/payroll/runs/${runId}/approve-hr`, {}, { headers: apiHeaders() })
      fetchRuns()
      if (selectedRun?.id === runId) {
        const res = await axios.get(`${BASE}/payroll/runs/${runId}`, { headers: apiHeaders() })
        setSelectedRun(res.data)
      }
    } catch (err: any) {
      alert(err.response?.data?.error?.message || "Failed to approve")
    }
  }

  async function approveFinance(runId: string) {
    try {
      await axios.post(`${BASE}/payroll/runs/${runId}/approve-finance`, {}, { headers: apiHeaders() })
      fetchRuns()
      if (selectedRun?.id === runId) {
        const res = await axios.get(`${BASE}/payroll/runs/${runId}`, { headers: apiHeaders() })
        setSelectedRun(res.data)
      }
    } catch (err: any) {
      alert(err.response?.data?.error?.message || "Failed to approve")
    }
  }

  async function markPaid(runId: string) {
    try {
      await axios.post(`${BASE}/payroll/runs/${runId}/mark-paid`, {}, { headers: apiHeaders() })
      fetchRuns()
      if (selectedRun?.id === runId) {
        const res = await axios.get(`${BASE}/payroll/runs/${runId}`, { headers: apiHeaders() })
        setSelectedRun(res.data)
      }
    } catch (err: any) {
      alert(err.response?.data?.error?.message || "Failed to mark paid")
    }
  }

  function openRun(run: PayrollRun) {
    setSelectedRun(run)
    fetchPayslips(run.id)
  }

  const totalGross = payslips.reduce((a, b) => a + b.gross_salary, 0)
  const totalNet = payslips.reduce((a, b) => a + b.net_salary, 0)
  const totalPF = payslips.reduce((a, b) => a + b.pf_deduction, 0)
  const totalTDS = payslips.reduce((a, b) => a + b.tds_amount, 0)

  return (
    <DashboardLayout>
      <div className="space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Payroll</h1>
            <p className="text-gray-500 text-sm mt-1">{runs.length} payroll runs</p>
          </div>
          <Button className="bg-blue-600 hover:bg-blue-700 text-white" onClick={() => setShowCreate(!showCreate)}>
            + Create Payroll Run
          </Button>
        </div>

        {/* Create Run Form */}
        {showCreate && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
            <h2 className="font-semibold text-gray-800">Create New Payroll Run</h2>
            {createError && <div className="bg-red-50 text-red-600 text-sm p-3 rounded-md">{createError}</div>}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Year</Label>
                <Input
                  type="number"
                  value={createForm.period_year}
                  onChange={e => setCreateForm({...createForm, period_year: parseInt(e.target.value)})}
                  min={2020} max={2100}
                />
              </div>
              <div className="space-y-2">
                <Label>Month</Label>
                <select
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  value={createForm.period_month}
                  onChange={e => setCreateForm({...createForm, period_month: parseInt(e.target.value)})}
                >
                  {months.map((m, i) => (
                    <option key={m} value={i + 1}>{m}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex gap-3">
              <Button onClick={createRun} disabled={createLoading} className="bg-blue-600 text-white">
                {createLoading ? "Creating..." : "Create Run"}
              </Button>
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-3 gap-6">

          {/* Payroll Runs List */}
          <div className="col-span-1 bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
              <h2 className="text-sm font-semibold text-gray-700">Payroll Runs</h2>
            </div>
            {loading ? (
              <div className="p-6 text-center text-gray-400 text-sm">Loading...</div>
            ) : runs.length === 0 ? (
              <div className="p-6 text-center text-gray-400 text-sm">No payroll runs yet</div>
            ) : (
              <div className="divide-y divide-gray-50">
                {runs.map(run => {
                  const conf = statusConfig[run.status]
                  return (
                    <button
                      key={run.id}
                      onClick={() => openRun(run)}
                      className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${selectedRun?.id === run.id ? "bg-blue-50 border-l-4 border-blue-600" : ""}`}
                    >
                      <p className="text-sm font-medium text-gray-900">
                        {months[run.period_month - 1]} {run.period_year}
                      </p>
                      <p className="text-xs text-gray-400 mt-0.5">{run.payslip_count} payslips</p>
                      <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${conf.color}`}>
                        {conf.label}
                      </span>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Payroll Run Detail */}
          <div className="col-span-2 space-y-4">
            {!selectedRun ? (
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-12 text-center text-gray-400">
                Select a payroll run to view details
              </div>
            ) : (
              <>
                {/* Run Status + Actions */}
                <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h2 className="font-semibold text-gray-800">
                        {months[selectedRun.period_month - 1]} {selectedRun.period_year}
                      </h2>
                      <span className={`inline-block mt-1 px-2 py-1 rounded-full text-xs font-medium ${statusConfig[selectedRun.status].color}`}>
                        {statusConfig[selectedRun.status].label}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      {selectedRun.status === "draft" && (
                        <Button onClick={() => approveHR(selectedRun.id)} className="bg-blue-600 hover:bg-blue-700 text-white text-sm">
                          HR Approve
                        </Button>
                      )}
                      {selectedRun.status === "hr_approved" && (
                        <Button onClick={() => approveFinance(selectedRun.id)} className="bg-purple-600 hover:bg-purple-700 text-white text-sm">
                          Finance Approve
                        </Button>
                      )}
                      {selectedRun.status === "finance_approved" && (
                        <Button onClick={() => markPaid(selectedRun.id)} className="bg-green-600 hover:bg-green-700 text-white text-sm">
                          Mark as Paid
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Summary */}
                  <div className="grid grid-cols-4 gap-4">
                    {[
                      { label: "Total Gross", value: fmt(totalGross) },
                      { label: "Total Net", value: fmt(totalNet) },
                      { label: "Total PF", value: fmt(totalPF) },
                      { label: "Total TDS", value: fmt(totalTDS) },
                    ].map(s => (
                      <div key={s.label} className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-400">{s.label}</p>
                        <p className="text-sm font-bold text-gray-800 mt-1">{s.value}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Payslips Table */}
                <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
                    <h2 className="text-sm font-semibold text-gray-700">Payslips ({payslips.length})</h2>
                  </div>
                  {payslipsLoading ? (
                    <div className="p-6 text-center text-gray-400">Loading payslips...</div>
                  ) : payslips.length === 0 ? (
                    <div className="p-6 text-center text-gray-400 text-sm">No payslips in this run</div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="bg-gray-50 border-b border-gray-100">
                            <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Basic</th>
                            <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">HRA</th>
                            <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Gross</th>
                            <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">PF</th>
                            <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">TDS</th>
                            <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">LOP Days</th>
                            <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Net Pay</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                          {payslips.map(p => (
                            <tr key={p.id} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm text-right text-gray-600">{fmt(p.basic)}</td>
                              <td className="px-4 py-3 text-sm text-right text-gray-600">{fmt(p.hra)}</td>
                              <td className="px-4 py-3 text-sm text-right font-medium text-gray-800">{fmt(p.gross_salary)}</td>
                              <td className="px-4 py-3 text-sm text-right text-red-500">-{fmt(p.pf_deduction)}</td>
                              <td className="px-4 py-3 text-sm text-right text-red-500">-{fmt(p.tds_amount)}</td>
                              <td className="px-4 py-3 text-sm text-right text-gray-600">{p.days_lop}</td>
                              <td className="px-4 py-3 text-sm text-right font-bold text-green-600">{fmt(p.net_salary)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
