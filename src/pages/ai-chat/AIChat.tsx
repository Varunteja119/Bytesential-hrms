import DashboardLayout from "@/components/layout/DashboardLayout"
import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

type Message = {
  id: number
  role: "user" | "assistant"
  text: string
  time: string
}

const suggestions = [
  "What is my leave balance?",
  "Run payroll for June 2025",
  "How many employees are on leave today?",
  "Generate offer letter for Arjun Mehta",
  "Show attrition report for Q2",
  "What is Rahul Sharma's current CTC?",
]

const fakeResponses: Record<string, string> = {
  "what is my leave balance?": "You currently have:\n• Earned Leave: 11 days remaining\n• Sick Leave: 5 days remaining\n• Casual Leave: 6 days remaining",
  "run payroll for june 2025": "✅ Payroll run initiated for June 2025.\n\nSummary:\n• Total Employees: 6\n• Total Gross: ₹3,80,000\n• Total Deductions: ₹34,690\n• Total Net Pay: ₹3,45,310\n\nPayroll is in DRAFT status. Please review and approve.",
  "how many employees are on leave today?": "3 employees are on leave today:\n• Priya Patel — Sick Leave\n• Amit Kumar — Casual Leave\n• Sneha Reddy — Earned Leave",
  "generate offer letter for arjun mehta": "✅ Offer letter generated for Arjun Mehta.\n\n• Role: Backend Developer\n• CTC: ₹12 LPA\n• Joining Date: July 1, 2025\n\nThe offer letter PDF has been saved and emailed to arjun@gmail.com.",
  "show attrition report for q2": "Q2 2025 Attrition Report:\n\n• Total Exits: 2\n• Attrition Rate: 8.3%\n• Departments Affected: Engineering (1), Sales (1)\n• Average Tenure at Exit: 14 months\n• Top Reason: Better opportunity (2)",
  "what is rahul sharma's current ctc?": "Rahul Sharma (BS-2025-001)\n• Current CTC: ₹10,20,000 per annum\n• Basic: ₹50,000/month\n• Last Revision: January 2025 (+15%)\n• Department: Engineering",
}

function getResponse(input: string): string {
  const key = input.toLowerCase().trim()
  for (const [q, a] of Object.entries(fakeResponses)) {
    if (key.includes(q.split(" ")[0]) || key === q) return a
  }
  return "I understand your query. Let me check the HR database and get back to you with accurate information. For complex queries, please contact your HR team directly."
}

function getTime() {
  return new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })
}

export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      role: "assistant",
      text: "Hello! I'm ByteSentinel's AI HR Assistant. I can help you with leave balances, payroll, employee information, document generation, and more.\n\nWhat can I help you with today?",
      time: getTime()
    }
  ])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function sendMessage(text?: string) {
    const msg = text || input.trim()
    if (!msg) return

    const userMsg: Message = { id: Date.now(), role: "user", text: msg, time: getTime() }
    setMessages(prev => [...prev, userMsg])
    setInput("")
    setLoading(true)

    await new Promise(r => setTimeout(r, 1200))

    const reply: Message = {
      id: Date.now() + 1,
      role: "assistant",
      text: getResponse(msg),
      time: getTime()
    }
    setMessages(prev => [...prev, reply])
    setLoading(false)
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <DashboardLayout>
      <div className="flex flex-col h-[calc(100vh-120px)]">

        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">AI HR Assistant</h1>
            <p className="text-gray-500 text-sm mt-1">Powered by DeepSeek · LangGraph</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-sm text-gray-500">Online</span>
          </div>
        </div>

        {/* Suggestions */}
        <div className="flex gap-2 flex-wrap mb-4">
          {suggestions.map(s => (
            <button
              key={s}
              onClick={() => sendMessage(s)}
              className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs text-gray-600 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-600 transition-colors"
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

                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-white text-sm font-bold ${
                  msg.role === "assistant" ? "bg-blue-600" : "bg-gray-600"
                }`}>
                  {msg.role === "assistant" ? "AI" : "V"}
                </div>

                {/* Bubble */}
                <div>
                  <div className={`px-4 py-3 rounded-2xl text-sm whitespace-pre-line ${
                    msg.role === "assistant"
                      ? "bg-gray-50 text-gray-800 rounded-tl-none"
                      : "bg-blue-600 text-white rounded-tr-none"
                  }`}>
                    {msg.text}
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
              <div className="flex gap-3 max-w-2xl">
                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold">
                  AI
                </div>
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
