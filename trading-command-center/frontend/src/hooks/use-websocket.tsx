import { useEffect, useRef, useState, useCallback } from 'react'
import { io, Socket } from 'socket.io-client'

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
  socket: Socket | null
  state: WebSocketState
  subscribe: (channel: string, symbol?: string) => void
  unsubscribe: (channel: string, symbol?: string) => void
  sendMessage: (message: any) => void
}

export function useWebSocket(): UseWebSocketReturn {
  const [socket, setSocket] = useState<Socket | null>(null)
  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    messages: [],
    error: null
  })
  const messageBuffer = useRef<WebSocketMessage[]>([])

  useEffect(() => {
    // Initialize WebSocket connection
    const ws = io('ws://localhost:8000', {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    })

    ws.on('connect', () => {
      console.log('✅ WebSocket connected')
      setState(prev => ({ ...prev, isConnected: true, error: null }))
      
      // Subscribe to default channels
      ws.emit('subscribe', { type: 'subscribe', channel: 'market_data' })
      ws.emit('subscribe', { type: 'subscribe', channel: 'signals' })
    })

    ws.on('disconnect', (reason) => {
      console.log('🔌 WebSocket disconnected:', reason)
      setState(prev => ({ ...prev, isConnected: false }))
    })

    ws.on('connect_error', (error) => {
      console.error('❌ WebSocket connection error:', error)
      setState(prev => ({ ...prev, error: error.message }))
    })

    ws.on('message', (message: WebSocketMessage) => {
      console.log('📡 WebSocket message received:', message.type)
      
      // Add to buffer dan state
      messageBuffer.current.push(message)
      
      // Keep only last 100 messages
      if (messageBuffer.current.length > 100) {
        messageBuffer.current = messageBuffer.current.slice(-100)
      }
      
      setState(prev => ({ ...prev, messages: messageBuffer.current }))
    })

    ws.on('market_update', (data) => {
      setState(prev => ({ 
        ...prev, 
        messages: [...prev.messages, { type: 'market_update', data }] 
      }))
    })

    ws.on('new_signal', (data) => {
      setState(prev => ({ 
        ...prev, 
        messages: [...prev.messages, { type: 'new_signal', data }] 
      }))
    })

    ws.on('market_summary', (data) => {
      setState(prev => ({ 
        ...prev, 
        messages: [...prev.messages, { type: 'market_summary', data }] 
      }))
    })

    setSocket(ws)

    // Cleanup
    return () => {
      if (ws) {
        ws.disconnect()
      }
    }
  }, [])

  const subscribe = useCallback((channel: string, symbol?: string) => {
    if (socket) {
      socket.emit('subscribe', { 
        type: 'subscribe', 
        channel, 
        symbol 
      })
    }
  }, [socket])

  const unsubscribe = useCallback((channel: string, symbol?: string) => {
    if (socket) {
      socket.emit('unsubscribe', { 
        type: 'unsubscribe', 
        channel, 
        symbol 
      })
    }
  }, [socket])

  const sendMessage = useCallback((message: any) => {
    if (socket) {
      socket.emit('message', message)
    }
  }, [socket])

  return {
    socket,
    state,
    subscribe,
    unsubscribe,
    sendMessage
  }
}

// WebSocket Provider untuk React Context
import { createContext, useContext } from 'react'

const WebSocketContext = createContext<UseWebSocketReturn | undefined>(undefined)

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const websocket = useWebSocket()
  
  return (
    <WebSocketContext.Provider value={websocket}>
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocketContext() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocketContext must be used within WebSocketProvider')
  }
  return context
}