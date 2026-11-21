import React from 'react'

interface FearGreedData {
  value: number
  sentiment: string
  color: string
  timestamp: string
  components: {
    stock_price_strength: number
    stock_price_momentum: number
    market_volatility: number
    put_call_ratio: number
    junk_bond_demand: number
    safe_haven_demand: number
  }
}

interface FearGreedGaugeProps {
  data: FearGreedData
  className?: string
}

export function FearGreedGauge({ data, className }: FearGreedGaugeProps) {
  const getGaugeColor = (value: number): string => {
    if (value >= 75) return '#ef4444' // Extreme Greed - Red
    if (value >= 55) return '#f97316' // Greed - Orange
    if (value >= 45) return '#eab308' // Neutral - Yellow
    if (value >= 25) return '#22c55e' // Fear - Green
    return '#06b6d4' // Extreme Fear - Cyan
  }

  const getGaugeRotation = (value: number): number => {
    // Convert 0-100 to -90 to 90 degrees
    return (value / 100) * 180 - 90
  }

  const rotation = getGaugeRotation(data.value)
  const gaugeColor = getGaugeColor(data.value)

  return (
    <div className={className}>
      {/* Gauge */}
      <div className="relative w-full h-32 mb-4">
        <svg className="w-full h-full" viewBox="0 0 200 100">
          {/* Background arc */}
          <path
            d="M 20 80 A 80 80 0 0 1 180 80"
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="8"
            strokeLinecap="round"
          />
          
          {/* Value arc */}
          <path
            d="M 20 80 A 80 80 0 0 1 180 80"
            fill="none"
            stroke={gaugeColor}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${(data.value / 100) * 160} 160`}
            strokeDashoffset="0"
            className="transition-all duration-500"
          />
          
          {/* Needle */}
          <g transform={`translate(100, 80)`}>
            <g transform={`rotate(${rotation})`}>
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="-60"
                stroke="#374151"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <circle cx="0" cy="0" r="4" fill="#374151" />
            </g>
          </g>
        </svg>
        
        {/* Value display */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div 
            className="text-3xl font-bold mb-1"
            style={{ color: gaugeColor }}
          >
            {data.value}
          </div>
          <div className="text-sm font-medium text-muted-foreground">
            {data.sentiment}
          </div>
        </div>
      </div>

      {/* Scale labels */}
      <div className="flex justify-between text-xs text-muted-foreground mb-4">
        <span>Extreme Fear</span>
        <span>Fear</span>
        <span>Neutral</span>
        <span>Greed</span>
        <span>Extreme Greed</span>
      </div>

      {/* Components */}
      <div className="space-y-2">
        <h4 className="text-sm font-medium mb-2">Components</h4>
        
        {Object.entries(data.components).map(([key, value]) => {
          const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
          
          return (
            <div key={key} className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">{label}</span>
              <div className="flex items-center space-x-2">
                <div className="w-16 h-1 bg-gray-200 rounded">
                  <div 
                    className="h-full bg-primary rounded transition-all duration-300"
                    style={{ width: `${value}%` }}
                  />
                </div>
                <span className="text-xs font-medium w-8">{value}</span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Last updated */}
      <div className="text-xs text-muted-foreground mt-4 text-center">
        Last updated: {new Date(data.timestamp).toLocaleTimeString()}
      </div>
    </div>
  )
}