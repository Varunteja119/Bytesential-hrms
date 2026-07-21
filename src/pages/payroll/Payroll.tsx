import DashboardLayout from "@/components/layout/DashboardLayout"
import { useState } from "react"
import { Button } from "@/components/ui/button"

const payrollData = [
  { id: 1, employee: "Rahul Sharma", empId: "BS-2025-001", department: "Engineering", basic: 50000, hra: 20000, special: 15000, pf: 1800, esi: 0, pt: 200, tds: 5000, lop: 0, gross: 85000, net: 78000 },
  { id: 2, employee: "Priya Patel", empId: "BS-2025-002", department: "HR", basic: 40000, hra: 16000, special: 12000, pf: 1800, esi: 0, pt: 200, tds: 3500, lop: 0, gross: 68000, net: 62500 },
  { id: 3, employee: "Amit Kumar", empId: "BS-2025-003", department: "Finance", basic: 35000, hra: 14000, special: 10000, pf: 1800, esi: 0, pt: 200, tds: 2500, lop: 1500, gross: 59000, net: 53000 },
  { id: 4, employee: "Sneha Reddy", empId: "BS-2025-004", department: "Engineering", basic: 30000, hra: 12000, special: 8000, pf: 1800, esi: 375, pt: 200, tds: 1500, lop: 0, gross: 50000, net: 46125 },
  { id: 5, employee: "Vikram Singh", empId: "BS-2025-005", department: "Sales", basic: 25000, hra: 10000, special: 7000, pf: 1800, esi: 315, pt: 200, tds: 800, lop: 3000, gross: 42000, net: 35885 },
  { id: 6, employee: "Ananya Das", empId: "BS-2025-006", department: "Engineering", basic: 45000, hra: 18000, special: 13000, pf: 1800, esi: 0, pt: 200, tds: 4200, lop: 0, gross: 76000, net: 69800 },
]

const fmt = (n: number) => `₹${n.toLocaleString("en-IN")}`

export default function Payroll() {
  const [status, setStatus] = useState<"draft" | "approved">("draft")
  const [month] = useState("June 2025")

  const totalGross = payrollData.reduce((a, b) => a + b.gross, 0)
  const totalNet = payrollData.reduce((a, b) => a + b.net, 0)
  const totalPF = payrollData.reduce((a, b) => a + b.pf, 0)
  const totalTDS = payrollData.reduce((a, b) => a + b.tds, 0)

  return (
    <DashboardLayout>
      <div className="space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Payroll</h1>
            <p className="text-gray-500 text-sm mt-1">{month} — {payrollData.length} employees</p>
          </div>
          <div className="flex gap-3">
            {status === "draft" && (
              <Button
                onClick={() => setStatus("approved")}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                ✓ Approve Payroll Run
              </Button>
            )}
            {status === "approved" && (
              <div className="flex items-center gap-2">
                <span className="bg-green-100 text-green-700 px-3 py-2 rounded-lg text-sm font-medium">
                  ✓ Payroll Approved
                </span>
                <Button className="bg-blue-600 hover:bg-blue-700 text-white">
                  📧 Send Payslips
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Total Gross", value: fmt(totalGross), color: "bg-blue-500" },
            { label: "Total Net Pay", value: fmt(totalNet), color: "bg-green-500" },
            { label: "Total PF", value: fmt(totalPF), color: "bg-purple-500" },
            { label: "Total TDS", value: fmt(totalTDS), color: "bg-orange-500" },
          ].map((s) => (
            <div key={s.label} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
              <div className={`w-8 h-8 ${s.color} rounded-lg mb-3`} />
              <p className="text-xl font-bold text-gray-900">{s.value}</p>
              <p className="text-sm text-gray-500 mt-1">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Status Banner */}
        <div className={`rounded-xl p-4 flex items-center justify-between ${
          status === "draft" ? "bg-yellow-50 border border-yellow-200" : "bg-green-50 border border-green-200"
        }`}>
          <div className="flex items-center gap-3">
            <span className="text-lg">{status === "draft" ? "⏳" : "✅"}</span>
            <div>
              <p className="font-medium text-gray-800">
                {status === "draft" ? "Payroll Draft — Pending Approval" : "Payroll Approved — Ready to Dispatch"}
              </p>
              <p className="text-sm text-gray-500">
                {status === "draft"
                  ? "Review all entries and click Approve to process payroll"
                  : "Click Send Payslips to email payslips to all employees"}
              </p>
            </div>
          </div>
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${
            status === "draft" ? "bg-yellow-100 text-yellow-700" : "bg-green-100 text-green-700"
          }`}>
            {status === "draft" ? "DRAFT" : "APPROVED"}
          </span>
        </div>

        {/* Payroll Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-left px-4 py-4 text-xs font-semibold text-gray-500 uppercase">Employee</th>
                  <th className="text-right px-4 py-4 text-xs font-semibold text-gray-500 uppercase">Basic</th>
                  <th className="text-right px-4 py-4 text-xs font-semibold text-gray-500 uppercase">HRA</th>
                  <th className="text-right px-4 py-4 text-xs font-semibold text-gray-500 uppercase">Special</th>
                  <th className="text-right px-4 py-4 text-xs font-semibold text-gray-500 uppercase">Gross</th>
                  <th className="text-right px-4 py-4 text-xs font-semibold text-gray-500 uppercase">PF</th>
                  <th className="text-right px-4 py-4 text-xs font-semibold text-gray-500 uppercase">TDS</th>
                  <th className="text-right px-4 py-4 text-xs font-semibold text-gray-500 uppercase">LOP</th>
                  <th className="text-right px-4 py-4 text-xs font-semibold text-gray-500 uppercase">Net Pay</th>
                  <th className="text-left px-4 py-4 text-xs font-semibold text-gray-500 uppercase">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {payrollData.map((emp) => (
                  <tr key={emp.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold">
                          {emp.employee.charAt(0)}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{emp.employee}</p>
                          <p className="text-xs text-gray-400">{emp.empId} · {emp.department}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-sm text-right text-gray-600">{fmt(emp.basic)}</td>
                    <td className="px-4 py-4 text-sm text-right text-gray-600">{fmt(emp.hra)}</td>
                    <td className="px-4 py-4 text-sm text-right text-gray-600">{fmt(emp.special)}</td>
                    <td className="px-4 py-4 text-sm text-right font-medium text-gray-800">{fmt(emp.gross)}</td>
                    <td className="px-4 py-4 text-sm text-right text-red-500">-{fmt(emp.pf)}</td>
                    <td className="px-4 py-4 text-sm text-right text-red-500">-{fmt(emp.tds)}</td>
                    <td className="px-4 py-4 text-sm text-right text-red-500">
                      {emp.lop > 0 ? `-${fmt(emp.lop)}` : "—"}
                    </td>
                    <td className="px-4 py-4 text-sm text-right font-bold text-green-600">{fmt(emp.net)}</td>
                    <td className="px-4 py-4">
                      <button className="text-xs text-blue-600 hover:underline">Payslip</button>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-gray-50 border-t-2 border-gray-200">
                  <td className="px-4 py-4 text-sm font-bold text-gray-800">Total</td>
                  <td colSpan={3} />
                  <td className="px-4 py-4 text-sm font-bold text-right text-gray-800">{fmt(totalGross)}</td>
                  <td className="px-4 py-4 text-sm font-bold text-right text-red-500">-{fmt(totalPF)}</td>
                  <td className="px-4 py-4 text-sm font-bold text-right text-red-500">-{fmt(totalTDS)}</td>
                  <td />
                  <td className="px-4 py-4 text-sm font-bold text-right text-green-600">{fmt(totalNet)}</td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

      </div>
    </DashboardLayout>
  )
}
