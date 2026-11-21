import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/hooks/use-auth'
import { Activity } from 'lucide-react'

export function LoginPage() {
  const { login } = useAuth()
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(password)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Activity className="h-6 w-6 text-primary" /> Trading Command Center</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-3">
            <label htmlFor="pw" className="text-sm">Password</label>
            <Input id="pw" type="password" autoComplete="current-password" required value={password}
                   onChange={(e) => setPassword(e.target.value)} />
            {error && <p role="alert" className="text-sm text-red-500">{error}</p>}
            <Button type="submit" className="w-full" disabled={busy}>{busy ? 'Masuk…' : 'Masuk'}</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
