// 解析后端 SSE 事件流。
// 兼容两类帧：新协议 {type: "answer_delta", text} 与旧协议 {token} / {error} / {done}。
// 使用跨 chunk 行缓冲，避免 TCP 分片导致 JSON 解析失败。

export function normalizeEvent(payload) {
  if (!payload || typeof payload !== 'object') return null
  if (typeof payload.type === 'string') return payload
  if (typeof payload.token === 'string') return { type: 'answer_delta', text: payload.token }
  if (payload.error) return { type: 'error', code: 'ai_error', message: String(payload.error) }
  if (payload.done) return { type: 'done', saved: Boolean(payload.saved) }
  return null
}

function parseLine(line) {
  if (!line.startsWith('data:')) return null
  const raw = line.slice(5).trim()
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export async function readEventStream(response, onEvent) {
  if (!response.ok || !response.body) {
    let detail = ''
    try {
      const payload = await response.clone().json()
      detail = payload.error || payload.message || ''
    } catch {
      // 非 JSON 错误体（如网关错误页），忽略
    }
    throw new Error(detail || `请求失败（HTTP ${response.status}）`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const handleLine = (line) => {
    const payload = parseLine(line)
    if (!payload) return
    const event = normalizeEvent(payload)
    if (event) onEvent(event)
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) handleLine(line)
  }

  buffer += decoder.decode()
  if (buffer) handleLine(buffer)
}

export const TOOL_LABELS = {
  retrieve_knowledge: '正在检索知识库…',
  read_source: '正在读取资料原文…',
  safe_math: '正在核对计算…',
  present_ui: '正在整理卡片…'
}
