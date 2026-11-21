import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Calendar, Clock, AlertCircle } from 'lucide-react'

interface EconomicEvent {
  date: string
  time: string
  currency: string
  event: string
  impact: 'High' | 'Medium' | 'Low'
  actual: string
  forecast: string
  previous: string
}

interface EconomicCalendarProps {
  data: EconomicEvent[]
  className?: string
}

export function EconomicCalendar({ data, className }: EconomicCalendarProps) {
  const getImpactColor = (impact: string): string => {
    switch (impact) {
      case 'High':
        return 'bg-red-500 text-white'
      case 'Medium':
        return 'bg-yellow-500 text-black'
      case 'Low':
        return 'bg-green-500 text-white'
      default:
        return 'bg-gray-500 text-white'
    }
  }

  const getImpactIcon = (impact: string): React.ReactNode => {
    switch (impact) {
      case 'High':
        return <AlertCircle className="h-3 w-3" />
      case 'Medium':
        return <AlertCircle className="h-3 w-3" />
      case 'Low':
        return <AlertCircle className="h-3 w-3" />
      default:
        return null
    }
  }

  return (
    <div className={className}>
      <div className="space-y-3 max-h-64 overflow-y-auto">
        {data.map((event, index) => (
          <div 
            key={index} 
            className="p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors cursor-pointer"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center space-x-2">
                <Badge className={getImpactColor(event.impact)}>
                  <div className="flex items-center space-x-1">
                    {getImpactIcon(event.impact)}
                    <span className="text-xs">{event.impact}</span>
                  </div>
                </Badge>
                <span className="text-xs font-medium">{event.currency}</span>
              </div>
              <div className="flex items-center space-x-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                <span>{event.time}</span>
              </div>
            </div>
            
            <div className="text-sm font-medium mb-2">{event.event}</div>
            
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <span className="text-muted-foreground">Previous:</span>
                <div className="font-medium">{event.previous || 'N/A'}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Forecast:</span>
                <div className="font-medium">{event.forecast || 'N/A'}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Actual:</span>
                <div className="font-medium text-primary">{event.actual || 'N/A'}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {data.length === 0 && (
        <div className="text-center py-8 text-muted-foreground">
          <Calendar className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>Kalender ekonomi belum terhubung ke sumber data</p>
        </div>
      )}
    </div>
  )
}