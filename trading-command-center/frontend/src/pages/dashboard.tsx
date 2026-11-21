import React, { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { useApi } from '@/hooks/use-api'
import { formatCurrency, formatPercentage, formatNumber } from '@/lib/utils'
import { 
  useMarketData, 
  useMarketSummary, 
  useTopMovers, 
  useMarketHeatmap,
  useFearGreedIndex,
  useEconomicCalendar
} from '@/hooks/use-market-data'
import { useWebSocketContext } from '@/hooks/use-websocket'

// Components
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { 
  TrendingUp, 
  TrendingDown, 
  Activity,
  DollarSign,
  BarChart3,
  Calendar,
  AlertCircle,
  ArrowUp,
  ArrowDown
} from 'lucide-react'

// Custom components
import { MarketHeatmap } from '@/components/market-heatmap'
import { TopMoversTable } from '@/components/top-movers-table'
import { MarketSummaryCards } from '@/components/market-summary-cards'
import { FearGreedGauge } from '@/components/fear-greed-gauge'
import { EconomicCalendar } from '@/components/economic-calendar'

export function DashboardPage() {
  const [selectedMarket, setSelectedMarket] = useState<'all' | 'indonesia' | 'us' | 'crypto'>('all')
  const { state: wsState } = useWebSocketContext()

  // Market data hooks
  const { data: marketSummary } = useMarketSummary()
  const { data: topMovers } = useTopMovers(10, selectedMarket)
  const { data: heatmapData } = useMarketHeatmap(selectedMarket)
  const { data: fearGreedData } = useFearGreedIndex()
  const { data: economicData } = useEconomicCalendar()
  const { data: recentSignals } = useApi<any[]>('/api/signals/?limit=5', 30000)

  // Real-time connection status
  const isConnected = wsState.isConnected

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Trading Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time market data and AI trading signals
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Connection Status */}
          <div className="flex items-center space-x-2">
            <div className={cn(
              "w-2 h-2 rounded-full",
              isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
            )} />
            <span className="text-sm text-muted-foreground">
              {isConnected ? 'Live' : 'Disconnected'}
            </span>
          </div>
          
          {/* Market Selector */}
          <select
            value={selectedMarket}
            onChange={(e) => setSelectedMarket(e.target.value as any)}
            className="px-3 py-2 text-sm border rounded-md bg-background"
          >
            <option value="all">All Markets</option>
            <option value="indonesia">Indonesia (IHSG)</option>
            <option value="us">US Markets</option>
            <option value="crypto">Cryptocurrency</option>
          </select>
        </div>
      </div>

      {/* Market Summary Cards */}
      <MarketSummaryCards marketType={selectedMarket} />

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Market Heatmap */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Market Heatmap</CardTitle>
                <Badge variant="outline">
                  {heatmapData?.length || 0} Symbols
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              {heatmapData ? (
                <MarketHeatmap data={heatmapData} />
              ) : (
                <div className="h-64 flex items-center justify-center">
                  <Skeleton className="h-64 w-full" />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Top Movers */}
          <Card>
            <CardHeader>
              <CardTitle>Top Movers</CardTitle>
            </CardHeader>
            <CardContent>
              {topMovers ? (
                <TopMoversTable data={topMovers} />
              ) : (
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Fear & Greed Index */}
          <Card>
            <CardHeader>
              <CardTitle>Fear & Greed Index</CardTitle>
            </CardHeader>
            <CardContent>
              {fearGreedData ? (
                <FearGreedGauge data={fearGreedData} />
              ) : (
                <Skeleton className="h-48 w-full" />
              )}
            </CardContent>
          </Card>

          {/* Economic Calendar */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Economic Calendar</CardTitle>
                <Calendar className="h-4 w-4 text-muted-foreground" />
              </div>
            </CardHeader>
            <CardContent>
              {economicData ? (
                <EconomicCalendar data={economicData} />
              ) : (
                <Skeleton className="h-64 w-full" />
              )}
            </CardContent>
          </Card>

          {/* Recent Signals */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Signals</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {(recentSignals ?? []).map((signal: any) => (
                  <div key={signal.id} className="flex items-center justify-between p-3 rounded-lg bg-accent/50">
                    <div>
                      <div className="font-medium">{signal.symbol}</div>
                      <div className="text-sm text-muted-foreground">{signal.strategy_name}</div>
                    </div>
                    <Badge variant={String(signal.signal_type).includes('BUY') ? 'default' : 'destructive'} className="ml-2">
                      {signal.signal_type}
                    </Badge>
                  </div>
                ))}
                {recentSignals?.length === 0 && <p className="text-sm text-muted-foreground">Belum ada sinyal aktif.</p>}
                
                {wsState.messages.filter(msg => msg.type === 'new_signal').length === 0 && (
                  <div className="text-center text-muted-foreground py-8">
                    <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No recent signals</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}