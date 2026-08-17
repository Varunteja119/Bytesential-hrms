import DashboardLayout from "@/components/layout/DashboardLayout"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import axios from "axios"
import { apiHeaders } from "@/lib/auth"

const BASE = "http://localhost:8000/api/v1"

interface Employee {
  id: string
  employee_code: string
  department: string
  designation: string
  employment_status: string
  profile_completed: boolean
  hr_verified: boolean
  phone: string | null
  date_of_joining: string
}

interface Document {
  id: string
  document_type: string
  original_filename: string
  verified: boolean
}

interface OnboardingStatus {
  credentials_generated: boolean
  password_changed: boolean
  profile_completed: boolean
  documents: { document_type: string; uploaded: boolean; verified: boolean }[]
  hr_verified: boolean
  employment_status: string
  ready_for_activation: boolean
}

export default function VerificationQueue() {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [selected, setSelected] = useState<Employee | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [activating, setActivating] = useState(false)
  const [activateMsg, setActivateMsg] = useState("")

  useEffect(() => {
    fetchEmployees()
  }, [])

  async function fetchEmployees() {
    try {
      const res = await axios.get(`${BASE}/employees`, { headers: apiHeaders() })
      // Only show pending activation employees
      const pending = res.data.filter((e: Employee) =>
        e.employment_status === "pending_activation"
      )
      setEmployees(pending)
    } catch (err) {
      console.error("Failed to fetch employees", err)
    } finally {
      setLoading(false)
    }
  }

  async function openEmployee(emp: Employee) {
    setSelected(emp)
    setActivateMsg("")
    try {
      const [docsRes, onboardRes] = await Promise.all([
        axios.get(`${BASE}/employees/${emp.id}/documents`, { headers: apiHeaders() }),
        axios.get(`${BASE}/employees/${emp.id}/onboarding-status`, { headers: apiHeaders() })
      ])
      setDocuments(docsRes.data)
      setOnboarding(onboardRes.data)
    } catch (err) {
      console.error("Failed to fetch employee details", err)
    }
  }

  async function verifyDocument(docId: string) {
    if (!selected) return
    try {
      await axios.patch(
        `${BASE}/employees/${selected.id}/documents/${docId}/verify`,
        {},
        { headers: apiHeaders() }
      )
      // Refresh documents and onboarding status
      const [docsRes, onboardRes] = await Promise.all([
        axios.get(`${BASE}/employees/${selected.id}/documents`, { headers: apiHeaders() }),
        axios.get(`${BASE}/employees/${selected.id}/onboarding-status`, { headers: apiHeaders() })
      ])
      setDocuments(docsRes.data)
      setOnboarding(onboardRes.data)
    } catch (err) {
      console.error("Failed to verify document", err)
    }
  }

  async function activateEmployee() {
    if (!selected) return
    setActivating(true)
    setActivateMsg("")
    try {
      await axios.post(
        `${BASE}/employees/${selected.id}/activate`,
        {},
        { headers: apiHeaders() }
      )
      setActivateMsg("✅ Employee activated successfully!")
      fetchEmployees()
      setSelected(null)
    } catch (err: any) {
      const msg = err.response?.data?.error?.message || "Activation failed"
      setActivateMsg(`❌ ${msg}`)
    } finally {
      setActivating(false)
    }
  }

  const checkItem = (done: boolean, label: string) => (
    <div className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
      <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${done ? "bg-green-500 text-white" : "bg-gray-200 text-gray-400"}`}>
        {done ? "✓" : "○"}
      </div>
      <span className={`text-sm ${done ? "text-gray-800" : "text-gray-400"}`}>{label}</span>
    </div>
  )

  return (
    <DashboardLayout>
      <div className="space-y-6">

        <div>
          <h1 className="text-2xl font-bold text-gray-900">HR Verification Queue</h1>
          <p className="text-gray-500 text-sm mt-1">
            {employees.length} employee{employees.length !== 1 ? "s" : ""} pending activation
          </p>
        </div>

        <div className="grid grid-cols-3 gap-6">

          {/* Employee List */}
          <div className="col-span-1 bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
              <h2 className="text-sm font-semibold text-gray-700">Pending Activation</h2>
            </div>
            {loading ? (
              <div className="p-6 text-center text-gray-400 text-sm">Loading...</div>
            ) : employees.length === 0 ? (
              <div className="p-6 text-center text-gray-400 text-sm">No employees pending activation</div>
            ) : (
              <div className="divide-y divide-gray-50">
                {employees.map(emp => (
                  <button
                    key={emp.id}
                    onClick={() => openEmployee(emp)}
                    className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${selected?.id === emp.id ? "bg-blue-50 border-l-4 border-blue-600" : ""}`}
                  >
                    <p className="text-sm font-medium text-gray-900">{emp.employee_code}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{emp.designation}</p>
                    <p className="text-xs text-gray-400">{emp.department}</p>
                    <span className="inline-block mt-1 px-2 py-0.5 rounded-full text-xs bg-yellow-100 text-yellow-700">
                      Pending
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Employee Detail */}
          <div className="col-span-2 space-y-4">
            {!selected ? (
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-12 text-center text-gray-400">
                Select an employee from the list to review their onboarding
              </div>
            ) : (
              <>
                {/* Onboarding Checklist */}
                {onboarding && (
                  <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
                    <h2 className="font-semibold text-gray-800 mb-4">Onboarding Checklist — {selected.employee_code}</h2>
                    {checkItem(onboarding.credentials_generated, "Credentials generated")}
                    {checkItem(onboarding.password_changed, "Password changed by employee")}
                    {checkItem(onboarding.profile_completed, "Profile completed by employee")}
                    {onboarding.documents.map(doc => (
                      checkItem(doc.verified, `${doc.document_type.replace("_", " ")} — uploaded & verified`)
                    ))}

                    {activateMsg && (
                      <div className={`mt-4 p-3 rounded-lg text-sm ${activateMsg.startsWith("✅") ? "bg-green-50 text-green-700" : "bg-red-50 text-red-600"}`}>
                        {activateMsg}
                      </div>
                    )}

                    <div className="mt-4">
                      <Button
                        onClick={activateEmployee}
                        disabled={activating}
                        className={`w-full ${onboarding.ready_for_activation ? "bg-green-600 hover:bg-green-700" : "bg-gray-300 cursor-not-allowed"} text-white`}
                      >
                        {activating ? "Activating..." : onboarding.ready_for_activation ? "✓ Activate Employee" : "Complete all steps to activate"}
                      </Button>
                    </div>
                  </div>
                )}

                {/* Documents */}
                <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
                  <h2 className="font-semibold text-gray-800 mb-4">Uploaded Documents</h2>
                  {documents.length === 0 ? (
                    <p className="text-sm text-gray-400">No documents uploaded yet</p>
                  ) : (
                    <div className="space-y-3">
                      {documents.map(doc => (
                        <div key={doc.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div>
                            <p className="text-sm font-medium text-gray-800 capitalize">
                              {doc.document_type.replace("_", " ")}
                            </p>
                            <p className="text-xs text-gray-400">{doc.original_filename}</p>
                          </div>
                          <div className="flex items-center gap-3">
                            {doc.verified ? (
                              <span className="px-2 py-1 rounded-full text-xs bg-green-100 text-green-700 font-medium">
                                ✓ Verified
                              </span>
                            ) : (
                              <button
                                onClick={() => verifyDocument(doc.id)}
                                className="px-3 py-1 rounded-lg text-xs bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                              >
                                Verify
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
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
