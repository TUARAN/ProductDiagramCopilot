import mermaid from 'mermaid'

let initialized = false

export function ensureMermaid() {
  if (initialized) return
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    theme: 'default',
    suppressErrorRendering: true,
  })
  initialized = true
}

export async function renderMermaid(id: string, code: string): Promise<string> {
  ensureMermaid()
  // Validate first so we throw instead of rendering Mermaid's error SVG.
  // Mermaid v11 may otherwise return an error SVG containing "Syntax error in text".
  await mermaid.parse(code)
  const { svg } = await mermaid.render(id, code)
  return svg
}
