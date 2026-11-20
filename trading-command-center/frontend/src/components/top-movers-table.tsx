import React from 'react'
import { cn, formatCurrency, formatNumber, formatPercentage, getChangeColor, getChangeIcon } from '@/lib/utils'

interface TopMoversData {
  top_gainers: Array<{
    symbol: string
    name: string
    price: number
    change: number
    change_percent: number
    volume: number
  }>
  top_losers: Array<{
    symbol: string
    name: string
    price: number
    change: number
    change_percent: number
    volume: number
  }>
  most_active: Array<{
    symbol: string
    name: string
    price: number
    volume: number
    volume_avg?: number
    change_percent: number
  }>
}

interface TopMoversTableProps {
  data: TopMoversData
  className?: string
}

export function TopMoversTable({ data, className }: TopMoversTableProps) {
  const [activeTab, setActiveTab] = React.useState<'gainers' | 'losers' | 'active'>('gainers')

  const tabs = [
    { key: 'gainers', label: 'Top Gainers', icon: '↗', color: 'text-green-500' },
    { key: 'losers', label: 'Top Losers', icon: '↘', color: 'text-red-500' },
    { key: 'active', label: 'Most Active', icon: '⚡', color: 'text-yellow-500' }
  ]

  const renderTable = (items: any[], type: string) => (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left py-2">Symbol</th>
            <th className="text-right py-2">Price</th>
            <th className="text-right py-2">Change</th>
            <th className="text-right py-2">Volume</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={item.symbol} className="border-b hover:bg-accent/50">
              <td className="py-3">
                <div>
                  <div className="font-medium">{item.symbol}</div>
                  <div className="text-xs text-muted-foreground truncate">
                    {item.name}
                  </div>
                </div>
              </td>
              <td className="text-right py-3">
                {formatCurrency(item.price)}
              </td>
              <td className="text-right py-3">
                <div className={cn("flex items-center justify-end space-x-1", getChangeColor(item.change_percent))}>
                  <span>{getChangeIcon(item.change_percent)}</span>
                  <span>{formatPercentage(item.change_percent)}</span>
                </div>
              </td>
              <td className="text-right py-3">
                {formatNumber(item.volume)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  return (
    <div className={className}>
      {/* Tabs */}
      <div className="flex space-x-1 mb-4 bg-muted p-1 rounded-lg">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={cn(
              "flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors",
              "flex items-center justify-center space-x-2",
              activeTab === tab.key
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <span className={tab.color}>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="min-h-[300px]">
        {activeTab === 'gainers' && renderTable(data.top_gainers, 'gainers')}
        {activeTab === 'losers' && renderTable(data.top_losers, 'losers')}
        {activeTab === 'active' && renderTable(data.most_active, 'active')}
      </div>
    </div>
  )
}