import DashboardLayout from "@/components/layout/DashboardLayout"
import { Button } from "@/components/ui/button"
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
} from "recharts"

const revenueExpense = [
  { month: "Jan", revenue: 95, expense: 62 },
  { month: "Feb", revenue: 102, expense: 65 },
  { month: "Mar", revenue: 108, expense: 67 },
  { month: "Apr", revenue: 114, expense: 70 },
  { month: "May", revenue: 121, expense: 73 },
  { month: "Jun", revenue: 128, expense: 75 },
]

const cashFlow = [
  { month: "Jan", cash: 33 },
  { month: "Feb", cash: 37 },
  { month: "Mar", cash: 41 },
  { month: "Apr", cash: 44 },
  { month: "May", cash: 48 },
  { month: "Jun", cash: 53 },
]

export default function Finance() {
  return (
    <DashboardLayout>

      <div className="space-y-6">

        <div className="flex items-center justify-between">

          <div>

            <h1 className="text-2xl font-bold">
              Finance
            </h1>

            <p className="text-gray-500 mt-1">
              Financial overview and company expenses
            </p>

          </div>

          <Button className="bg-blue-600 hover:bg-blue-700 text-white">
            Export Report
          </Button>

        </div>

        <div className="grid grid-cols-4 gap-5">

          {[
            {
              title: "Revenue",
              value: "₹1.28 Cr",
              color: "bg-green-500",
            },
            {
              title: "Expenses",
              value: "₹75 L",
              color: "bg-red-500",
            },
            {
              title: "Net Profit",
              value: "₹53 L",
              color: "bg-blue-500",
            },
            {
              title: "Pending Invoices",
              value: "18",
              color: "bg-purple-500",
            },
          ].map((card) => (

            <div
              key={card.title}
              className="bg-white rounded-xl border border-gray-100 shadow-sm p-5"
            >

              <div
                className={`w-10 h-10 rounded-lg ${card.color} mb-4`}
              />

              <h2 className="text-3xl font-bold">
                {card.value}
              </h2>

              <p className="text-gray-500 mt-1">
                {card.title}
              </p>

            </div>

          ))}

        </div>

        <div className="grid grid-cols-2 gap-6">

          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">

            <h2 className="font-semibold text-lg mb-5">
              Revenue vs Expenses (₹ Lakhs)
            </h2>

            <div className="h-80">

              <ResponsiveContainer width="100%" height="100%">

                <AreaChart data={revenueExpense}>

                  <CartesianGrid strokeDasharray="3 3" />

                  <XAxis dataKey="month" />

                  <YAxis tickFormatter={(v)=>`₹${v}L`} />

                  <Tooltip
                    formatter={(v)=>[`₹${v} L`]}
                  />

                  <Area
                    dataKey="revenue"
                    stroke="#16a34a"
                    fill="#bbf7d0"
                  />

                  <Area
                    dataKey="expense"
                    stroke="#dc2626"
                    fill="#fecaca"
                  />

                </AreaChart>

              </ResponsiveContainer>

            </div>

          </div>

          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">

            <h2 className="font-semibold text-lg mb-5">
              Monthly Cash Flow (₹ Lakhs)
            </h2>

            <div className="h-80">

              <ResponsiveContainer width="100%" height="100%">

                <BarChart data={cashFlow}>

                  <CartesianGrid strokeDasharray="3 3"/>

                  <XAxis dataKey="month"/>

                  <YAxis tickFormatter={(v)=>`₹${v}L`}/>

                  <Tooltip
                    formatter={(v)=>[`₹${v} L`]}
                  />

                  <Bar
                    dataKey="cash"
                    fill="#2563eb"
                    radius={[6,6,0,0]}
                  />

                </BarChart>

              </ResponsiveContainer>

            </div>

          </div>

        </div>

        <div className="grid grid-cols-2 gap-6">

          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">

            <div className="px-6 py-4 border-b border-gray-100">
              <h2 className="text-lg font-semibold">
                Recent Transactions
              </h2>
            </div>

            <table className="w-full">

              <thead className="bg-gray-50">

                <tr>

                  <th className="text-left px-6 py-4 text-sm font-semibold">
                    Date
                  </th>

                  <th className="text-left px-6 py-4 text-sm font-semibold">
                    Description
                  </th>

                  <th className="text-left px-6 py-4 text-sm font-semibold">
                    Amount
                  </th>

                  <th className="text-left px-6 py-4 text-sm font-semibold">
                    Status
                  </th>

                </tr>

              </thead>

              <tbody>

                {[
                  {
                    date: "18 Jul",
                    desc: "Employee Salaries",
                    amount: "₹42,50,000",
                    status: "Paid",
                  },
                  {
                    date: "17 Jul",
                    desc: "AWS Cloud Services",
                    amount: "₹1,45,000",
                    status: "Paid",
                  },
                  {
                    date: "15 Jul",
                    desc: "Office Rent",
                    amount: "₹3,25,000",
                    status: "Paid",
                  },
                  {
                    date: "12 Jul",
                    desc: "Vendor Invoice",
                    amount: "₹92,000",
                    status: "Pending",
                  },
                ].map((row) => (

                  <tr
                    key={row.desc}
                    className="border-t border-gray-100 hover:bg-gray-50"
                  >

                    <td className="px-6 py-4">
                      {row.date}
                    </td>

                    <td className="px-6 py-4">
                      {row.desc}
                    </td>

                    <td className="px-6 py-4 font-medium">
                      {row.amount}
                    </td>

                    <td className="px-6 py-4">

                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${
                          row.status === "Paid"
                            ? "bg-green-100 text-green-700"
                            : "bg-yellow-100 text-yellow-700"
                        }`}
                      >
                        {row.status}
                      </span>

                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">

            <h2 className="text-lg font-semibold mb-6">
              Budget Allocation
            </h2>

            {[
              { name: "Engineering", value: 40 },
              { name: "HR", value: 15 },
              { name: "Marketing", value: 18 },
              { name: "Sales", value: 17 },
              { name: "Operations", value: 10 },
            ].map((item) => (

              <div
                key={item.name}
                className="mb-6"
              >

                <div className="flex justify-between mb-2">

                  <span className="text-sm font-medium">
                    {item.name}
                  </span>

                  <span className="text-sm text-gray-500">
                    {item.value}%
                  </span>

                </div>

                <div className="w-full bg-gray-200 rounded-full h-3">

                  <div
                    className="bg-blue-600 h-3 rounded-full"
                    style={{
                      width: `${item.value}%`,
                    }}
                  />

                </div>

              </div>

            ))}

            <div className="border-t pt-6 mt-8">

              <h3 className="font-semibold mb-4">
                Quick Actions
              </h3>

              <div className="grid grid-cols-1 gap-3">

                <Button className="bg-blue-600 hover:bg-blue-700 text-white">
                  Generate Invoice
                </Button>

                <Button
                  variant="outline"
                >
                  Download GST Report
                </Button>

                <Button
                  variant="outline"
                >
                  Export Financial Statement
                </Button>

              </div>

            </div>

          </div>

        </div>

      </div>

    </DashboardLayout>
  )
}

