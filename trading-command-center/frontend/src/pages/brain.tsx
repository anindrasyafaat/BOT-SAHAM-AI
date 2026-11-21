import { useQueryClient } from 'react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useApi, postApi, ApiState } from '@/hooks/use-api'
import { toast } from '@/hooks/use-toast'
import { cn, formatDateTime } from '@/lib/utils'
import { Brain, Power } from 'lucide-react'

interface Perf {
  total_signals: number
  winning_signals: number
  losing_signals: number
  win_rate: number | null
  avg_profit: number | null
  avg_loss: number | null
  profit_factor: number | null
}
interface Strategy {
  strategy_name: string
  enabled: boolean
  min_confidence: number
  performance: Perf | null
}
interface BrainEvent {
  time: string
  strategy: string
  reason: string
  expectancy: number
  win_rate: number
  closed: number
}

const MIN_SAMPLE = 20 // sama dengan backend/signals/learning.py

function expectancy(p: Perf) {
  const wr = (p.win_rate ?? 0) / 100
  return wr * (p.avg_profit ?? 0) + (1 - wr) * (p.avg_loss ?? 0)
}

export function BrainPage() {
  const qc = useQueryClient()
  const { data, isLoading, error } = useApi<{ strategies: Strategy[]; log: BrainEvent[] }>('/api/signals/brain', 15000)

  const toggle = async (name: string) => {
    try {
      await postApi(`/api/signals/strategies/${encodeURIComponent(name)}/toggle`)
      qc.invalidateQueries(['/api/signals/brain'])
    } catch (e) {
      toast({ title: `Gagal mengubah ${name}`, description: (e as Error).message, variant: 'destructive' })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Brain className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Brain</h1>
          <p className="text-muted-foreground">
            Setiap strategi belajar dari sinyal yang sudah ditutup: yang merugi jadi lebih selektif atau dimatikan,
            yang untung diberi ruang lebih.
          </p>
        </div>
      </div>

      <ApiState isLoading={isLoading} error={error} />

      {data && (
        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Parameter hasil belajar</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-muted-foreground">
                  <tr>
                    <th className="py-2">Strategi</th>
                    <th>Status</th>
                    <th className="text-right">Ambang</th>
                    <th className="text-right">Win rate</th>
                    <th className="text-right">Expectancy</th>
                    <th className="text-right">PF</th>
                    <th className="pl-4">Kematangan</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data.strategies.map((s) => {
                    const p = s.performance
                    const closed = p ? p.winning_signals + p.losing_signals : 0
                    const exp = p ? expectancy(p) : null
                    return (
                      <tr key={s.strategy_name} className="border-t">
                        <td className="py-2 font-medium">{s.strategy_name}</td>
                        <td>
                          <Badge variant={s.enabled ? 'default' : 'destructive'}>{s.enabled ? 'aktif' : 'mati'}</Badge>
                        </td>
                        <td className="text-right tabular-nums">{s.min_confidence.toFixed(0)}%</td>
                        <td className="text-right tabular-nums">{p?.win_rate != null ? `${p.win_rate.toFixed(1)}%` : '–'}</td>
                        <td className={cn('text-right tabular-nums', exp != null && (exp >= 0 ? 'text-green-500' : 'text-red-500'))}>
                          {exp != null ? `${exp.toFixed(2)}%` : '–'}
                        </td>
                        <td className="text-right tabular-nums">{p?.profit_factor != null ? p.profit_factor.toFixed(2) : '–'}</td>
                        <td className="pl-4 w-40">
                          <div className="h-2 rounded bg-muted" title={`${closed}/${MIN_SAMPLE} sinyal tertutup`}>
                            <div className="h-2 rounded bg-primary" style={{ width: `${Math.min(100, (closed / MIN_SAMPLE) * 100)}%` }} />
                          </div>
                        </td>
                        <td className="text-right">
                          <Button size="sm" variant="ghost" onClick={() => toggle(s.strategy_name)} aria-label={`Toggle ${s.strategy_name}`}>
                            <Power className="h-4 w-4" />
                          </Button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Jejak keputusan</CardTitle>
            </CardHeader>
            <CardContent>
              {data.log.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Belum ada penyesuaian. Brain mulai menilai sebuah strategi setelah {MIN_SAMPLE} sinyalnya tertutup.
                </p>
              ) : (
                <ol className="space-y-3 text-sm">
                  {data.log.map((e, i) => (
                    <li key={i} className="border-l-2 border-primary pl-3">
                      <div className="font-medium">{e.strategy}</div>
                      <div>{e.reason}</div>
                      <div className="text-xs text-muted-foreground">
                        {formatDateTime(e.time)} · WR {e.win_rate}% · exp {e.expectancy}% · n={e.closed}
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
