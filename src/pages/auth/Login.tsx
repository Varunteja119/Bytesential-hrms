import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import axios from "axios"

export default function Login() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!email || !password) {
      setError("Please fill in all fields")
      return
    }

    setLoading(true)
    setError("")

    try {
      const response = await axios.post(
        "http://localhost:8000/api/v1/auth/login",
        { email, password }
      )
      const { access_token, refresh_token, user } = response.data
      localStorage.setItem("access_token", access_token)
      localStorage.setItem("refresh_token", refresh_token)
      localStorage.setItem("user", JSON.stringify(user))
      navigate("/dashboard")

    } catch (err: any) {
      // TEMPORARY — bypass login until backend is running
      localStorage.setItem("access_token", "dev_token")
      localStorage.setItem("user", JSON.stringify({
        full_name: "Varun",
        email: email,
        roles: ["hr_admin"]
      }))
      navigate("/dashboard")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">ByteSentinel</h1>
          <p className="text-gray-500 mt-2">HR Management System</p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Sign in to your account</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="bg-red-50 text-red-600 text-sm p-3 rounded-md">
                  {error}
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@bytesentinel.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Signing in..." : "Sign in"}
              </Button>
            </form>
          </CardContent>
        </Card>
        <p className="text-center text-sm text-gray-500 mt-4">
          ByteSentinel Pvt Ltd — Internal HRMS
        </p>
      </div>
    </div>
  )
}
