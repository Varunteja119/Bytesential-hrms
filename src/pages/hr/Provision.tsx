import DashboardLayout from "@/components/layout/DashboardLayout"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import axios from "axios"
import { apiHeaders } from "@/lib/auth"

const BASE = "http://localhost:8000/api/v1"

interface Candidate {
  id: string
  full_name: string
  email: string
  status: string
  job_id: string
}

interface ProvisionResult {
  employee: {
    id: string
    employee_code: string
    department: string
    designation: string
    date_of_joining: string
  }
  temp_password: string
}

export default function Provision() {
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Candidate | null>(null)
  const [form, setForm] = useState({
    department: "",
    designation: "",
    date_of_joining: new Date().toISOString().split("T")[0]
  })
  const [provisioning, setProvisioning] = useState(false)
  const [result, setResult] = useState<ProvisionResult | null>(null)
  const [error, setError] = useState("")

  useEffect(() => {
    fetchAcceptedCandidates()
  }, [])

  async function fetchAcceptedCandidates() {
    try {
      const res = await axios.get(`${BASE}/recruitment/candidates`, { headers: apiHeaders() })
      const accepted = res.data.filter((c: Candidate) => c.status === "accepted")
      setCandidates(accepted)
    } catch (err) {
      console.error("Failed to fetch candidates", err)
    } finally {
      setLoading(false)
    }
  }

  async function handleProvision() {
    if (!selected || !form.department || !form.designation || !form.date_of_joining) {
      setError("Please fill in all fields")
      return
    }

    setProvisioning(true)
    setError("")
    setResult(null)

    try {
      const res = await axios.post(
        `${BASE}/employees/provision`,
        {
          candidate_id: selected.id,
          department: form.department,
          designation: form.designation,
          date_of_joining: form.date_of_joining
        },
        { headers: apiHeaders() }
      )
      setResult(res.data)
      // Remove from list
      setCandidates(prev => prev.filter(c => c.id !== selected.id))
      setSelected(null)
    } catch (err: any) {
      setError(err.response?.data?.error?.message || "Provisioning failed")
    } finally {
      setProvisioning(false)
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">

        <div>
          <h1 className="text-2xl font-bold text-gray-900">Employee Provisioning</h1>
          <p className="text-gray-500 text-sm mt-1">
            Convert accepted candidates into employees
          </p>
        </div>

        {/* Success Result */}
        {result && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-green-800 mb-3">✅ Employee Provisioned Successfully</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-green-600 font-medium">Employee Code</p>
                <p className="text-green-900 font-bold text-lg">{result.employee.employee_code}</p>
              </div>
              <div>
                <p className="text-green-600 font-medium">Department</p>
                <p className="text-green-900">{result.employee.department}</p>
              </div>
              <div>
                <p className="text-green-600 font-medium">Designation</p>
                <p className="text-green-900">{result.employee.designation}</p>
              </div>
              <div>
                <p className="text-green-600 font-medium">Joining Date</p>
                <p className="text-green-900">{result.employee.date_of_joining}</p>
              </div>
            </div>
            <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-sm font-semibold text-yellow-800">⚠️ Temporary Password — Copy Now</p>
              <p className="text-xs text-yellow-600 mt-1">This password will never be shown again. Share it with the employee securely.</p>
              <code className="block mt-2 text-lg font-bold text-yellow-900 bg-yellow-100 px-4 py-2 rounded">
                {result.temp_password}
              </code>
            </div>
            <Button
              className="mt-4 bg-green-600 hover:bg-green-700 text-white"
              onClick={() => setResult(null)}
            >
              Provision Another
            </Button>
          </div>
        )}

        <div className="grid grid-cols-2 gap-6">

          {/* Accepted Candidates List */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
              <h2 className="text-sm font-semibold text-gray-700">Accepted Candidates</h2>
            </div>
            {loading ? (
              <div className="p-6 text-center text-gray-400 text-sm">Loading...</div>
            ) : candidates.length === 0 ? (
              <div className="p-6 text-center text-gray-400 text-sm">
                No accepted candidates — move candidates to accepted in Recruitment first
              </div>
            ) : (
              <div className="divide-y divide-gray-50">
                {candidates.map(c => (
                  <button
                    key={c.id}
                    onClick={() => { setSelected(c); setError("") }}
                    className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
                      selected?.id === c.id ? "bg-blue-50 border-l-4 border-blue-600" : ""
                    }`}
                  >
                    <p className="text-sm font-medium text-gray-900">{c.full_name}</p>
                    <p className="text-xs text-gray-400">{c.email}</p>
                    <span className="inline-block mt-1 px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">
                      Accepted
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Provision Form */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
            <h2 className="font-semibold text-gray-800 mb-4">
              {selected ? `Provision — ${selected.full_name}` : "Select a candidate to provision"}
            </h2>

            {!selected ? (
              <p className="text-sm text-gray-400">Click a candidate from the list to fill in their employment details.</p>
            ) : (
              <div className="space-y-4">
                {error && (
                  <div className="bg-red-50 text-red-600 text-sm p-3 rounded-md">{error}</div>
                )}

                <div className="space-y-2">
                  <Label>Department *</Label>
                  <Input
                    value={form.department}
                    onChange={e => setForm({...form, department: e.target.value})}
                    placeholder="e.g. Engineering"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Designation *</Label>
                  <Input
                    value={form.designation}
                    onChange={e => setForm({...form, designation: e.target.value})}
                    placeholder="e.g. Backend Engineer"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Date of Joining *</Label>
                  <Input
                    type="date"
                    value={form.date_of_joining}
                    onChange={e => setForm({...form, date_of_joining: e.target.value})}
                  />
                </div>

                <Button
                  onClick={handleProvision}
                  disabled={provisioning}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {provisioning ? "Provisioning..." : "Provision as Employee"}
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
