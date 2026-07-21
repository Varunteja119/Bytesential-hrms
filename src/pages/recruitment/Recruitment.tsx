import DashboardLayout from "@/components/layout/DashboardLayout"
import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

const candidates = [
  {
    id: 1, name: "Arjun Mehta", email: "arjun@gmail.com",
    role: "Backend Developer", experience: "3 years",
    currentCTC: "8 LPA", expectedCTC: "12 LPA",
    status: "selected", round: "Offer Sent",
    appliedDate: "Jun 1, 2025"
  },
  {
    id: 2, name: "Kavya Nair", email: "kavya@gmail.com",
    role: "UI/UX Designer", experience: "2 years",
    currentCTC: "6 LPA", expectedCTC: "9 LPA",
    status: "interview", round: "Round 2",
    appliedDate: "Jun 5, 2025"
  },
  {
    id: 3, name: "Rohan Gupta", email: "rohan@gmail.com",
    role: "DevOps Engineer", experience: "4 years",
    currentCTC: "12 LPA", expectedCTC: "18 LPA",
    status: "screening", round: "Round 1",
    appliedDate: "Jun 8, 2025"
  },
  {
    id: 4, name: "Meera Joshi", email: "meera@gmail.com",
    role: "Data Analyst", experience: "2 years",
    currentCTC: "5 LPA", expectedCTC: "8 LPA",
    status: "applied", round: "Applied",
    appliedDate: "Jun 10, 2025"
  },
  {
    id: 5, name: "Siddharth Rao", email: "siddharth@gmail.com",
    role: "Product Manager", experience: "5 years",
    currentCTC: "18 LPA", expectedCTC: "25 LPA",
    status: "rejected", round: "Rejected",
    appliedDate: "May 28, 2025"
  },
  {
    id: 6, name: "Divya Krishnan", email: "divya@gmail.com",
    role: "AI Engineer", experience: "3 years",
    currentCTC: "10 LPA", expectedCTC: "15 LPA",
    status: "joined", round: "Joined",
    appliedDate: "May 20, 2025"
  },
]

const statusConfig: Record<string, { label: string, color: string }> = {
  applied:   { label: "Applied",    color: "bg-gray-100 text-gray-600" },
  screening: { label: "Screening",  color: "bg-blue-100 text-blue-600" },
  interview: { label: "Interview",  color: "bg-yellow-100 text-yellow-600" },
  selected:  { label: "Selected",   color: "bg-green-100 text-green-600" },
  rejected:  { label: "Rejected",   color: "bg-red-100 text-red-600" },
  joined:    { label: "Joined",     color: "bg-purple-100 text-purple-600" },
}

const pipeline = ["applied", "screening", "interview", "selected", "joined"]

export default function Recruitment() {
  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState("all")
  const [view, setView] = useState<"list" | "pipeline">("list")

  const filtered = candidates.filter(c => {
    const matchSearch = c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.role.toLowerCase().includes(search.toLowerCase())
    const matchFilter = filter === "all" || c.status === filter
    return matchSearch && matchFilter
  })

  return (
    <DashboardLayout>
      <div className="space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Recruitment</h1>
            <p className="text-gray-500 text-sm mt-1">{candidates.length} total candidates</p>
          </div>
          <Button className="bg-blue-600 hover:bg-blue-700 text-white">
            + Add Candidate
          </Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-6 gap-3">
          {pipeline.map(stage => {
            const count = candidates.filter(c => c.status === stage).length
            const conf = statusConfig[stage]
            return (
              <div key={stage} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 text-center">
                <p className="text-2xl font-bold text-gray-900">{count}</p>
                <p className="text-xs text-gray-500 mt-1">{conf.label}</p>
              </div>
            )
          })}
        </div>

        {/* Controls */}
        <div className="flex items-center justify-between">
          <div className="flex gap-3">
            <Input
              placeholder="Search candidates..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-64"
            />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 bg-white"
            >
              <option value="all">All Status</option>
              {Object.entries(statusConfig).map(([key, val]) => (
                <option key={key} value={key}>{val.label}</option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setView("list")}
              className={`px-4 py-2 rounded-lg text-sm font-medium ${view === "list" ? "bg-blue-600 text-white" : "bg-white border border-gray-200 text-gray-600"}`}
            >
              List
            </button>
            <button
              onClick={() => setView("pipeline")}
              className={`px-4 py-2 rounded-lg text-sm font-medium ${view === "pipeline" ? "bg-blue-600 text-white" : "bg-white border border-gray-200 text-gray-600"}`}
            >
              Pipeline
            </button>
          </div>
        </div>

        {/* List View */}
        {view === "list" && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Candidate</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Role</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Experience</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">CTC</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Status</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Applied</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map((c) => {
                  const conf = statusConfig[c.status]
                  return (
                    <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-purple-600 flex items-center justify-center text-white text-sm font-bold">
                            {c.name.charAt(0)}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">{c.name}</p>
                            <p className="text-xs text-gray-500">{c.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{c.role}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{c.experience}</td>
                      <td className="px-6 py-4">
                        <p className="text-xs text-gray-500">Current: {c.currentCTC}</p>
                        <p className="text-xs text-gray-700 font-medium">Expected: {c.expectedCTC}</p>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${conf.color}`}>
                          {conf.label}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">{c.appliedDate}</td>
                      <td className="px-6 py-4">
                        <div className="flex gap-2">
                          <button className="text-xs text-blue-600 hover:underline">View</button>
                          <button className="text-xs text-green-600 hover:underline">Move</button>
                          <button className="text-xs text-gray-500 hover:underline">Reject</button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <div className="text-center py-12 text-gray-400">No candidates found</div>
            )}
          </div>
        )}

        {/* Pipeline View */}
        {view === "pipeline" && (
          <div className="grid grid-cols-5 gap-4">
            {pipeline.map(stage => {
              const conf = statusConfig[stage]
              const stageCandidates = filtered.filter(c => c.status === stage)
              return (
                <div key={stage} className="bg-gray-50 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-gray-700">{conf.label}</h3>
                    <span className="text-xs bg-white border border-gray-200 text-gray-500 px-2 py-0.5 rounded-full">
                      {stageCandidates.length}
                    </span>
                  </div>
                  <div className="space-y-3">
                    {stageCandidates.map(c => (
                      <div key={c.id} className="bg-white rounded-lg p-3 shadow-sm border border-gray-100">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="w-7 h-7 rounded-full bg-purple-600 flex items-center justify-center text-white text-xs font-bold">
                            {c.name.charAt(0)}
                          </div>
                          <p className="text-sm font-medium text-gray-900">{c.name}</p>
                        </div>
                        <p className="text-xs text-gray-500">{c.role}</p>
                        <p className="text-xs text-gray-400 mt-1">{c.experience} · {c.expectedCTC}</p>
                      </div>
                    ))}
                    {stageCandidates.length === 0 && (
                      <p className="text-xs text-gray-400 text-center py-4">No candidates</p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}

      </div>
    </DashboardLayout>
  )
}
