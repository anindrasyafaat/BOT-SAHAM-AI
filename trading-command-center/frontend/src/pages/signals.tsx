import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { useApi, ApiState } from '@/hooks/use-api'
import { cn, formatNumber, formatDateTime } from '@/lib/utils'

interface Signal {
  id: number
  symbol: string
  signal_type: string
  strategy_name: string
  timeframe: string
  confidence_score: number
  entry_price: number
  target_price_1: number | null
  stop_loss: number
  risk_reward_ratio: number | null
  generated_at: string
}

export function SignalsPage() {
  const [minConf, setMinConf] = useState(70)
  const [symbol, setSymbol] = useState('')
  const q = new URLSearchParams({ min_confidence: String(minConf), limit: '100' })
  if (symbol) q.set('symbol', symbol.toUpperCase())
  const { data, isLoading, error } = useApi<Signal[]>(`/api/signals/?${q}`, 30000)
  const { data: perf } = useApi<{ overall: { total_signals: number; win_rate: number } }>('/api/signals/performance', 120000)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Trading Signals</h1>
        <p className="text-muted-foreground">Sinyal aktif yang lolos ambang confidence hasil belajar AI Brain.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card><CardContent className="pt-6"><div className="text-sm text-muted-foreground">Sinyal aktif</div><div className="text-2xl font-bold">{data?.length ?? '–'}</div></CardContent></Card>
        <Card><CardContent className="pt-6"><div className="text-sm text-muted-foreground">Total sinyal 30 hari</div><div className="text-2xl font-bold">{perf?.overall.total_signals ?? '–'}</div></CardContent></Card>
        <Card><CardContent className="pt-6"><div className="text-sm text-muted-foreground">Win rate 30 hari</div><div className="text-2xl font-bold">{perf ? `${perf.overall.win_rate.toFixed(1)}%` : '–'}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-4">
          <CardTitle>Sinyal aktif</CardTitle>
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <Input className="w-32" placeholder="Simbol" value={symbol} onChange={(e) => setSymbol(e.target.value)} aria-label="Filter simbol" />
            <label className="flex items-center gap-2">
              Min confidence {minConf}%
              <input type="range" min={50} max={95} value={minConf} onChange={(e) => setMinConf(+e.target.value)} />
            </label>
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <ApiState isLoading={isLoading} error={error} />
          {data && data.length === 0 && <p className="py-8 text-center text-muted-foreground">Belum ada sinyal yang memenuhi filter.</p>}
          {data && data.length > 0 && (
            <table className="w-full text-sm">
              <thead className="text-left text-muted-foreground">
                <tr><th className="py-2">Simbol</th><th>Arah</th><th>Strategi</th><th className="w-40">Confidence</th><th className="text-right">Entry</th><th className="text-right">TP1</th><th className="text-right">SL</th><th className="text-right">R:R</th><th className="text-right">Waktu</th></tr>
              </thead>
              <tbody>
                {data.map((s) => {
                  const buy = s.signal_type.toUpperCase().includes('BUY')
                  return (
                    <tr key={s.id} className="border-t">
                      <td className="py-2 font-medium">{s.symbol}</td>
                      <td><Badge className={cn(buy ? 'bg-green-600' : 'bg-red-600', 'text-white')}>{s.signal_type}</Badge></td>
                      <td>{s.strategy_name} <span className="text-muted-foreground">({s.timeframe})</span></td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="h-2 flex-1 rounded bg-muted"><div className="h-2 rounded bg-primary" style={{ width: `${s.confidence_score}%` }} /></div>
                          <span className="tabular-nums">{s.confidence_score.toFixed(0)}</span>
                        </div>
                      </td>
                      <td className="text-right tabular-nums">{formatNumber(s.entry_price)}</td>
                      <td className="text-right tabular-nums text-green-500">{s.target_price_1 != null ? formatNumber(s.target_price_1) : '–'}</td>
                      <td className="text-right tabular-nums text-red-500">{formatNumber(s.stop_loss)}</td>
                      <td className="text-right tabular-nums">{s.risk_reward_ratio?.toFixed(2) ?? '–'}</td>
                      <td className="text-right text-muted-foreground">{formatDateTime(s.generated_at)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
