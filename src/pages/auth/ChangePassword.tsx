import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import axios from "axios"
import { getToken } from "@/lib/auth"

export default function ChangePassword() {
  const [current, setCurrent] = useState("")
  const [newPass, setNewPass] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!current || !newPass) {
      setError("Please fill in all fields")
      return
    }

    if (newPass.length < 8) {
      setError("New password must be at least 8 characters")
      return
    }

    setLoading(true)
    setError("")

    try {
      await axios.post(
        "http://localhost:8000/api/v1/auth/change-password",
        { current_password: current, new_password: newPass },
        { headers: { Authorization: `Bearer ${getToken()}` } }
      )

      // Update must_change_password in localStorage
      const user = JSON.parse(localStorage.getItem("user") || "{}")
      user.must_change_password = false
      localStorage.setItem("user", JSON.stringify(user))

      // Redirect based on role
      const roles: string[] = user.roles || []
      if (roles.includes("admin") || roles.includes("hr_manager")) {
        navigate("/dashboard")
      } else {
        navigate("/onboarding")
      }

    } catch (err: any) {
      const message = err.response?.data?.error?.message
        || "Failed to change password"
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">ByteSentinel</h1>
          <p className="text-gray-500 mt-2">Set your new password</p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Change Password</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-yellow-600 bg-yellow-50 p-3 rounded-md mb-4">
              You must set a new password before continuing.
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="bg-red-50 text-red-600 text-sm p-3 rounded-md">
                  {error}
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="current">Current Password</Label>
                <Input
                  id="current"
                  type="password"
                  placeholder="Your temporary password"
                  value={current}
                  onChange={(e) => setCurrent(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="new">New Password</Label>
                <Input
                  id="new"
                  type="password"
                  placeholder="Min 8 characters"
                  value={newPass}
                  onChange={(e) => setNewPass(e.target.value)}
                />
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Saving..." : "Set New Password"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
