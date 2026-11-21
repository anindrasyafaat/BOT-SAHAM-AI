import { useState } from 'react'
import { useQueryClient } from 'react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useApi, postApi, ApiState } from '@/hooks/use-api'
import { toast } from '@/hooks/use-toast'
import { cn, formatDateTime } from '@/lib/utils'
import { Sparkles } from 'lucide-react'

type Kind = 'peluang' | 'strategi' | 'portofolio' | 'bebas'
interface Evidence { bobot: number; teks: string; sumber: string }
interface Alt {
  operator: string; pola_pikir: string; judul: string; alasan: string; skor: number; skor_bukti: number
  rekam_jejak_operator: number | null; risiko: string; pemicu: string; titik_batal: string
  aksi: null | { tipe: 'buy' | 'sell' | 'toggle_strategy'; simbol?: string; strategi?: string; stop_loss?: number | null; take_profit?: number | null; porsi?: number }
}
interface Pattern { kondisi: Record<string, string>; n: number; win_rate: number; expectancy: number; wilson_bawah: number; wilson_atas: number }
interface Framework {
  jenis: string; masalah: string; ditafsirkan_sebagai?: string; fakta: Record<string, any>
  pengalaman: { analog: null | Record<string, any>; pola: { berhasil: Pattern[]; gagal: Pattern[] }; total_pengalaman: number }
  hipotesis: { bukti: Evidence[]; ringkasan: null | { pro: number; kontra: number; net: number; bias: string; kesepakatan_bukti: number; jumlah_bukti: number } }
  alternatif: Alt[]
  keputusan: { rekomendasi: Alt; cadangan: Alt; checklist: string[]; pre_mortem: string[] }
  rencana_belajar: string[]
  preflight?: Preflight
  kontrol_kualitas?: Review
}
interface QCheck { id: string; nama: string; status: 'lulus' | 'peringatan' | 'gagal'; detail: string; perbaikan: string | null }
interface Preflight { checks: QCheck[]; verdict: string; blocking: boolean; jenis?: string; simbol?: string | null }
interface Review {
  checks: QCheck[]; verdict: string; keyakinan: number; stabilitas: number | null; pembalik: string[]; advokat_setan: string[]
  ukuran_posisi: null | { jumlah_maks: number; risiko_idr: number; nilai_idr: number; dibatasi_kas: boolean; risiko_per_trade: number }
  keputusan_final: Alt & { alasan_kontrol?: string }; diturunkan: boolean
}
interface Gen { id: number; jenis: string; simbol: string | null; masalah: string; narasi: string; sumber_narasi: string; dipilih: string | null; hasil: string | null; sumber_hasil: string | null; catatan: string | null; dibuat: string; kerangka?: Framework }

const KINDS: { v: Kind; label: string; hint: string }[] = [
  { v: 'peluang', label: 'Peluang aset', hint: 'Masuk, tunggu, atau hindari sebuah simbol?' },
  { v: 'strategi', label: 'Masalah strategi', hint: 'Strategi merugi: apa alternatifnya?' },
  { v: 'portofolio', label: 'Risiko portofolio', hint: 'Drawdown, konsentrasi, posisi tanpa SL' },
  { v: 'bebas', label: 'Tulis bebas', hint: 'Sebut ticker dengan HURUF BESAR, mis. "BBCA turun terus, perlu cut loss?"' },
]
const fail = (e: unknown) => toast({ title: 'Gagal', description: (e as Error).message, variant: 'destructive' })
const ICON = { lulus: '✓', peringatan: '!', gagal: '✗' } as const
const TONE = { lulus: 'text-green-500', peringatan: 'text-yellow-500', gagal: 'text-red-500' } as const

function CheckList({ title, checks }: { title: string; checks: QCheck[] }) {
  return (
    <div>
      <div className="mb-1 text-sm font-medium">{title}</div>
      <ul className="space-y-1 text-sm" data-testid="qc-list">
        {checks.map((c) => (
          <li key={c.id} className="flex gap-2">
            <span className={cn('w-4 shrink-0 font-bold', TONE[c.status])} aria-label={c.status}>{ICON[c.status]}</span>
            <span><b>{c.nama}</b> — {c.detail}{c.perbaikan && <span className="text-muted-foreground"> · {c.perbaikan}</span>}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

const fmtKondisi = (k: Record<string, string>) => Object.entries(k).map(([a, b]) => `${a}=${b}`).join(' · ')

function PatternList({ title, items, good }: { title: string; items: Pattern[]; good: boolean }) {
  return (
    <div>
      <div className={cn('mb-1 text-sm font-medium', good ? 'text-green-500' : 'text-red-500')}>{title}</div>
      {items.length === 0 ? <p className="text-sm text-muted-foreground">Belum ada (butuh ≥ 8 sinyal tertutup per kondisi).</p> : (
        <ul className="space-y-1 text-sm">
          {items.map((p, i) => (
            <li key={i} className="flex flex-wrap justify-between gap-2 border-t pt-1">
              <span>{fmtKondisi(p.kondisi)}</span>
              <span className="tabular-nums text-muted-foreground">WR {p.win_rate}% · exp {p.expectancy}% · n={p.n} · Wilson {p.wilson_bawah}–{p.wilson_atas}%</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function GeneratePage() {
  const qc = useQueryClient()
  const [kind, setKind] = useState<Kind>('peluang')
  const [symbol, setSymbol] = useState('')
  const [strategy, setStrategy] = useState('')
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<Gen | null>(null)
  const [pre, setPre] = useState<Preflight | null>(null)
  const strategies = useApi<{ strategy_name: string }[]>('/api/signals/strategies', 0)
  const patterns = useApi<{ berhasil: Pattern[]; gagal: Pattern[]; total_pengalaman: number }>('/api/insight/patterns', 300000)
  const history = useApi<Gen[]>('/api/insight/history?limit=20', 60000)

  const refresh = () => qc.invalidateQueries({ predicate: (q) => String(q.queryKey[0]).startsWith('/api/insight') })

  const body = () => ({
    jenis: kind, simbol: kind === 'peluang' ? symbol.trim() : undefined,
    strategi: kind === 'strategi' ? strategy : undefined, teks: text,
  })

  const run = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      const r = await postApi('/api/insight/generate', body())
      setResult(r.data)
      setPre(null)
      refresh()
    } catch (err) {
      const d = (err as Error & { detail?: any }).detail
      if (d?.preflight) {  // gerbang 1 memblokir: tampilkan daftar perbaikan, bukan sekadar error
        setPre(d.preflight)
        setResult(null)
        toast({ title: 'Generate diblokir pemeriksaan kualitas', description: 'Lihat daftar perbaikan di bawah.', variant: 'destructive' })
      } else fail(err)
    } finally { setBusy(false) }
  }

  const precheck = async () => {
    setBusy(true)
    try { setPre((await postApi('/api/insight/preflight', body())).data) } catch (err) { fail(err) } finally { setBusy(false) }
  }

  const choose = async (g: Gen, op: string) => {
    try {
      await postApi(`/api/insight/${g.id}/choose`, { operator: op })
      setResult((r) => (r && r.id === g.id ? { ...r, dipilih: op } : r))
      toast({ title: `Dipilih: ${op}`, description: 'Hasilnya akan menjadi pengalaman untuk keputusan berikutnya.' })
      refresh()
    } catch (err) { fail(err) }
  }

  const execute = async (a: Alt) => {
    const x = a.aksi!
    try {
      if (x.tipe === 'buy') {
        const qty = window.prompt(`Jumlah beli ${x.simbol}${x.simbol?.endsWith('.JK') ? ' (lembar, kelipatan 100)' : ''}${x.porsi ? ` — saran porsi ${Math.round(x.porsi * 100)}% dari rencana` : ''}:`)
        if (!qty) return
        await postApi('/api/portfolio/buy', { symbol: x.simbol, quantity: parseFloat(qty), stop_loss: x.stop_loss ?? undefined, take_profit: x.take_profit ?? undefined })
      } else if (x.tipe === 'sell') {
        await postApi('/api/portfolio/close-position', { symbol: x.simbol })
      } else {
        await postApi(`/api/signals/strategies/${encodeURIComponent(x.strategi!)}/toggle`)
      }
      toast({ title: 'Aksi dijalankan (paper trading)' })
      qc.invalidateQueries({ predicate: (q) => /\/api\/(portfolio|signals)/.test(String(q.queryKey[0])) })
    } catch (err) { fail(err) }
  }

  const outcome = async (id: number, hasil: 'berhasil' | 'gagal') => {
    try { await postApi(`/api/insight/${id}/outcome`, { hasil }); refresh() } catch (err) { fail(err) }
  }

  const fw = result?.kerangka
  const s = fw?.hipotesis.ringkasan

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Sparkles className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Generate</h1>
          <p className="text-muted-foreground">Kerangka berpikir dari data & pengalaman Anda, lalu beberapa alternatif solusi yang dinilai bukti.</p>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={run} className="space-y-3">
            <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Jenis kasus">
              {KINDS.map((k) => (
                <Button key={k.v} type="button" size="sm" role="radio" aria-checked={kind === k.v}
                        variant={kind === k.v ? 'default' : 'outline'} onClick={() => setKind(k.v)}>{k.label}</Button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">{KINDS.find((k) => k.v === kind)!.hint}</p>
            <div className="flex flex-wrap gap-2">
              {kind === 'peluang' && <Input className="w-40" placeholder="BBCA.JK / AAPL / BTC" value={symbol} required aria-label="Simbol" onChange={(e) => setSymbol(e.target.value)} />}
              {kind === 'strategi' && (
                <select className="rounded-md border bg-background px-3 text-sm" value={strategy} required aria-label="Strategi" onChange={(e) => setStrategy(e.target.value)}>
                  <option value="">Pilih strategi…</option>
                  {strategies.data?.map((x) => <option key={x.strategy_name} value={x.strategy_name}>{x.strategy_name}</option>)}
                </select>
              )}
              <Input className="min-w-[16rem] flex-1" maxLength={1000} required={kind === 'bebas'} value={text} aria-label="Masalah"
                     placeholder={kind === 'bebas' ? 'Ceritakan masalahnya…' : 'Masalah (opsional)'} onChange={(e) => setText(e.target.value)} />
              <Button type="button" variant="outline" disabled={busy} onClick={precheck}>Cek dulu</Button>
              <Button type="submit" disabled={busy}>{busy ? 'Berpikir…' : 'Generate'}</Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {pre && (
        <Card data-testid="preflight-panel">
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2">
              Pemeriksaan sebelum generate
              <Badge variant={pre.blocking ? 'destructive' : pre.verdict === 'lulus' ? 'default' : 'secondary'}>{pre.verdict}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent><CheckList title="Kelayakan data & pengalaman" checks={pre.checks} /></CardContent>
        </Card>
      )}

      {result && fw && (
        <div className="space-y-4" data-testid="generate-result">
          {fw.kontrol_kualitas && (() => {
            const q = fw.kontrol_kualitas!
            return (
              <Card className={cn(q.diturunkan && 'border-yellow-500')} data-testid="qc-panel">
                <CardHeader>
                  <CardTitle className="flex flex-wrap items-center gap-2">
                    0. Pemeriksaan kualitas
                    <Badge variant={q.keyakinan >= 70 ? 'default' : q.keyakinan >= 35 ? 'secondary' : 'destructive'}>keyakinan {q.keyakinan}/100</Badge>
                    {q.stabilitas != null && <Badge variant="outline">stabilitas {q.stabilitas}%</Badge>}
                    <Badge variant="outline">{q.verdict}</Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-lg border p-3">
                    <div className="text-sm text-muted-foreground">Keputusan akhir setelah kontrol</div>
                    <div className="text-lg font-semibold">{q.keputusan_final.judul}</div>
                    {q.diturunkan && (
                      <p className="text-sm text-yellow-600">
                        Diturunkan dari “{fw.keputusan.rekomendasi.judul}” karena: {q.keputusan_final.alasan_kontrol}
                      </p>
                    )}
                    {q.ukuran_posisi && (
                      <p className="mt-1 text-sm">
                        Ukuran maksimal: <b>{q.ukuran_posisi.jumlah_maks.toLocaleString('id-ID')}</b> unit · rugi maks saat kena SL ±
                        {' '}{q.ukuran_posisi.risiko_idr.toLocaleString('id-ID')} IDR ({(q.ukuran_posisi.risiko_per_trade * 100).toFixed(1)}% modal)
                        {q.ukuran_posisi.dibatasi_kas && ' · dibatasi kas'}
                      </p>
                    )}
                  </div>
                  <div className="grid gap-4 lg:grid-cols-2">
                    {fw.preflight && <CheckList title="Gerbang 1 · sebelum generate" checks={fw.preflight.checks} />}
                    <CheckList title="Gerbang 2 · sebelum menjawab" checks={q.checks} />
                  </div>
                  <div>
                    <div className="mb-1 text-sm font-medium">Advokat setan — argumen terkuat melawan keputusan ini</div>
                    <ul className="list-inside list-disc text-sm text-muted-foreground">{q.advokat_setan.map((x) => <li key={x}>{x}</li>)}</ul>
                  </div>
                </CardContent>
              </Card>
            )
          })()}
          <Card>
            <CardHeader>
              <CardTitle className="flex flex-wrap items-center gap-2">
                1. Masalah <Badge variant="outline">{fw.jenis}{fw.ditafsirkan_sebagai ? ` (dari teks bebas)` : ''}</Badge>
                <Badge variant="secondary">narasi: {result.sumber_narasi}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="font-medium">{fw.masalah}</p>
              <p className="text-sm">{result.narasi}</p>
            </CardContent>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>2. Fakta</CardTitle></CardHeader>
              <CardContent>
                <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded bg-muted p-3 text-xs">{JSON.stringify(fw.fakta, null, 2)}</pre>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>3. Pengalaman</CardTitle></CardHeader>
              <CardContent className="space-y-3 text-sm">
                {fw.pengalaman.analog ? (
                  <div className="rounded border p-3">
                    <div className="font-medium">Analog historis ({fmtKondisi(fw.pengalaman.analog.kunci)})</div>
                    <div className="text-muted-foreground">
                      {fw.pengalaman.analog.n} kejadian di {fw.pengalaman.analog.simbol} simbol → {fw.pengalaman.analog.horizon_hari} hari kemudian naik {fw.pengalaman.analog.peluang_naik}%,
                      median {fw.pengalaman.analog.median_return}%, rentang {fw.pengalaman.analog.p10}% s/d {fw.pengalaman.analog.p90}%
                    </div>
                  </div>
                ) : <p className="text-muted-foreground">Analog historis tidak dipakai untuk jenis kasus ini.</p>}
                <PatternList title="Pola berhasil yang cocok" items={fw.pengalaman.pola.berhasil} good />
                <PatternList title="Pola gagal yang cocok" items={fw.pengalaman.pola.gagal} good={false} />
                <p className="text-xs text-muted-foreground">Total pengalaman sinyal tertutup: {fw.pengalaman.total_pengalaman}</p>
              </CardContent>
            </Card>
          </div>

          {s && (
            <Card>
              <CardHeader>
                <CardTitle>4. Hipotesis: condong <span className={cn(s.bias === 'bullish' ? 'text-green-500' : s.bias === 'bearish' ? 'text-red-500' : '')}>{s.bias}</span></CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-3 text-sm text-muted-foreground">Pro {s.pro} · Kontra {s.kontra} · Kesepakatan bukti {s.kesepakatan_bukti}% · {s.jumlah_bukti} bukti</div>
                <ul className="space-y-1 text-sm">
                  {fw.hipotesis.bukti.map((b, i) => (
                    <li key={i} className="flex gap-2">
                      <span className={cn('w-14 shrink-0 text-right tabular-nums', b.bobot >= 0 ? 'text-green-500' : 'text-red-500')}>{b.bobot > 0 ? '+' : ''}{b.bobot}</span>
                      <span>{b.teks} <span className="text-muted-foreground">({b.sumber})</span></span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader><CardTitle>5. Alternatif solusi (7 pola pikir, diurutkan skor)</CardTitle></CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              {fw.alternatif.map((a) => (
                <div key={a.operator} className={cn('rounded-lg border p-3 text-sm', result.dipilih === a.operator && 'border-primary ring-1 ring-primary')}>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <Badge variant="outline">{a.operator}</Badge> <span className="text-xs text-muted-foreground">{a.pola_pikir}</span>
                      <div className="mt-1 font-semibold">{a.judul}</div>
                    </div>
                    <div className="text-right text-2xl font-bold tabular-nums">{a.skor}</div>
                  </div>
                  <div className="my-2 h-2 rounded bg-muted"><div className="h-2 rounded bg-primary" style={{ width: `${a.skor}%` }} /></div>
                  <p>{a.alasan}</p>
                  <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-2 text-xs text-muted-foreground">
                    <dt>Pemicu</dt><dd>{a.pemicu}</dd>
                    <dt>Risiko</dt><dd>{a.risiko}</dd>
                    <dt>Batal bila</dt><dd>{a.titik_batal}</dd>
                    <dt>Skor bukti</dt><dd>{a.skor_bukti}{a.rekam_jejak_operator != null ? ` · rekam jejak operator ${a.rekam_jejak_operator}%` : ''}</dd>
                  </dl>
                  <div className="mt-3 flex gap-2">
                    <Button size="sm" variant={result.dipilih === a.operator ? 'default' : 'outline'} onClick={() => choose(result, a.operator)}>
                      {result.dipilih === a.operator ? 'Dipilih' : 'Pilih'}
                    </Button>
                    {a.aksi && <Button size="sm" variant="secondary" onClick={() => execute(a)}>Jalankan</Button>}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>6. Keputusan & pre-mortem</CardTitle></CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>Rekomendasi: <b>{fw.keputusan.rekomendasi.judul}</b> · cadangan: {fw.keputusan.cadangan.judul}</div>
                <div>
                  <div className="font-medium">Checklist sebelum eksekusi</div>
                  <ul className="list-inside list-disc text-muted-foreground">{fw.keputusan.checklist.map((c) => <li key={c}>{c}</li>)}</ul>
                </div>
                <div>
                  <div className="font-medium">Kalau keputusan ini gagal, kemungkinan karena…</div>
                  <ul className="list-inside list-disc text-muted-foreground">{fw.keputusan.pre_mortem.map((c) => <li key={c}>{c}</li>)}</ul>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>7. Rencana belajar</CardTitle></CardHeader>
              <CardContent>
                <ul className="list-inside list-disc text-sm text-muted-foreground">{fw.rencana_belajar.map((c) => <li key={c}>{c}</li>)}</ul>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Pola dari seluruh pengalaman</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <ApiState isLoading={patterns.isLoading} error={patterns.error} />
            {patterns.data && (
              <>
                <p className="text-xs text-muted-foreground">{patterns.data.total_pengalaman} sinyal tertutup menjadi pengalaman.</p>
                <PatternList title="Berhasil" items={patterns.data.berhasil} good />
                <PatternList title="Gagal" items={patterns.data.gagal} good={false} />
              </>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Riwayat keputusan</CardTitle></CardHeader>
          <CardContent>
            {history.data?.length === 0 && <p className="text-sm text-muted-foreground">Belum ada.</p>}
            <ul className="space-y-2 text-sm">
              {history.data?.map((g) => (
                <li key={g.id} className="border-t pt-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{g.jenis}</Badge>{g.simbol && <b>{g.simbol}</b>}
                    <span className="text-xs text-muted-foreground">{formatDateTime(g.dibuat)}</span>
                    {g.dipilih && <Badge>{g.dipilih}</Badge>}
                    {g.hasil && <Badge variant={g.hasil === 'berhasil' ? 'default' : 'destructive'}>{g.hasil} ({g.sumber_hasil})</Badge>}
                  </div>
                  <div className="text-muted-foreground">{g.masalah}</div>
                  {g.dipilih && !g.hasil && (
                    <div className="mt-1 flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => outcome(g.id, 'berhasil')}>Berhasil</Button>
                      <Button size="sm" variant="outline" onClick={() => outcome(g.id, 'gagal')}>Gagal</Button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
