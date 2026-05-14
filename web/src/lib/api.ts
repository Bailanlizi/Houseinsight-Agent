/** REST / WS 基址与请求封装（与 Vite 代理或 VITE_API_BASE 配合） */

export function apiBase(): string {
  const b = import.meta.env.VITE_API_BASE as string | undefined
  return b?.replace(/\/$/, '') ?? ''
}

export function wsUrl(sessionId: string): string {
  const api = import.meta.env.VITE_API_BASE as string | undefined
  if (api) {
    const u = new URL(api)
    u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:'
    u.pathname = `/sessions/${sessionId}/ws`
    u.search = ''
    u.hash = ''
    return u.toString()
  }
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/sessions/${sessionId}/ws`
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const base = apiBase()
  const url = base ? `${base}${path}` : path
  return fetch(url, init)
}
