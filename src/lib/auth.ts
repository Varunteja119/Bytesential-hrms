export function getUser() {
  try {
    const stored = localStorage.getItem("user")
    if (stored && stored !== "undefined") {
      return JSON.parse(stored)
    }
  } catch {
    return null
  }
  return null
}

export function getRoles(): string[] {
  const user = getUser()
  return user?.roles || []
}

export function isAdmin(): boolean {
  return getRoles().includes("admin")
}

export function isHRManager(): boolean {
  return getRoles().includes("hr_manager") || isAdmin()
}

export function isEmployee(): boolean {
  return getRoles().includes("employee")
}

export function getToken(): string | null {
  return localStorage.getItem("access_token")
}

export function apiHeaders() {
  return {
    Authorization: `Bearer ${getToken()}`
  }
}
