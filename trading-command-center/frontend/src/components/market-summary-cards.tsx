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

interface MarketSummaryCardsProps {
  marketType: string
}

export function MarketSummaryCards({ marketType }: MarketSummaryCardsProps) {
  // Mock data untuk demo
  const summaryData = {
    total_symbols: 150,
    advancers: 85,
    decliners: 45,
    unchanged: 20,
    advancers_pct: 56.67,
    decliners_pct: 30.0,
    unchanged_pct: 13.33,
    volume_total: 1250000000,
    market_cap_total: 8500000000000
  }

  const cards = [
    {
      title: 'Total Symbols',
      value: formatNumber(summaryData.total_symbols),
      icon: BarChart3,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10'
    },
    {
      title: 'Advancers',
      value: formatNumber(summaryData.advancers),
      subValue: formatPercentage(summaryData.advancers_pct),
      icon: TrendingUp,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10'
    },
    {
      title: 'Decliners',
      value: formatNumber(summaryData.decliners),
      subValue: formatPercentage(summaryData.decliners_pct),
      icon: TrendingDown,
      color: 'text-red-500',
      bgColor: 'bg-red-500/10'
    },
    {
      title: 'Unchanged',
      value: formatNumber(summaryData.unchanged),
      subValue: formatPercentage(summaryData.unchanged_pct),
      icon: Activity,
      color: 'text-yellow-500',
      bgColor: 'bg-yellow-500/10'
    },
    {
      title: 'Total Volume',
      value: formatNumber(summaryData.volume_total),
      icon: DollarSign,
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10'
    },
    {
      title: 'Market Cap',
      value: formatNumber(summaryData.market_cap_total),
      icon: BarChart3,
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
                  {card.subValue} of total
                </p>
              )}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}