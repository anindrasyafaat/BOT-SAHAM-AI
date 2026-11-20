import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useApi, ApiState } from '@/hooks/use-api'
import { cn, formatNumber, formatVolume, formatPercentage } from '@/lib/utils'

const SCREENS = [
  { key: 'gainers', label: 'Top Gainers' },
  { key: 'losers', label: 'Top Losers' },
  { key: 'volume-explosion', label: 'Volume Explosion' },
  { key: 'breakouts', label: 'Breakouts' },
  { key: 'oversold', label: 'Oversold' },
]

interface Row {
  symbol: string
  name: string
  price: number
  change_percent: number
  volume: number
  volume_ratio?: number
  criteria_met?: string[]
}

export function ScreenerPage() {
  const [screen, setScreen] = useState(SCREENS[0].key)
  const { data, isLoading, error } = useApi<Row[]>(`/api/screener/${screen}`, 60000)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Stock Screener</h1>
        <p className="text-muted-foreground">Saring peluang dengan preset momentum, volume, dan reversal.</p>
      </div>

      <div className="flex flex-wrap gap-2" role="tablist">
        {SCREENS.map((s) => (
          <Button key={s.key} role="tab" aria-selected={screen === s.key} size="sm" variant={screen === s.key ? 'default' : 'outline'} onClick={() => setScreen(s.key)}>
            {s.label}
          </Button>
        ))}
      </div>

      <Card>
        <CardContent className="overflow-x-auto pt-6">
          <ApiState isLoading={isLoading} error={error} />
          {data && (
            <table className="w-full text-sm">
              <thead className="text-left text-muted-foreground">
                <tr><th className="py-2">Simbol</th><th>Nama</th><th className="text-right">Harga</th><th className="text-right">Perubahan</th><th className="text-right">Volume</th><th className="text-right">Vol ratio</th><th className="pl-4">Kriteria</th></tr>
              </thead>
              <tbody>
                {data.map((r) => (
                  <tr key={r.symbol} className="border-t">
                    <td className="py-2 font-medium">{r.symbol}</td>
                    <td>{r.name}</td>
                    <td className="text-right tabular-nums">{formatNumber(r.price)}</td>
                    <td className={cn('text-right tabular-nums', r.change_percent >= 0 ? 'text-green-500' : 'text-red-500')}>{formatPercentage(r.change_percent)}</td>
                    <td className="text-right tabular-nums">{formatVolume(r.volume)}</td>
                    <td className="text-right tabular-nums">{r.volume_ratio ? `${r.volume_ratio.toFixed(1)}×` : '–'}</td>
                    <td className="pl-4"><div className="flex flex-wrap gap-1">{r.criteria_met?.map((c) => <Badge key={c} variant="secondary">{c}</Badge>)}</div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
