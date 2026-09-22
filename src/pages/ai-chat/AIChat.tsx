import DashboardLayout from "@/components/layout/DashboardLayout"
import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import axios from "axios"
import { apiHeaders } from "@/lib/auth"

const BASE = "http://localhost:8000/api/v1"

type Message = {
  id: string
  role: "user" | "assistant"
  content: string
  time: string
}

const suggestions = [
  "What is my leave balance?",
  "How many employees are active?",
  "Show me attendance summary",
  "What is the payroll cost this month?",
  "Who is on leave today?",
  "Show me attrition risk",
]

function getTime() {
  return new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })
}

export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hello! I'm ByteSentinel's AI HR Assistant powered by LangGraph. I can help you with leave balances, payroll, employee information, attendance, and more.\n\nWhat can I help you with today?",
      time: getTime()
    }
  ])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [error, setError] = useState("")
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function sendMessage(text?: string) {
    const msg = text || input.trim()
    if (!msg) return

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: msg,
      time: getTime()
    }
    setMessages(prev => [...prev, userMsg])
    setInput("")
    setLoading(true)
    setError("")

    try {
      const res = await axios.post(
        `${BASE}/ai-assistant/chat`,
        {
          question: msg,
          session_id: sessionId || undefined
        },
        { headers: apiHeaders() }
      )

      const data = res.data
      if (data.session_id) setSessionId(data.session_id)

      const reply: Message = {
        id: data.id || Date.now().toString() + "r",
        role: "assistant",
        content: data.content,
        time: getTime()
      }
      setMessages(prev => [...prev, reply])

    } catch (err: any) {
      const errMsg = err.response?.data?.error?.message || "AI Assistant is unavailable — make sure Ollama is running"
      setError(errMsg)
      const errReply: Message = {
        id: Date.now().toString() + "e",
        role: "assistant",
        content: `⚠️ ${errMsg}`,
        time: getTime()
      }
      setMessages(prev => [...prev, errReply])
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  function clearChat() {
    setSessionId(null)
    setMessages([{
      id: "welcome",
      role: "assistant",
      content: "Hello! I'm ByteSentinel's AI HR Assistant. What can I help you with?",
      time: getTime()
    }])
  }

  return (
    <DashboardLayout>
      <div className="flex flex-col h-[calc(100vh-120px)]">

        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">AI HR Assistant</h1>
            <p className="text-gray-500 text-sm mt-1">Powered by LangGraph · DeepSeek</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-sm text-gray-500">Online</span>
            </div>
            <Button variant="outline" onClick={clearChat} className="text-sm">
              New Chat
            </Button>
          </div>
        </div>

        {/* Suggestions */}
        <div className="flex gap-2 flex-wrap mb-4">
          {suggestions.map(s => (
            <button
              key={s}
              onClick={() => sendMessage(s)}
              disabled={loading}
              className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs text-gray-600 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-600 transition-colors disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>

        {/* Chat Window */}
        <div className="flex-1 bg-white rounded-xl border border-gray-100 shadow-sm overflow-y-auto p-6 space-y-4">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`flex gap-3 max-w-2xl ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-white text-sm font-bold ${
                  msg.role === "assistant" ? "bg-blue-600" : "bg-gray-600"
                }`}>
                  {msg.role === "assistant" ? "AI" : "V"}
                </div>
                <div>
                  <div className={`px-4 py-3 rounded-2xl text-sm whitespace-pre-line ${
                    msg.role === "assistant"
                      ? "bg-gray-50 text-gray-800 rounded-tl-none"
                      : "bg-blue-600 text-white rounded-tr-none"
                  }`}>
                    {msg.content}
                  </div>
                  <p className={`text-xs text-gray-400 mt-1 ${msg.role === "user" ? "text-right" : ""}`}>
                    {msg.time}
                  </p>
                </div>
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {loading && (
            <div className="flex justify-start">
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold">AI</div>
                <div className="bg-gray-50 px-4 py-3 rounded-2xl rounded-tl-none">
                  <div className="flex gap-1 items-center h-4">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="flex gap-3 mt-4">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask anything — leave balance, payroll, employee info..."
            className="flex-1"
            disabled={loading}
          />
          <Button
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6"
          >
            Send
          </Button>
        </div>

      </div>
    </DashboardLayout>
  )
}
