// 把网络到达的文字按帧平滑“打印”出来。
// 原因：DeepSeek 的响应经常以突发 chunk 的形式到达（一次几十个字），
// 直接 append 会出现“等几秒 → 一瞬间整段出现”的观感；这里先把增量放进缓冲，
// 每帧按缓冲量自适应吐出，既保留逐字感，又不会让长回答拖得太慢。

export function createTypewriter(
  write,
  { interval = 32, minCharsPerTick = 2, maxCharsPerTick = 24, chunkDivisor = 10 } = {}
) {
  let buffer = ''
  let timer = null
  let waiters = []

  const settle = () => {
    const pending = waiters
    waiters = []
    pending.forEach((resolve) => resolve())
  }

  const tick = () => {
    timer = null
    if (!buffer.length) {
      settle()
      return
    }
    const pending = buffer.length
    const count = Math.max(
      minCharsPerTick,
      Math.min(maxCharsPerTick, Math.ceil(pending / Math.max(chunkDivisor, 1)))
    )
    write(buffer.slice(0, count))
    buffer = buffer.slice(count)
    if (buffer.length) {
      timer = setTimeout(tick, interval)
    } else {
      settle()
    }
  }

  return {
    push(text) {
      if (!text) return
      buffer += text
      if (timer === null) timer = setTimeout(tick, interval)
    },
    reset() {
      if (timer !== null) {
        clearTimeout(timer)
        timer = null
      }
      buffer = ''
      settle()
    },
    flush() {
      if (timer !== null) {
        clearTimeout(timer)
        timer = null
      }
      if (buffer.length) {
        write(buffer)
        buffer = ''
      }
      settle()
    },
    drained() {
      if (!buffer.length && timer === null) return Promise.resolve()
      return new Promise((resolve) => waiters.push(resolve))
    }
  }
}
