import { useQuery, useQueryClient } from 'react-query'
import { useWebSocketContext } from './use-websocket'
import { useEffect, useState } from 'react'

export interface MarketData {
  symbol: string
  name: string
  current_price: number
  open_price: number
  high_price: number
  low_price: number
  close_price: number
  volume: number
  volume_avg?: number
  market_cap?: number
  pe_ratio?: number
  pb_ratio?: number
  dividend_yield?: number
  change_amount: number
  change_percent: number
  timestamp: string
  market_type: string
  exchange?: string
  currency?: string
}

export interface MarketSummary {
  market_type: string
  total_stocks: number
  advancers: number
  decliners: number
  unchanged: number
  index_value?: number
  index_change?: number
  index_change_percent?: number
  fear_greed_index?: number
  vix_level?: number
  timestamp: string
}

export function useMarketData(symbol?: string) {
  const queryClient = useQueryClient()
  const { state } = useWebSocketContext()
  const [realtimeData, setRealtimeData] = useState<Record<string, MarketData>>({})

  // Fetch initial market data
  const { data: marketData, isLoading, error } = useQuery(
    ['marketData', symbol],
    async () => {
      const response = await fetch(
        symbol ? `/api/market/realtime/${symbol}` : '/api/market/realtime'
      )
      if (!response.ok) throw new Error('Failed to fetch market data')
      return response.json()
    },
    {
      staleTime: 30000, // 30 seconds
      refetchInterval: 60000, // 1 minute
    }
  )

  // Handle WebSocket updates
  useEffect(() => {
    const marketMessages = state.messages.filter(msg => msg.type === 'market_update')
    
    marketMessages.forEach(message => {
      if (message.data?.symbol) {
        setRealtimeData(prev => ({
          ...prev,
          [message.data.symbol]: message.data
        }))
        
        // Update React Query cache
        queryClient.setQueryData(['marketData', message.data.symbol], (oldData: any) => {
          if (oldData) {
            return {
              ...oldData,
              data: message.data
            }
          }
          return oldData
        })
      }
    })
  }, [state.messages, queryClient])

  return {
    data: symbol ? realtimeData[symbol] || marketData?.data : marketData?.data,
    isLoading,
    error,
    realtimeData
  }
}

export function useMarketSummary() {
  const { data, isLoading, error } = useQuery(
    'marketSummary',
    async () => {
      const response = await fetch('/api/market/market-summary')
      if (!response.ok) throw new Error('Failed to fetch market summary')
      return response.json()
    },
    {
      staleTime: 60000, // 1 minute
      refetchInterval: 120000, // 2 minutes
    }
  )

  return {
    data: data?.data,
    isLoading,
    error
  }
}

export function useTopMovers(limit: number = 10, marketType: string = 'all') {
  const { data, isLoading, error } = useQuery(
    ['topMovers', limit, marketType],
    async () => {
      const response = await fetch(
        `/api/market/top-movers?limit=${limit}&market_type=${marketType}`
      )
      if (!response.ok) throw new Error('Failed to fetch top movers')
      return response.json()
    },
    {
      staleTime: 30000, // 30 seconds
      refetchInterval: 60000, // 1 minute
    }
  )

  return {
    data: data?.data,
    isLoading,
    error
  }
}

export function useMarketHeatmap(marketType: string = 'all') {
  const { data, isLoading, error } = useQuery(
    ['heatmap', marketType],
    async () => {
      const response = await fetch(`/api/market/heatmap?market_type=${marketType}`)
      if (!response.ok) throw new Error('Failed to fetch heatmap')
      return response.json()
    },
    {
      staleTime: 30000, // 30 seconds
      refetchInterval: 60000, // 1 minute
    }
  )

  return {
    data: data?.data,
    isLoading,
    error
  }
}

export function useHistoricalData(symbol: string, days: number = 30) {
  const { data, isLoading, error } = useQuery(
    ['historical', symbol, days],
    async () => {
      const response = await fetch(`/api/market/historical/${symbol}?days=${days}`)
      if (!response.ok) throw new Error('Failed to fetch historical data')
      return response.json()
    },
    {
      staleTime: 300000, // 5 minutes
      enabled: !!symbol,
    }
  )

  return {
    data: data?.data,
    isLoading,
    error
  }
}

export function useEconomicCalendar() {
  const { data, isLoading, error } = useQuery(
    'economicCalendar',
    async () => {
      const response = await fetch('/api/market/economic-calendar')
      if (!response.ok) throw new Error('Failed to fetch economic calendar')
      return response.json()
    },
    {
      staleTime: 3600000, // 1 hour
      refetchInterval: 3600000, // 1 hour
    }
  )

  return {
    data: data?.data,
    isLoading,
    error
  }
}

export function useFearGreedIndex() {
  const { data, isLoading, error } = useQuery(
    'fearGreedIndex',
    async () => {
      const response = await fetch('/api/market/fear-greed-index')
      if (!response.ok) throw new Error('Failed to fetch Fear & Greed Index')
      return response.json()
    },
    {
      staleTime: 3600000, // 1 hour
      refetchInterval: 3600000, // 1 hour
    }
  )

  return {
    data: data?.data,
    isLoading,
    error
  }
}