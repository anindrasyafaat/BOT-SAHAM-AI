import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { useQueryClient } from 'react-query'
import { toast } from './use-toast'

// Protokol backend (FastAPI WebSocket /ws): JSON {type, data|signal, symbol?}; klien kirim {type: 'subscribe', channel, symbol?}.
interface WebSocketMessage {
  type: string
  data: any
  symbol?: string
  channel?: string
}

interface WebSocketState {
  isConnected: boolean
  messages: WebSocketMessage[]
  error: string | null
}

interface UseWebSocketReturn {
  socket: WebSocket | null
  state: WebSocketState
  subscribe: (channel: string, symbol?: string) => void
  unsubscribe: (channel: string, symbol?: string) => void
  sendMessage: (message: any) => void
}

const MAX_MESSAGES = 100
const wsUrl = () => `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`

export function useWebSocket(): UseWebSocketReturn {
  const qc = useQueryClient()
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [state, setState] = useState<WebSocketState>({ isConnected: false, messages: [], error: null })
  const buffer = useRef<WebSocketMessage[]>([])

  useEffect(() => {
    let ws: WebSocket
    let retry = 0
    let timer: ReturnType<typeof setTimeout>
    let closed = false

    const connect = () => {
      ws = new WebSocket(wsUrl())
      setSocket(ws)
      ws.onopen = () => {
        retry = 0
        setState((p) => ({ ...p, isConnected: true, error: null }))
        for (const channel of ['market_data', 'signals']) ws.send(JSON.stringify({ type: 'subscribe', channel }))
      }
      ws.onclose = () => {
        setState((p) => ({ ...p, isConnected: false }))
        if (!closed) timer = setTimeout(connect, Math.min(30000, 1000 * 2 ** retry++)) // backoff
      }
      ws.onerror = () => setState((p) => ({ ...p, error: 'Koneksi realtime gagal' }))
      ws.onmessage = (ev) => {
        let raw: any
        try {
          raw = JSON.parse(ev.data)
        } catch {
          return
        }
        const msg: WebSocketMessage = { ...raw, data: raw.data ?? raw.signal }
        if (msg.type === 'new_signal') {
          qc.invalidateQueries({ predicate: (q) => String(q.queryKey[0]).startsWith('/api/signals') })
          toast({ title: `Sinyal ${msg.data?.signal_type} ${msg.data?.symbol}`, description: `${msg.data?.strategy_name} · confidence ${Math.round(msg.data?.confidence_score ?? 0)}%` })
        } else if (msg.type === 'brain_update') {
          qc.invalidateQueries(['/api/signals/brain'])
          toast({ title: `AI Brain: ${msg.data?.strategy}`, description: msg.data?.reason })
        } else if (msg.type === 'notification') {
          toast({ title: msg.data?.title, description: msg.data?.message })
        }
        buffer.current = [...buffer.current, msg].slice(-MAX_MESSAGES)
        setState((p) => ({ ...p, messages: buffer.current }))
      }
    }
    connect()
    return () => {
      closed = true
      clearTimeout(timer)
      ws?.close()
    }
  }, [qc])

  const send = useCallback((message: any) => {
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message))
  }, [socket])

  return {
    socket,
    state,
    subscribe: useCallback((channel: string, symbol?: string) => send({ type: 'subscribe', channel, symbol }), [send]),
    unsubscribe: useCallback((channel: string, symbol?: string) => send({ type: 'unsubscribe', channel, symbol }), [send]),
    sendMessage: send,
  }
}

const WebSocketContext = createContext<UseWebSocketReturn | undefined>(undefined)

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const websocket = useWebSocket()
  return <WebSocketContext.Provider value={websocket}>{children}</WebSocketContext.Provider>
}

export function useWebSocketContext() {
  const context = useContext(WebSocketContext)
  if (!context) throw new Error('useWebSocketContext must be used within WebSocketProvider')
  return context
}
