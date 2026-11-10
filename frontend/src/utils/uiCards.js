// 智能 UI 卡片的客户端二次校验与辅助函数。
// 服务端已经严格校验；这里再做一次防御，非法卡片直接降级为不渲染，避免页面异常。

export function safeSourceURL(value) {
  if (!value) return undefined
  try {
    const url = new URL(value)
    if (['http:', 'https:'].includes(url.protocol) && !url.username && !url.password) return url.href
  } catch {
    return undefined
  }
  return undefined
}

export function sourceHref(source) {
  return source && source.source ? safeSourceURL(source.source) : undefined
}

export function cardCitations(card) {
  if (!card) return []
  if (card.type === 'source_list') return Array.isArray(card.citations) ? card.citations : []
  if (card.type === 'guide') {
    return (card.steps || []).flatMap((step) => (Array.isArray(step.citations) ? step.citations : []))
  }
  return []
}

const CARD_TYPES = new Set(['source_list', 'guide', 'related_chapters'])

export function validateUI(value, sources = [], chapterIds = new Set()) {
  if (value == null) return { ui: null, errors: [] }
  if (typeof value !== 'object' || value.version !== 1 || !Array.isArray(value.cards)) {
    return { ui: null, errors: ['invalid_envelope'] }
  }
  if (value.cards.length < 1 || value.cards.length > 3) {
    return { ui: null, errors: ['invalid_envelope'] }
  }

  const sourceMap = new Map(sources.map((source) => [source.citation, source]))
  const cards = []
  const errors = []

  value.cards.forEach((card, index) => {
    if (!card || !CARD_TYPES.has(card.type)) {
      errors.push(`card_${index}:invalid_schema`)
      return
    }
    if (card.type === 'source_list') {
      if (!Array.isArray(card.citations) || card.citations.length === 0) {
        errors.push(`card_${index}:invalid_schema`)
        return
      }
      const invalid = card.citations.some((citation) => !sourceMap.has(citation))
      if (invalid) {
        errors.push(`card_${index}:invalid_source`)
        return
      }
    }
    if (card.type === 'guide') {
      const steps = card.steps
      if (!card.title || !Array.isArray(steps) || steps.length === 0) {
        errors.push(`card_${index}:invalid_schema`)
        return
      }
      const invalid = steps.some(
        (step) =>
          !step ||
          !step.title ||
          !step.detail ||
          !Array.isArray(step.citations) ||
          step.citations.some((citation) => !sourceMap.has(citation))
      )
      if (invalid) {
        errors.push(`card_${index}:invalid_schema`)
        return
      }
    }
    if (card.type === 'related_chapters') {
      const ids = card.chapterIds
      if (!Array.isArray(ids) || ids.length === 0 || ids.some((id) => !chapterIds.has(id))) {
        errors.push(`card_${index}:unknown_chapter`)
        return
      }
    }
    cards.push(card)
  })

  if (!cards.length) return { ui: null, errors }
  return { ui: { version: 1, cards }, errors }
}

export function citationsOfSources(sources = []) {
  return sources.map((source) => source.citation)
}
