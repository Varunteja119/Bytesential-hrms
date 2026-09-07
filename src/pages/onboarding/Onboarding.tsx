import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import axios from "axios"
import { getToken } from "@/lib/auth"

const BASE = "http://localhost:8000/api/v1"

interface OnboardingStatus {
  credentials_generated: boolean
  password_changed: boolean
  profile_completed: boolean
  documents: { document_type: string; uploaded: boolean; verified: boolean }[]
  hr_verified: boolean
  employment_status: string
  ready_for_activation: boolean
}

interface EmployeeProfile {
  id: string
  employee_code: string
  full_name?: string
  department: string
  designation: string
  date_of_joining: string
  phone: string | null
  address: string | null
  date_of_birth: string | null
  gender: string | null
  aadhaar_number: string | null
  pan_number: string | null
  bank_account_number: string | null
  bank_ifsc: string | null
  bank_name: string | null
  profile_completed: boolean
}

const docTypes = [
  { value: "aadhaar", label: "Aadhaar Card" },
  { value: "pan", label: "PAN Card" },
  { value: "bank_proof", label: "Bank Proof" },
  { value: "education_certificate", label: "Education Certificate" },
  { value: "experience_certificate", label: "Experience Certificate" },
]

export default function Onboarding() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [status, setStatus] = useState<OnboardingStatus | null>(null)
  const [profile, setProfile] = useState<EmployeeProfile | null>(null)
  const [loading, setLoading] = useState(true)

  // Step 1 — Change password
  const [currentPass, setCurrentPass] = useState("")
  const [newPass, setNewPass] = useState("")
  const [passError, setPassError] = useState("")
  const [passLoading, setPassLoading] = useState(false)

  // Step 2 — Profile
  const [profileForm, setProfileForm] = useState({
    phone: "", address: "", date_of_birth: "",
    gender: "", aadhaar_number: "", pan_number: "",
    bank_account_number: "", bank_ifsc: "", bank_name: ""
  })
  const [profileError, setProfileError] = useState("")
  const [profileLoading, setProfileLoading] = useState(false)

  // Step 3 — Documents
  const [selectedDocType, setSelectedDocType] = useState("aadhaar")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadError, setUploadError] = useState("")
  const [uploadLoading, setUploadLoading] = useState(false)

  const headers = { Authorization: `Bearer ${getToken()}` }

  useEffect(() => {
    fetchData()
  }, [])

  async function fetchData() {
    try {
      const [profileRes, statusRes] = await Promise.all([
        axios.get(`${BASE}/employees/me`, { headers }),
        axios.get(`${BASE}/employees/me/onboarding-status`, { headers })
      ])
      setProfile(profileRes.data)
      setStatus(statusRes.data)

      // Pre-fill profile form
      const p = profileRes.data
      setProfileForm({
        phone: p.phone || "",
        address: p.address || "",
        date_of_birth: p.date_of_birth || "",
        gender: p.gender || "",
        aadhaar_number: p.aadhaar_number || "",
        pan_number: p.pan_number || "",
        bank_account_number: p.bank_account_number || "",
        bank_ifsc: p.bank_ifsc || "",
        bank_name: p.bank_name || ""
      })

      // Determine current step
      const s = statusRes.data
      if (!s.password_changed) setStep(1)
      else if (!s.profile_completed) setStep(2)
      else setStep(3)

    } catch (err) {
      console.error("Failed to load onboarding data", err)
    } finally {
      setLoading(false)
    }
  }

  async function changePassword() {
    if (!currentPass || !newPass) { setPassError("Fill in both fields"); return }
    if (newPass.length < 8) { setPassError("New password must be at least 8 characters"); return }
    setPassLoading(true); setPassError("")
    try {
      await axios.post(`${BASE}/auth/change-password`,
        { current_password: currentPass, new_password: newPass },
        { headers }
      )
      await fetchData()
    } catch (err: any) {
      setPassError(err.response?.data?.error?.message || "Failed to change password")
    } finally {
      setPassLoading(false)
    }
  }

  async function saveProfile() {
    setProfileLoading(true); setProfileError("")
    try {
      const payload: any = {}
      Object.entries(profileForm).forEach(([k, v]) => { if (v) payload[k] = v })
      await axios.patch(`${BASE}/employees/me`, payload, { headers })
      await fetchData()
    } catch (err: any) {
      setProfileError(err.response?.data?.error?.message || "Failed to save profile")
    } finally {
      setProfileLoading(false)
    }
  }

  async function uploadDocument() {
    if (!selectedFile || !profile) return
    setUploadLoading(true); setUploadError("")
    try {
      const formData = new FormData()
      formData.append("file", selectedFile)
      await axios.post(
        `${BASE}/employees/${profile.id}/documents?document_type=${selectedDocType}`,
        formData,
        { headers: { ...headers, "Content-Type": "multipart/form-data" } }
      )
      setSelectedFile(null)
      await fetchData()
    } catch (err: any) {
      setUploadError(err.response?.data?.error?.message || "Upload failed")
    } finally {
      setUploadLoading(false)
    }
  }

  function logout() {
    localStorage.clear()
    navigate("/login")
  }

  if (loading) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <p className="text-gray-400">Loading your onboarding...</p>
    </div>
  )

  const completedSteps = status ? [
    status.password_changed,
    status.profile_completed,
    status.documents.filter(d => d.uploaded).length >= 3
  ] : [false, false, false]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">ByteSentinel</h1>
          <p className="text-xs text-gray-400">New Employee Onboarding</p>
        </div>
        <div className="flex items-center gap-4">
          {profile && (
            <div className="text-right">
              <p className="text-sm font-medium text-gray-800">{profile.employee_code}</p>
              <p className="text-xs text-gray-400">{profile.designation} · {profile.department}</p>
            </div>
          )}
          <button onClick={logout} className="text-sm text-red-400 hover:text-red-600">Logout</button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto py-10 px-4 space-y-6">

        {/* Progress Steps */}
        <div className="flex items-center justify-between bg-white rounded-xl border border-gray-100 shadow-sm p-6">
          {["Set Password", "Complete Profile", "Upload Documents"].map((label, i) => (
            <div key={label} className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                completedSteps[i] ? "bg-green-500 text-white" :
                step === i + 1 ? "bg-blue-600 text-white" :
                "bg-gray-200 text-gray-400"
              }`}>
                {completedSteps[i] ? "✓" : i + 1}
              </div>
              <span className={`text-sm font-medium ${step === i + 1 ? "text-blue-600" : completedSteps[i] ? "text-green-600" : "text-gray-400"}`}>
                {label}
              </span>
              {i < 2 && <div className="w-16 h-0.5 bg-gray-200 mx-2" />}
            </div>
          ))}
        </div>

        {/* Step 1 — Change Password */}
        {step === 1 && (
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Set Your Password</h2>
            <p className="text-sm text-yellow-600 bg-yellow-50 p-3 rounded-lg">
              You must set a new password before continuing. Use the temporary password HR shared with you.
            </p>
            {passError && <div className="bg-red-50 text-red-600 text-sm p-3 rounded-md">{passError}</div>}
            <div className="space-y-2">
              <Label>Temporary Password</Label>
              <Input type="password" value={currentPass} onChange={e => setCurrentPass(e.target.value)} placeholder="Enter temp password from HR" />
            </div>
            <div className="space-y-2">
              <Label>New Password (min 8 characters)</Label>
              <Input type="password" value={newPass} onChange={e => setNewPass(e.target.value)} placeholder="Choose a strong password" />
            </div>
            <Button onClick={changePassword} disabled={passLoading} className="w-full bg-blue-600 hover:bg-blue-700 text-white">
              {passLoading ? "Saving..." : "Set New Password →"}
            </Button>
          </div>
        )}

        {/* Step 2 — Profile */}
        {step === 2 && (
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Complete Your Profile</h2>
            <p className="text-sm text-gray-500">Fill in your personal and banking details. All fields are required for activation.</p>
            {profileError && <div className="bg-red-50 text-red-600 text-sm p-3 rounded-md">{profileError}</div>}
            <div className="grid grid-cols-2 gap-4">
              {[
                { key: "phone", label: "Phone Number", placeholder: "+91-9876543210" },
                { key: "date_of_birth", label: "Date of Birth", type: "date", placeholder: "" },
                { key: "gender", label: "Gender", placeholder: "male / female / other" },
                { key: "aadhaar_number", label: "Aadhaar Number", placeholder: "XXXX-XXXX-1234" },
                { key: "pan_number", label: "PAN Number", placeholder: "ABCDE1234F" },
                { key: "bank_account_number", label: "Bank Account Number", placeholder: "123456789012" },
                { key: "bank_ifsc", label: "Bank IFSC Code", placeholder: "HDFC0001234" },
                { key: "bank_name", label: "Bank Name", placeholder: "HDFC Bank" },
              ].map(field => (
                <div key={field.key} className="space-y-1">
                  <Label>{field.label}</Label>
                  <Input
                    type={field.type || "text"}
                    placeholder={field.placeholder}
                    value={(profileForm as any)[field.key]}
                    onChange={e => setProfileForm({...profileForm, [field.key]: e.target.value})}
                  />
                </div>
              ))}
            </div>
            <div className="space-y-1">
              <Label>Address</Label>
              <textarea
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                rows={2}
                placeholder="Full residential address"
                value={profileForm.address}
                onChange={e => setProfileForm({...profileForm, address: e.target.value})}
              />
            </div>
            <Button onClick={saveProfile} disabled={profileLoading} className="w-full bg-blue-600 hover:bg-blue-700 text-white">
              {profileLoading ? "Saving..." : "Save Profile →"}
            </Button>
          </div>
        )}

        {/* Step 3 — Documents */}
        {step === 3 && (
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Upload Documents</h2>
            <p className="text-sm text-gray-500">Upload Aadhaar, PAN, and Bank Proof to complete onboarding. HR will verify them.</p>

            {/* Document Status */}
            <div className="grid grid-cols-3 gap-3">
              {status?.documents.map(doc => (
                <div key={doc.document_type} className={`p-3 rounded-lg border text-center ${
                  doc.verified ? "bg-green-50 border-green-200" :
                  doc.uploaded ? "bg-yellow-50 border-yellow-200" :
                  "bg-gray-50 border-gray-200"
                }`}>
                  <p className="text-xs font-medium capitalize text-gray-700">{doc.document_type.replace("_", " ")}</p>
                  <p className="text-xs mt-1">
                    {doc.verified ? "✅ Verified" : doc.uploaded ? "⏳ Pending HR" : "❌ Not uploaded"}
                  </p>
                </div>
              ))}
            </div>

            {uploadError && <div className="bg-red-50 text-red-600 text-sm p-3 rounded-md">{uploadError}</div>}

            <div className="space-y-3 border border-gray-100 rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-700">Upload a Document</h3>
              <div className="space-y-1">
                <Label>Document Type</Label>
                <select
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  value={selectedDocType}
                  onChange={e => setSelectedDocType(e.target.value)}
                >
                  {docTypes.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <Label>File (PDF or image)</Label>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={e => setSelectedFile(e.target.files?.[0] || null)}
                  className="w-full text-sm text-gray-500 file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:bg-blue-50 file:text-blue-600 hover:file:bg-blue-100"
                />
              </div>
              <Button
                onClick={uploadDocument}
                disabled={!selectedFile || uploadLoading}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white"
              >
                {uploadLoading ? "Uploading..." : "Upload Document"}
              </Button>
            </div>

            {status?.employment_status === "active" && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                <p className="text-green-700 font-semibold">🎉 Your account has been activated!</p>
                <p className="text-green-600 text-sm mt-1">HR has verified your documents and activated your account.</p>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  )
}
