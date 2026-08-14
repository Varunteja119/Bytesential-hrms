import { Navigate } from "react-router-dom"
import { getToken, getRoles } from "@/lib/auth"

interface Props {
  children: React.ReactNode
  roles?: string[]
}

export default function ProtectedRoute({ children, roles }: Props) {
  const token = getToken()

  if (!token) {
    return <Navigate to="/login" replace />
  }

  if (roles && roles.length > 0) {
    const userRoles = getRoles()
    const hasRole = roles.some(r => userRoles.includes(r))
    if (!hasRole) {
      return <Navigate to="/onboarding" replace />
    }
  }

  return <>{children}</>
}
