import DashboardLayout from "@/components/layout/DashboardLayout"

const stats = [
  { label: "Total Employees", value: "24", icon: "👥", color: "bg-blue-500" },
  { label: "Present Today", value: "18", icon: "✅", color: "bg-green-500" },
  { label: "On Leave", value: "3", icon: "🌴", color: "bg-yellow-500" },
  { label: "Open Positions", value: "5", icon: "📋", color: "bg-purple-500" },
]

export default function Dashboard() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Overview</h1>

        {/* Stats Grid */}
        <div className="grid grid-cols-4 gap-4">
          {stats.map((stat) => (
            <div key={stat.label} className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <div className={`w-10 h-10 ${stat.color} rounded-lg flex items-center justify-center text-white text-lg mb-4`}>
                {stat.icon}
              </div>
              <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              <p className="text-sm text-gray-500 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Recent Activity</h2>
          <div className="space-y-3">
            {[
              { action: "New employee onboarded", name: "Rahul Sharma", time: "2 hours ago" },
              { action: "Leave request approved", name: "Priya Patel", time: "4 hours ago" },
              { action: "Payroll processed", name: "June 2025", time: "1 day ago" },
              { action: "New candidate added", name: "Amit Kumar", time: "2 days ago" },
            ].map((item, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div>
                  <p className="text-sm font-medium text-gray-800">{item.action}</p>
                  <p className="text-xs text-gray-500">{item.name}</p>
                </div>
                <span className="text-xs text-gray-400">{item.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
