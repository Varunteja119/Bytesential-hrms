import DashboardLayout from "@/components/layout/DashboardLayout"
import { Button } from "@/components/ui/button"
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
} from "recharts"

const attendanceTrend = [
  { month: "Jan", attendance: 91 },
  { month: "Feb", attendance: 93 },
  { month: "Mar", attendance: 95 },
  { month: "Apr", attendance: 94 },
  { month: "May", attendance: 96 },
  { month: "Jun", attendance: 97 },
]

const departmentData = [
  { department: "Engineering", employees: 42 },
  { department: "HR", employees: 12 },
  { department: "Finance", employees: 18 },
  { department: "Sales", employees: 25 },
  { department: "Marketing", employees: 15 },
]

const leaveData = [
  { name: "Annual", value: 46 },
  { name: "Sick", value: 24 },
  { name: "Casual", value: 18 },
  { name: "Other", value: 12 },
]

const payrollTrend = [
  { month: "Jan", payroll: 62 },
  { month: "Feb", payroll: 64 },
  { month: "Mar", payroll: 65 },
  { month: "Apr", payroll: 66 },
  { month: "May", payroll: 68 },
  { month: "Jun", payroll: 69 },
]

const COLORS = [
  "#2563eb",
  "#16a34a",
  "#eab308",
  "#dc2626",
]

const insights = [
  {
    department: "Engineering",
    attendance: "97%",
    productivity: "High",
    status: "Excellent",
  },
  {
    department: "HR",
    attendance: "95%",
    productivity: "Good",
    status: "Good",
  },
  {
    department: "Finance",
    attendance: "93%",
    productivity: "Average",
    status: "Stable",
  },
  {
    department: "Sales",
    attendance: "91%",
    productivity: "High",
    status: "Improving",
  },
]

export default function Analytics() {
  return (
    <DashboardLayout>
      <div className="space-y-6">

        <div className="flex items-center justify-between">

          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              HR Analytics
            </h1>

            <p className="text-sm text-gray-500 mt-1">
              Organization performance overview
            </p>
          </div>

          <Button className="bg-blue-600 hover:bg-blue-700 text-white">
            Export Report
          </Button>

        </div>

        <div className="grid grid-cols-4 gap-5">

          {[
            {
              title: "Employees",
              value: "112",
              color: "bg-blue-500",
            },
            {
              title: "Attendance",
              value: "96%",
              color: "bg-green-500",
            },
            {
              title: "Monthly Payroll",
              value: "₹69 L",
              color: "bg-purple-500",
            },
            {
              title: "Attrition",
              value: "4.1%",
              color: "bg-orange-500",
            },
          ].map((card) => (
            <div
              key={card.title}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-5"
            >
              <div
                className={`w-10 h-10 rounded-lg ${card.color} mb-4`}
              />

              <h3 className="text-3xl font-bold">
                {card.value}
              </h3>

              <p className="text-gray-500 mt-1">
                {card.title}
              </p>
            </div>
          ))}

        </div>

        <div className="grid grid-cols-2 gap-6">

          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">

            <h2 className="font-semibold text-lg mb-5">
              Attendance Trend
            </h2>

            <div className="h-80">

              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={attendanceTrend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />

                  <Line
                    type="monotone"
                    dataKey="attendance"
                    stroke="#2563eb"
                    strokeWidth={3}
                  />
                </LineChart>
              </ResponsiveContainer>

            </div>

          </div>

          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">

            <h2 className="font-semibold text-lg mb-5">
              Employees by Department
            </h2>

            <div className="h-80">

              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={departmentData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="department" />
                  <YAxis />
                  <Tooltip />

                  <Bar
                    dataKey="employees"
                    fill="#2563eb"
                    radius={[6,6,0,0]}
                  />
                </BarChart>
              </ResponsiveContainer>

            </div>

          </div>

        </div>
        <div className="grid grid-cols-2 gap-6">

          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">

            <h2 className="font-semibold text-lg mb-5">
              Leave Distribution
            </h2>

            <div className="h-80">

              <ResponsiveContainer width="100%" height="100%">
                <PieChart>

                  <Pie
                    data={leaveData}
                    dataKey="value"
                    nameKey="name"
                    outerRadius={100}
                    label
                  >
                    {leaveData.map((_, index) => (
                      <Cell
                        key={index}
                        fill={COLORS[index % COLORS.length]}
                      />
                    ))}
                  </Pie>

                  <Tooltip />

                </PieChart>
              </ResponsiveContainer>

            </div>

          </div>

          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">

            <h2 className="font-semibold text-lg mb-5">
            Monthly Payroll (₹ Lakhs)
            </h2>

            <div className="h-80">

              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={payrollTrend}>

                  <CartesianGrid strokeDasharray="3 3" />

                  <XAxis dataKey="month" />

                  <YAxis />

                  <Tooltip />

                  <Area
                    type="monotone"
                    dataKey="payroll"
                    stroke="#16a34a"
                    fill="#bbf7d0"
                  />

                </AreaChart>
              </ResponsiveContainer>

            </div>

          </div>

        </div>

        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">

          <div className="px-6 py-4 border-b border-gray-100">

            <h2 className="text-lg font-semibold">
              Department Performance
            </h2>

          </div>

          <table className="w-full">

            <thead>

              <tr className="bg-gray-50">

                <th className="text-left px-6 py-4 text-sm font-semibold">
                  Department
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold">
                  Attendance
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold">
                  Productivity
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold">
                  Status
                </th>

              </tr>

            </thead>

            <tbody>

              {insights.map((item) => (

                <tr
                  key={item.department}
                  className="border-t border-gray-100 hover:bg-gray-50"
                >

                  <td className="px-6 py-4">
                    {item.department}
                  </td>

                  <td className="px-6 py-4">
                    {item.attendance}
                  </td>

                  <td className="px-6 py-4">
                    {item.productivity}
                  </td>

                  <td className="px-6 py-4">

                    <span className="px-3 py-1 rounded-full bg-green-100 text-green-700 text-xs font-medium">
                      {item.status}
                    </span>

                  </td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

      </div>
    </DashboardLayout>
  )
}
