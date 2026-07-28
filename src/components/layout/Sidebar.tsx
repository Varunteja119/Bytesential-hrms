import { useNavigate, useLocation } from "react-router-dom"

const menuItems = [
  { icon: "🏠", label: "Dashboard", path: "/dashboard" },
  { icon: "👥", label: "Employees", path: "/employees" },
  { icon: "📋", label: "Recruitment", path: "/recruitment" },
  { icon: "📅", label: "Attendance", path: "/attendance" },
  { icon: "🌴", label: "Leave", path: "/leave" },
  { icon: "💰", label: "Payroll", path: "/payroll" },
  { icon: "📊", label: "Analytics", path: "/analytics" },
  { icon: "🧾", label: "Finance", path: "/finance" },
  { icon: "🤖", label: "AI Assistant", path: "/ai-chat" },
]

export default function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()

  let user: any = {}
  try {
    const stored = localStorage.getItem("user")
    if (stored && stored !== "undefined") {
      user = JSON.parse(stored)
    }
  } catch {
    user = {}
  }

  const initials = user?.full_name
    ? user.full_name.split(" ").map((n: string) => n[0]).join("").toUpperCase()
    : "U"

  function handleLogout() {
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
    localStorage.removeItem("user")
    navigate("/login")
  }

  return (
    <div className="w-64 min-h-screen bg-gray-900 text-white flex flex-col">
      <div className="p-6 border-b border-gray-700">
        <h1 className="text-xl font-bold text-white">ByteSentinel</h1>
        <p className="text-gray-400 text-xs mt-1">HR Management</p>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {menuItems.map((item) => (
          <button
            key={item.label}
            onClick={() => navigate(item.path)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm transition-colors ${
              location.pathname === item.path
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:bg-gray-800 hover:text-white"
            }`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="p-4 border-t border-gray-700 space-y-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm font-bold">
            {initials}
          </div>
          <div>
            <p className="text-sm text-white">{user?.full_name || "User"}</p>
            <p className="text-xs text-gray-400">{user?.email || ""}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full text-left px-4 py-2 rounded-lg text-sm text-red-400 hover:bg-gray-800 transition-colors"
        >
          🚪 Logout
        </button>
      </div>
    </div>
  )
}
