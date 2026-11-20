import React from 'react'
import { cn, formatCurrency, formatNumber, formatPercentage } from '@/lib/utils'

interface HeatmapData {
  symbol: string
  name: string
  price: number
  change: number
  change_percent: number
  volume: number
  market_cap?: number
  color: string
}

interface MarketHeatmapProps {
  data: HeatmapData[]
  className?: string
}

export function MarketHeatmap({ data, className }: MarketHeatmapProps) {
  if (!data || data.length === 0) {
    return (
      <div className={className}>
        <div className="text-center text-muted-foreground py-8">
          No market data available
        </div>
      </div>
    )
  }

  // Sort by change percent for visual effect
  const sortedData = [...data].sort((a, b) => b.change_percent - a.change_percent)

  return (
    <div className={cn("grid grid-cols-4 sm:grid-cols-6 lg:grid-cols-8 gap-2", className)}>
      {sortedData.map((item) => (
        <div
          key={item.symbol}
          className="group relative p-2 rounded cursor-pointer transition-all duration-200 hover:scale-105 hover:shadow-lg"
          style={{ backgroundColor: item.color }}
          title={`${item.name} (${item.symbol})\nPrice: ${formatCurrency(item.price)}\nChange: ${formatPercentage(item.change_percent)}`}
        >
          <div className="text-center">
            <div className="text-xs font-bold text-gray-900 truncate">
              {item.symbol}
            </div>
            <div className="text-xs text-gray-800 mt-1">
              {formatPercentage(item.change_percent)}
            </div>
          </div>
          
          {/* Hover tooltip */}
          <div className="absolute z-10 invisible group-hover:visible bg-background text-foreground p-3 rounded-lg shadow-lg border min-w-[200px] -top-16 left-1/2 transform -translate-x-1/2">
            <div className="font-semibold">{item.name}</div>
            <div className="text-sm text-muted-foreground">{item.symbol}</div>
            <div className="mt-2 space-y-1 text-sm">
              <div>Price: {formatCurrency(item.price)}</div>
              <div>Change: {formatPercentage(item.change_percent)}</div>
              <div>Volume: {formatNumber(item.volume)}</div>
              {item.market_cap && (
                <div>Market Cap: {formatNumber(item.market_cap)}</div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}