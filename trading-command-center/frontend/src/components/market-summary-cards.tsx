import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  TrendingUp, 
  TrendingDown, 
  Activity,
  DollarSign,
  BarChart3,
  AlertCircle
} from 'lucide-react'
import { cn, formatNumber, formatPercentage } from '@/lib/utils'
import { useMarketData, type MarketData } from '@/hooks/use-market-data'

interface MarketSummaryCardsProps {
  marketType: string
}

export function MarketSummaryCards({ marketType }: MarketSummaryCardsProps) {
  const { data: all } = useMarketData()
  const inMarket = (q: MarketData) =>
    marketType === 'all' ||
    (marketType === 'crypto' ? q.market_type === 'crypto'
      : marketType === 'indonesia' ? q.symbol.endsWith('.JK')
      : q.market_type !== 'crypto' && !q.symbol.endsWith('.JK'))
  const quotes = Object.values((all ?? {}) as Record<string, MarketData>).filter(inMarket)
  const n = quotes.length || 1
  const up = quotes.filter((q) => q.change_percent > 0).length
  const down = quotes.filter((q) => q.change_percent < 0).length
  const flat = quotes.length - up - down
  const avg = quotes.reduce((s, q) => s + q.change_percent, 0) / n
  const top = quotes.reduce<MarketData | null>((b, q) => (!b || q.change_percent > b.change_percent ? q : b), null)
  const summaryData = {
    total_symbols: quotes.length, advancers: up, decliners: down, unchanged: flat,
    advancers_pct: (up / n) * 100, decliners_pct: (down / n) * 100, unchanged_pct: (flat / n) * 100,
  }

  const cards = [
    {
      title: 'Total Symbols',
      value: formatNumber(summaryData.total_symbols, 0),
      icon: BarChart3,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10'
    },
    {
      title: 'Advancers',
      value: formatNumber(summaryData.advancers, 0),
      subValue: `${formatPercentage(summaryData.advancers_pct)} dari total`,
      icon: TrendingUp,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10'
    },
    {
      title: 'Decliners',
      value: formatNumber(summaryData.decliners, 0),
      subValue: `${formatPercentage(summaryData.decliners_pct)} dari total`,
      icon: TrendingDown,
      color: 'text-red-500',
      bgColor: 'bg-red-500/10'
    },
    {
      title: 'Unchanged',
      value: formatNumber(summaryData.unchanged, 0),
      subValue: `${formatPercentage(summaryData.unchanged_pct)} dari total`,
      icon: Activity,
      color: 'text-yellow-500',
      bgColor: 'bg-yellow-500/10'
    },
    {
      title: 'Rata-rata perubahan',
      value: formatPercentage(avg),
      icon: Activity,
      color: avg >= 0 ? 'text-green-500' : 'text-red-500',
      bgColor: 'bg-purple-500/10'
    },
    {
      title: 'Top gainer',
      value: top ? top.symbol : '–',
      subValue: top ? `naik ${formatPercentage(top.change_percent)}` : undefined,
      icon: TrendingUp,
      color: 'text-indigo-500',
      bgColor: 'bg-indigo-500/10'
    }
  ]

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {cards.map((card, index) => {
        const Icon = card.icon
        
        return (
          <Card key={index} className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {card.title}
              </CardTitle>
              <div className={cn("p-2 rounded-lg", card.bgColor)}>
                <Icon className={cn("h-4 w-4", card.color)} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{card.value}</div>
              {card.subValue && (
                <p className="text-xs text-muted-foreground mt-1">
                  {card.subValue}
                </p>
              )}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}