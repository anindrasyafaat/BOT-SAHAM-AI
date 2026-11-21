import { useState } from 'react'
import { useQueryClient } from 'react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { useApi, postApi, ApiState } from '@/hooks/use-api'
import { toast } from '@/hooks/use-toast'
import { cn, formatCurrency, formatDateTime, formatNumber, formatPercentage } from '@/lib/utils'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts'

interface Summary { total_value: number; cash_balance: number; total_pnl: number; total_pnl_percent: number; today_pnl: number; today_pnl_percent: number }
interface Trade { id: number; symbol: string; side: string; quantity: number; price: number; value_idr: number; fees: number; realized_pnl: number | null; reason: string; trade_date: string }
interface Position { stop_loss: number | null; take_profit: number | null; symbol: string; name: string; quantity: number; avg_entry_price: number; current_price: number; market_value: number; unrealized_pnl: number; unrealized_pnl_percent: number }
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
  const trades = useApi<Trade[]>('/api/portfolio/trades?limit=50', 60000)
  const s = summary.data
  const qc = useQueryClient()
  const [order, setOrder] = useState({ symbol: '', quantity: '', stop_loss: '', take_profit: '' })
  const refresh = () => qc.invalidateQueries({ predicate: (q) => String(q.queryKey[0]).startsWith('/api/portfolio') })
  const run = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn()
      toast({ title: ok })
      refresh()
    } catch (e) {
      toast({ title: 'Gagal', description: (e as Error).message, variant: 'destructive' })
    }
  }
  const num = (v: string) => (v === '' ? undefined : parseFloat(v))
  const buy = (e: React.FormEvent) => {
    e.preventDefault()
    run(() => postApi('/api/portfolio/buy', {
      symbol: order.symbol.trim(), quantity: num(order.quantity), stop_loss: num(order.stop_loss), take_profit: num(order.take_profit),
    }), `Beli ${order.symbol.toUpperCase()} tereksekusi`).then(() => setOrder({ symbol: '', quantity: '', stop_loss: '', take_profit: '' }))
  }

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
        <CardHeader><CardTitle>Order beli (paper trading)</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={buy} className="flex flex-wrap items-end gap-2 text-sm">
            <Input className="w-32" placeholder="BBCA.JK" required value={order.symbol} aria-label="Simbol" onChange={(e) => setOrder({ ...order, symbol: e.target.value })} />
            <Input className="w-28" type="number" step="any" min="0" placeholder="Jumlah" required value={order.quantity} aria-label="Jumlah" onChange={(e) => setOrder({ ...order, quantity: e.target.value })} />
            <Input className="w-28" type="number" step="any" min="0" placeholder="Stop loss" value={order.stop_loss} aria-label="Stop loss" onChange={(e) => setOrder({ ...order, stop_loss: e.target.value })} />
            <Input className="w-28" type="number" step="any" min="0" placeholder="Take profit" value={order.take_profit} aria-label="Take profit" onChange={(e) => setOrder({ ...order, take_profit: e.target.value })} />
            <Button type="submit" size="sm">Beli harga pasar</Button>
          </form>
          <p className="mt-2 text-xs text-muted-foreground">Saham IDX dalam lembar, kelipatan 100 (1 lot). Fee beli/jual mengikuti konfigurasi server. Posisi otomatis ditutup saat menyentuh SL/TP.</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Posisi terbuka</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto">
          <ApiState isLoading={positions.isLoading} error={positions.error} />
          {positions.data?.length === 0 && <p className="text-sm text-muted-foreground">Belum ada posisi.</p>}
          {positions.data && positions.data.length > 0 && (
            <table className="w-full text-sm">
              <thead className="text-left text-muted-foreground">
                <tr><th className="py-2">Simbol</th><th>Nama</th><th className="text-right">Lot/Qty</th><th className="text-right">Avg</th><th className="text-right">Harga</th><th className="text-right">Nilai</th><th className="text-right">P&L</th><th className="text-right">SL / TP</th><th /></tr>
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
                    <td className="text-right tabular-nums text-muted-foreground">{p.stop_loss ? formatNumber(p.stop_loss) : '–'} / {p.take_profit ? formatNumber(p.take_profit) : '–'}</td>
                    <td className="text-right">
                      <Button size="sm" variant="outline" onClick={() => run(() => postApi('/api/portfolio/close-position', { symbol: p.symbol }), `Posisi ${p.symbol} ditutup`)}>Tutup</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Riwayat transaksi</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto">
          {trades.data?.length === 0 && <p className="text-sm text-muted-foreground">Belum ada transaksi.</p>}
          {trades.data && trades.data.length > 0 && (
            <table className="w-full text-sm">
              <thead className="text-left text-muted-foreground">
                <tr><th className="py-2">Waktu</th><th>Simbol</th><th>Sisi</th><th className="text-right">Qty</th><th className="text-right">Harga</th><th className="text-right">Nilai (IDR)</th><th className="text-right">Fee</th><th className="text-right">P&L realisasi</th><th className="pl-4">Alasan</th></tr>
              </thead>
              <tbody>
                {trades.data.map((t) => (
                  <tr key={t.id} className="border-t">
                    <td className="py-2 text-muted-foreground">{formatDateTime(t.trade_date)}</td>
                    <td className="font-medium">{t.symbol}</td>
                    <td><Badge className={cn(t.side === 'BUY' ? 'bg-green-600' : 'bg-red-600', 'text-white')}>{t.side}</Badge></td>
                    <td className="text-right tabular-nums">{formatNumber(t.quantity, 0)}</td>
                    <td className="text-right tabular-nums">{formatNumber(t.price)}</td>
                    <td className="text-right tabular-nums">{idr(t.value_idr)}</td>
                    <td className="text-right tabular-nums">{idr(t.fees)}</td>
                    <td className={cn('text-right tabular-nums', t.realized_pnl == null ? '' : t.realized_pnl >= 0 ? 'text-green-500' : 'text-red-500')}>{t.realized_pnl == null ? '–' : idr(t.realized_pnl)}</td>
                    <td className="pl-4">{t.reason}</td>
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
