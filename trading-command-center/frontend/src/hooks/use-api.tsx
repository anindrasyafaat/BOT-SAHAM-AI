import { useQuery } from 'react-query'

const TOKEN_KEY = 'tcc-token'

export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}

export function setToken(token: string | null) {
  try { token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY) } catch { /* mode privat */ }
}

// Semua request API lewat sini: token ikut otomatis; 401 -> kembali ke layar login.
export async function apiFetch(path: string, init: RequestInit = {}) {
  const token = getToken()
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(path, { ...init, headers })
  if (res.status === 401 && !path.startsWith('/api/auth')) {
    setToken(null)
    window.dispatchEvent(new Event('tcc-unauthorized'))
  }
  return res
}

// Semua route backend membungkus hasil dalam { status, data }; hook ini mengembalikan `data`.
export function useApi<T = any>(path: string, refetchInterval = 60000) {
  return useQuery<T>(
    [path],
    async () => {
      const res = await apiFetch(path)
      if (!res.ok) throw new Error(`${res.status} ${path}`)
      return (await res.json()).data
    },
    { refetchInterval }
  )
}

// Kirim JSON; lempar Error berisi pesan `detail` dari FastAPI agar bisa ditampilkan ke pengguna.
export async function sendApi(path: string, method: 'POST' | 'DELETE' = 'POST', body?: unknown) {
  const res = await apiFetch(path, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const json = await res.json().catch(() => ({}))
  if (!res.ok) {
    const d = json.detail
    throw new Error(typeof d === 'string' ? d : Array.isArray(d) ? d.map((x: any) => x.msg).join('; ') : `${res.status} ${path}`)
  }
  return json
}

export const postApi = (path: string, body?: unknown) => sendApi(path, 'POST', body)

export function ApiState({ isLoading, error }: { isLoading: boolean; error: unknown }) {
  if (isLoading) return <p className="py-8 text-center text-muted-foreground">Memuat…</p>
  if (error) return <p className="py-8 text-center text-red-500">Gagal memuat: {String((error as Error).message ?? error)}</p>
  return null
}
