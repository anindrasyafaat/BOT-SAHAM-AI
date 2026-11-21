import { useState } from 'react'
import { useQueryClient } from 'react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useApi, postApi, sendApi, ApiState } from '@/hooks/use-api'
import { toast } from '@/hooks/use-toast'
import { formatDateTime } from '@/lib/utils'

type Settings = Record<string, boolean>
interface Channel { name: string; display_name: string; enabled: boolean; ready: boolean; requirements: string[] }
interface Alert { alert_id: string; symbol: string; alert_type: string; target_price: number | null; percent_change: number | null; status: string; created_at: string; triggered_price?: number }
interface Notif { id: string; type: string; title: string; message: string; channel: string; status: string; sent_at: string; error?: string }

const LABELS: Record<string, string> = {
  telegram_enabled: 'Kirim ke Telegram',
  discord_enabled: 'Kirim ke Discord',
  browser_notifications_enabled: 'Notifikasi di browser',
  signal_notifications: 'Notifikasi sinyal baru',
  price_alerts: 'Aktifkan price alert',
}

const fail = (e: unknown) => toast({ title: 'Gagal', description: (e as Error).message, variant: 'destructive' })

export function SettingsPage() {
  const qc = useQueryClient()
  const settings = useApi<Settings>('/api/notifications/settings', 0)
  const channels = useApi<Channel[]>('/api/notifications/channels', 0)
  const alerts = useApi<Alert[]>('/api/notifications/price-alerts', 30000)
  const history = useApi<Notif[]>('/api/notifications/history?limit=20', 30000)
  const health = useApi<any>('/health', 30000)
  const [form, setForm] = useState({ symbol: '', alert_type: 'above', value: '' })

  const refresh = () => qc.invalidateQueries({ predicate: (q) => String(q.queryKey[0]).startsWith('/api/notifications') })

  const toggle = async (key: string) => {
    try {
      await postApi('/api/notifications/settings', { ...settings.data, [key]: !settings.data![key] })
      refresh()
    } catch (e) { fail(e) }
  }
  const test = async (channel: string) => {
    try {
      await postApi('/api/notifications/test', { channel })
      toast({ title: `Tes ${channel} terkirim` })
      refresh()
    } catch (e) { fail(e) }
  }
  const addAlert = async (e: React.FormEvent) => {
    e.preventDefault()
    const v = parseFloat(form.value)
    try {
      await postApi('/api/notifications/price-alerts', {
        symbol: form.symbol.trim(), alert_type: form.alert_type,
        ...(form.alert_type === 'percent_change' ? { percent_change: v } : { target_price: v }),
      })
      setForm({ ...form, symbol: '', value: '' })
      refresh()
    } catch (e) { fail(e) }
  }
  const delAlert = async (id: string) => {
    try { await sendApi(`/api/notifications/price-alerts/${id}`, 'DELETE'); refresh() } catch (e) { fail(e) }
  }

  const md = health.data?.services?.market_data

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Notifikasi, price alert, dan status sistem.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Notifikasi</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <ApiState isLoading={settings.isLoading} error={settings.error} />
            {settings.data && Object.keys(LABELS).map((k) => (
              <label key={k} className="flex items-center justify-between gap-4 text-sm">
                <span>{LABELS[k]}</span>
                <input type="checkbox" className="h-4 w-4" checked={!!settings.data![k]} onChange={() => toggle(k)} />
              </label>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Channel</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            {channels.data?.map((c) => (
              <div key={c.name} className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="font-medium">{c.display_name}</span>{' '}
                  <Badge variant={c.ready ? 'default' : 'secondary'}>{c.ready ? 'siap' : 'belum dikonfigurasi'}</Badge>
                  {!c.ready && <div className="text-xs text-muted-foreground">Set env: {c.requirements.join(', ')}</div>}
                </div>
                <Button size="sm" variant="outline" disabled={!c.ready} onClick={() => test(c.name)}>Kirim tes</Button>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Price alert</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={addAlert} className="flex flex-wrap gap-2 text-sm">
              <Input className="w-32" placeholder="BBCA.JK" value={form.symbol} required aria-label="Simbol"
                     onChange={(e) => setForm({ ...form, symbol: e.target.value })} />
              <select className="rounded-md border bg-background px-2" value={form.alert_type} aria-label="Jenis alert"
                      onChange={(e) => setForm({ ...form, alert_type: e.target.value })}>
                <option value="above">Harga ≥</option>
                <option value="below">Harga ≤</option>
                <option value="percent_change">|Perubahan| ≥ %</option>
              </select>
              <Input className="w-28" type="number" step="any" min="0" placeholder="Nilai" value={form.value} required aria-label="Nilai"
                     onChange={(e) => setForm({ ...form, value: e.target.value })} />
              <Button size="sm" type="submit">Tambah</Button>
            </form>
            {alerts.data?.length === 0 && <p className="text-sm text-muted-foreground">Belum ada alert.</p>}
            <ul className="space-y-2 text-sm">
              {alerts.data?.map((a) => (
                <li key={a.alert_id} className="flex items-center justify-between gap-2 border-t pt-2">
                  <span>
                    <b>{a.symbol}</b> {a.alert_type === 'percent_change' ? `|Δ| ≥ ${a.percent_change}%` : `${a.alert_type === 'above' ? '≥' : '≤'} ${a.target_price}`}{' '}
                    <Badge variant={a.status === 'active' ? 'outline' : 'default'}>{a.status}</Badge>
                  </span>
                  <Button size="sm" variant="ghost" onClick={() => delAlert(a.alert_id)} aria-label={`Hapus alert ${a.symbol}`}>Hapus</Button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Status sistem</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <ApiState isLoading={health.isLoading} error={health.error} />
            {health.data && (
              <>
                <div>Status: <Badge variant={health.data.status === 'healthy' ? 'default' : 'secondary'}>{health.data.status}</Badge></div>
                <div>Simbol terpantau: {md?.symbols ?? 0}</div>
                <div>Refresh data terakhir: {md?.last_refresh ? formatDateTime(md.last_refresh) : '–'}</div>
                {md?.last_error && <div className="text-red-500">Error terakhir: {md.last_error}</div>}
                <div>Signal generator: {health.data.services?.signals}</div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Riwayat notifikasi</CardTitle></CardHeader>
        <CardContent>
          {history.data?.length === 0 && <p className="text-sm text-muted-foreground">Belum ada notifikasi.</p>}
          <ul className="space-y-2 text-sm">
            {history.data?.map((n) => (
              <li key={n.id} className="border-t pt-2">
                <div className="flex flex-wrap items-center gap-2">
                  <b>{n.title}</b>
                  <Badge variant="outline">{n.channel}</Badge>
                  <Badge variant={n.status === 'sent' ? 'default' : 'destructive'}>{n.status}</Badge>
                  <span className="text-xs text-muted-foreground">{formatDateTime(n.sent_at)}</span>
                </div>
                <div className="text-muted-foreground">{n.message}{n.error ? ` — ${n.error}` : ''}</div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
