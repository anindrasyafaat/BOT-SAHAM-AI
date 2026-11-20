import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useApi, ApiState } from '@/hooks/use-api'
import { cn, formatCurrency, formatNumber, formatPercentage } from '@/lib/utils'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts'

interface Summary { total_value: number; cash_balance: number; total_pnl: number; total_pnl_percent: number; today_pnl: number; today_pnl_percent: number }
interface Position { symbol: string; name: string; quantity: number; avg_entry_price: number; current_price: number; market_value: number; unrealized_pnl: number; unrealized_pnl_percent: number }
type Perf = Record<string, number>

const idr = (v: number) => formatCurrency(v, 'IDR')
const PERF_LABELS: [string, string, (v: number) => string][] = [
  ['annualized_return', 'Return tahunan', (v) => formatPercentage(v)],
  ['sharpe_ratio', 'Sharpe', (v) => v.toFixed(2)],
  ['max_drawdown', 'Max drawdown', (v) => formatPercentage(v)],
  ['win_rate', 'Win rate', (v) => `${v.toFixed(1)}%`],
  ['profit_factor', 'Profit factor', (v) => v.toFixed(2)],
  ['total_trades', 'Total trade', (v) => String(v)],
]

export function PortfolioPage() {
  const summary = useApi<Summary>('/api/portfolio/', 60000)
  const positions = useApi<Position[]>('/api/portfolio/positions', 60000)
  const perf = useApi<Perf>('/api/portfolio/performance', 300000)
  const equity = useApi<{ date: string; value: number }[]>('/api/portfolio/equity-curve', 300000)
  const s = summary.data

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Portfolio</h1>
        <p className="text-muted-foreground">Posisi, P&L, dan kurva ekuitas.</p>
      </div>

      <ApiState isLoading={summary.isLoading} error={summary.error} />
      {s && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ['Nilai total', idr(s.total_value), null],
            ['Kas', idr(s.cash_balance), null],
            ['Total P&L', `${idr(s.total_pnl)} (${formatPercentage(s.total_pnl_percent)})`, s.total_pnl],
            ['P&L hari ini', `${idr(s.today_pnl)} (${formatPercentage(s.today_pnl_percent)})`, s.today_pnl],
          ].map(([label, value, sign]) => (
            <Card key={label as string}>
              <CardContent className="pt-6">
                <div className="text-sm text-muted-foreground">{label}</div>
                <div className={cn('text-xl font-bold', sign != null && ((sign as number) >= 0 ? 'text-green-500' : 'text-red-500'))}>{value}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Kurva ekuitas (90 hari)</CardTitle></CardHeader>
          <CardContent className="h-64">
            {equity.data && (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={equity.data.map((p) => ({ date: p.date.slice(5, 10), value: Math.round(p.value) }))}>
                  <XAxis dataKey="date" fontSize={12} minTickGap={24} />
                  <YAxis fontSize={12} tickFormatter={(v) => `${(v / 1e6).toFixed(0)}jt`} domain={['auto', 'auto']} />
                  <Tooltip formatter={(v: number) => idr(v)} />
                  <Line type="monotone" dataKey="value" stroke="#3b82f6" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Statistik</CardTitle></CardHeader>
          <CardContent>
            {perf.data && (
              <dl className="grid grid-cols-2 gap-3 text-sm">
                {PERF_LABELS.filter(([k]) => perf.data![k] != null).map(([k, label, fmt]) => (
                  <div key={k}><dt className="text-muted-foreground">{label}</dt><dd className="font-semibold tabular-nums">{fmt(perf.data![k])}</dd></div>
                ))}
              </dl>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Posisi terbuka</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto">
          <ApiState isLoading={positions.isLoading} error={positions.error} />
          {positions.data && (
            <table className="w-full text-sm">
              <thead className="text-left text-muted-foreground">
                <tr><th className="py-2">Simbol</th><th>Nama</th><th className="text-right">Lot/Qty</th><th className="text-right">Avg</th><th className="text-right">Harga</th><th className="text-right">Nilai</th><th className="text-right">P&L</th></tr>
              </thead>
              <tbody>
                {positions.data.map((p) => (
                  <tr key={p.symbol} className="border-t">
                    <td className="py-2 font-medium">{p.symbol}</td>
                    <td>{p.name}</td>
                    <td className="text-right tabular-nums">{formatNumber(p.quantity, 0)}</td>
                    <td className="text-right tabular-nums">{formatNumber(p.avg_entry_price)}</td>
                    <td className="text-right tabular-nums">{formatNumber(p.current_price)}</td>
                    <td className="text-right tabular-nums">{idr(p.market_value)}</td>
                    <td className={cn('text-right tabular-nums', p.unrealized_pnl >= 0 ? 'text-green-500' : 'text-red-500')}>
                      {idr(p.unrealized_pnl)} ({formatPercentage(p.unrealized_pnl_percent)})
                    </td>
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
