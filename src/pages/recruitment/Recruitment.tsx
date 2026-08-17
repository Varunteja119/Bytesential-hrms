import DashboardLayout from "@/components/layout/DashboardLayout"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import axios from "axios"
import { apiHeaders } from "@/lib/auth"

const BASE = "http://localhost:8000/api/v1"

type JobStatus = "draft" | "open" | "closed"
type CandidateStatus = "applied" | "screening" | "interview" | "hr_approval" | "offered" | "accepted" | "rejected" | "withdrawn"

interface Job {
  id: string
  title: string
  department: string
  description: string
  requirements: string | null
  status: JobStatus
  candidate_count: number
}

interface Candidate {
  id: string
  full_name: string
  email: string
  phone: string | null
  job_id: string
  status: CandidateStatus
  ai_score: number | null
  ai_summary: string | null
  notes: string | null
}

const statusColors: Record<string, string> = {
  applied: "bg-gray-100 text-gray-600",
  screening: "bg-blue-100 text-blue-600",
  interview: "bg-yellow-100 text-yellow-700",
  hr_approval: "bg-purple-100 text-purple-700",
  offered: "bg-indigo-100 text-indigo-700",
  accepted: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-600",
  withdrawn: "bg-gray-100 text-gray-400",
}

const nextStatus: Record<string, CandidateStatus[]> = {
  applied: ["screening", "rejected", "withdrawn"],
  screening: ["interview", "rejected", "withdrawn"],
  interview: ["hr_approval", "rejected", "withdrawn"],
  hr_approval: ["offered", "rejected", "withdrawn"],
  offered: ["accepted", "rejected", "withdrawn"],
}

export default function Recruitment() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState<"jobs" | "candidates">("jobs")
  const [search, setSearch] = useState("")

  // Create job form
  const [showJobForm, setShowJobForm] = useState(false)
  const [jobForm, setJobForm] = useState({ title: "", department: "", description: "", requirements: "" })
  const [jobLoading, setJobLoading] = useState(false)

  // Add candidate form
  const [showCandidateForm, setShowCandidateForm] = useState(false)
  const [candidateForm, setCandidateForm] = useState({ full_name: "", email: "", phone: "", notes: "" })
  const [candidateLoading, setCandidateLoading] = useState(false)

  useEffect(() => {
    fetchJobs()
  }, [])

  async function fetchJobs() {
    try {
      const res = await axios.get(`${BASE}/recruitment/jobs`, { headers: apiHeaders() })
      setJobs(res.data)
    } catch (err) {
      console.error("Failed to fetch jobs", err)
    } finally {
      setLoading(false)
    }
  }

  async function fetchCandidates(jobId?: string) {
    try {
      const url = jobId
        ? `${BASE}/recruitment/candidates?job_id=${jobId}`
        : `${BASE}/recruitment/candidates`
      const res = await axios.get(url, { headers: apiHeaders() })
      setCandidates(res.data)
    } catch (err) {
      console.error("Failed to fetch candidates", err)
    }
  }

  async function createJob() {
    if (!jobForm.title || !jobForm.department || !jobForm.description) return
    setJobLoading(true)
    try {
      await axios.post(`${BASE}/recruitment/jobs`, jobForm, { headers: apiHeaders() })
      setShowJobForm(false)
      setJobForm({ title: "", department: "", description: "", requirements: "" })
      fetchJobs()
    } catch (err) {
      console.error("Failed to create job", err)
    } finally {
      setJobLoading(false)
    }
  }

  async function updateJobStatus(jobId: string, status: JobStatus) {
    try {
      await axios.patch(`${BASE}/recruitment/jobs/${jobId}`, { status }, { headers: apiHeaders() })
      fetchJobs()
    } catch (err) {
      console.error("Failed to update job", err)
    }
  }

  async function createCandidate() {
    if (!selectedJob || !candidateForm.full_name || !candidateForm.email) return
    setCandidateLoading(true)
    try {
      await axios.post(`${BASE}/recruitment/candidates`, {
        ...candidateForm,
        job_id: selectedJob.id
      }, { headers: apiHeaders() })
      setShowCandidateForm(false)
      setCandidateForm({ full_name: "", email: "", phone: "", notes: "" })
      fetchCandidates(selectedJob.id)
    } catch (err) {
      console.error("Failed to create candidate", err)
    } finally {
      setCandidateLoading(false)
    }
  }

  async function moveCandidate(candidateId: string, status: CandidateStatus) {
    try {
      await axios.patch(
        `${BASE}/recruitment/candidates/${candidateId}/status`,
        { status },
        { headers: apiHeaders() }
      )
      if (selectedJob) fetchCandidates(selectedJob.id)
    } catch (err: any) {
      alert(err.response?.data?.error?.message || "Failed to move candidate")
    }
  }

  function openJob(job: Job) {
    setSelectedJob(job)
    setView("candidates")
    fetchCandidates(job.id)
  }

  const filteredJobs = jobs.filter(j =>
    j.title.toLowerCase().includes(search.toLowerCase()) ||
    j.department.toLowerCase().includes(search.toLowerCase())
  )

  const filteredCandidates = candidates.filter(c =>
    c.full_name.toLowerCase().includes(search.toLowerCase()) ||
    c.email.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <DashboardLayout>
      <div className="space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {view === "jobs" ? "Recruitment" : `Candidates — ${selectedJob?.title}`}
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              {view === "jobs" ? `${jobs.length} open positions` : `${candidates.length} candidates`}
            </p>
          </div>
          <div className="flex gap-3">
            {view === "candidates" && (
              <Button variant="outline" onClick={() => { setView("jobs"); setSearch("") }}>
                ← Back to Jobs
              </Button>
            )}
            {view === "jobs" && (
              <Button className="bg-blue-600 hover:bg-blue-700 text-white" onClick={() => setShowJobForm(true)}>
                + Post Job
              </Button>
            )}
            {view === "candidates" && (
              <Button className="bg-blue-600 hover:bg-blue-700 text-white" onClick={() => setShowCandidateForm(true)}>
                + Add Candidate
              </Button>
            )}
          </div>
        </div>

        {/* Search */}
        <Input
          placeholder={view === "jobs" ? "Search jobs..." : "Search candidates..."}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />

        {/* Create Job Form */}
        {showJobForm && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
            <h2 className="font-semibold text-gray-800">Post New Job</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Job Title *</label>
                <Input value={jobForm.title} onChange={e => setJobForm({...jobForm, title: e.target.value})} placeholder="e.g. Backend Engineer" />
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Department *</label>
                <Input value={jobForm.department} onChange={e => setJobForm({...jobForm, department: e.target.value})} placeholder="e.g. Engineering" />
              </div>
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">Description *</label>
              <textarea
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                rows={3}
                value={jobForm.description}
                onChange={e => setJobForm({...jobForm, description: e.target.value})}
                placeholder="Job description..."
              />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">Requirements</label>
              <textarea
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                rows={2}
                value={jobForm.requirements}
                onChange={e => setJobForm({...jobForm, requirements: e.target.value})}
                placeholder="Required skills and experience..."
              />
            </div>
            <div className="flex gap-3">
              <Button onClick={createJob} disabled={jobLoading} className="bg-blue-600 text-white">
                {jobLoading ? "Creating..." : "Create Job"}
              </Button>
              <Button variant="outline" onClick={() => setShowJobForm(false)}>Cancel</Button>
            </div>
          </div>
        )}

        {/* Add Candidate Form */}
        {showCandidateForm && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
            <h2 className="font-semibold text-gray-800">Add Candidate</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Full Name *</label>
                <Input value={candidateForm.full_name} onChange={e => setCandidateForm({...candidateForm, full_name: e.target.value})} placeholder="Candidate name" />
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Email *</label>
                <Input type="email" value={candidateForm.email} onChange={e => setCandidateForm({...candidateForm, email: e.target.value})} placeholder="candidate@email.com" />
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Phone</label>
                <Input value={candidateForm.phone} onChange={e => setCandidateForm({...candidateForm, phone: e.target.value})} placeholder="+91-9876543210" />
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Notes</label>
                <Input value={candidateForm.notes} onChange={e => setCandidateForm({...candidateForm, notes: e.target.value})} placeholder="Any notes..." />
              </div>
            </div>
            <div className="flex gap-3">
              <Button onClick={createCandidate} disabled={candidateLoading} className="bg-blue-600 text-white">
                {candidateLoading ? "Adding..." : "Add Candidate"}
              </Button>
              <Button variant="outline" onClick={() => setShowCandidateForm(false)}>Cancel</Button>
            </div>
          </div>
        )}

        {/* Jobs View */}
        {view === "jobs" && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            {loading ? (
              <div className="text-center py-12 text-gray-400">Loading jobs...</div>
            ) : filteredJobs.length === 0 ? (
              <div className="text-center py-12 text-gray-400">No jobs found — post your first job</div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Job Title</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Department</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Candidates</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Status</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filteredJobs.map((job) => (
                    <tr key={job.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                        <p className="text-sm font-medium text-gray-900">{job.title}</p>
                        <p className="text-xs text-gray-400 mt-0.5 truncate max-w-xs">{job.description}</p>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{job.department}</td>
                      <td className="px-6 py-4">
                        <span className="text-sm font-medium text-gray-900">{job.candidate_count}</span>
                        <span className="text-xs text-gray-400 ml-1">candidates</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          job.status === "open" ? "bg-green-100 text-green-700" :
                          job.status === "closed" ? "bg-red-100 text-red-600" :
                          "bg-yellow-100 text-yellow-700"
                        }`}>
                          {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex gap-2">
                          <button onClick={() => openJob(job)} className="text-xs text-blue-600 hover:underline">
                            View Candidates
                          </button>
                          {job.status === "draft" && (
                            <button onClick={() => updateJobStatus(job.id, "open")} className="text-xs text-green-600 hover:underline">
                              Publish
                            </button>
                          )}
                          {job.status === "open" && (
                            <button onClick={() => updateJobStatus(job.id, "closed")} className="text-xs text-red-500 hover:underline">
                              Close
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Candidates View */}
        {view === "candidates" && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            {filteredCandidates.length === 0 ? (
              <div className="text-center py-12 text-gray-400">No candidates yet — add your first candidate</div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Candidate</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Status</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">AI Score</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Notes</th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Move To</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filteredCandidates.map((c) => (
                    <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white text-sm font-bold">
                            {c.full_name.charAt(0)}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">{c.full_name}</p>
                            <p className="text-xs text-gray-400">{c.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[c.status]}`}>
                          {c.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {c.ai_score !== null ? (
                          <span className="text-sm font-medium text-gray-900">{c.ai_score}/100</span>
                        ) : (
                          <span className="text-xs text-gray-400">Not screened</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-xs text-gray-500 max-w-xs truncate">
                        {c.notes || "—"}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex gap-2 flex-wrap">
                          {(nextStatus[c.status] || []).map(next => (
                            <button
                              key={next}
                              onClick={() => moveCandidate(c.id, next)}
                              className={`text-xs px-2 py-1 rounded border transition-colors ${
                                next === "rejected" || next === "withdrawn"
                                  ? "border-red-200 text-red-500 hover:bg-red-50"
                                  : "border-blue-200 text-blue-600 hover:bg-blue-50"
                              }`}
                            >
                              {next.replace("_", " ")}
                            </button>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

      </div>
    </DashboardLayout>
  )
}
