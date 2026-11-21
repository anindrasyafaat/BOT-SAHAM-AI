import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useApi, ApiState } from '@/hooks/use-api'
import { cn, formatDateTime } from '@/lib/utils'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, ReferenceLine } from 'recharts'

interface News {
  id: string
  title: string
  summary: string
  source: string
  category: string
  published_at: string
  symbol?: string
  sentiment: 'positive' | 'negative' | 'neutral'
  impact: string
  url: string
}

const SENT = { positive: 'bg-green-600', negative: 'bg-red-600', neutral: 'bg-gray-500' }

export function NewsPage() {
  const [highOnly, setHighOnly] = useState(false)
  const { data, isLoading, error } = useApi<News[]>(highOnly ? '/api/news/high-impact' : '/api/news/latest?limit=50', 300000)
  const { data: sent } = useApi<{ summary: { overall_sentiment: number; sentiment_label: string; total_news: number }; timeline: { date: string; sentiment_score: number }[] }>('/api/news/sentiment?days=14', 600000)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Market News</h1>
          <p className="text-muted-foreground">Berita pasar dengan skor sentimen dan dampak.</p>
        </div>
        <Button size="sm" variant={highOnly ? 'default' : 'outline'} onClick={() => setHighOnly(!highOnly)} aria-pressed={highOnly}>
          Hanya high impact
        </Button>
      </div>

      {sent && (
        <Card>
          <CardHeader>
            <CardTitle>
              Sentimen 14 hari: <span className={cn(sent.summary.overall_sentiment >= 0 ? 'text-green-500' : 'text-red-500')}>{sent.summary.sentiment_label} ({sent.summary.overall_sentiment.toFixed(2)})</span>
              <span className="ml-2 text-sm font-normal text-muted-foreground">{sent.summary.total_news} berita</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={sent.timeline.map((t) => ({ ...t, date: t.date.slice(5, 10) }))}>
                <XAxis dataKey="date" fontSize={12} />
                <YAxis domain={[-1, 1]} fontSize={12} />
                <Tooltip />
                <ReferenceLine y={0} stroke="#888" />
                <Area type="monotone" dataKey="sentiment_score" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      <ApiState isLoading={isLoading} error={error} />
      <div className="grid gap-4 md:grid-cols-2">
        {data?.map((n) => (
          <Card key={n.id}>
            <CardContent className="space-y-2 pt-6">
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <Badge className={cn(SENT[n.sentiment] ?? 'bg-gray-500', 'text-white')}>{n.sentiment}</Badge>
                <Badge variant={n.impact === 'high' ? 'destructive' : 'secondary'}>{n.impact} impact</Badge>
                <Badge variant="outline">{n.category}</Badge>
                {n.symbol && <Badge variant="outline">{n.symbol}</Badge>}
              </div>
              <a href={n.url} target="_blank" rel="noreferrer" className="block font-semibold hover:underline">{n.title}</a>
              <p className="text-sm text-muted-foreground">{n.summary}</p>
              <div className="text-xs text-muted-foreground">{n.source} · {formatDateTime(n.published_at)}</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
