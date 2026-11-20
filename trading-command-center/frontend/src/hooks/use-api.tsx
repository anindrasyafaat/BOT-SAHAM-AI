import { useQuery } from 'react-query'

// Semua route backend membungkus hasil dalam { status, data }; hook ini mengembalikan `data`.
export function useApi<T = any>(path: string, refetchInterval = 60000) {
  return useQuery<T>(
    [path],
    async () => {
      const res = await fetch(path)
      if (!res.ok) throw new Error(`${res.status} ${path}`)
      return (await res.json()).data
    },
    { refetchInterval }
  )
}

export async function postApi(path: string) {
  const res = await fetch(path, { method: 'POST' })
  if (!res.ok) throw new Error(`${res.status} ${path}`)
  return res.json()
}

export function ApiState({ isLoading, error }: { isLoading: boolean; error: unknown }) {
  if (isLoading) return <p className="py-8 text-center text-muted-foreground">Memuat…</p>
  if (error) return <p className="py-8 text-center text-red-500">Gagal memuat: {String((error as Error).message ?? error)}</p>
  return null
}
