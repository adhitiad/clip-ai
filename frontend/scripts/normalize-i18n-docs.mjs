import { readFile, writeFile } from 'node:fs/promises'

const targets = ['project.inlang/README.md', 'src/paraglide/README.md']

const rules = [
  [/\bnpx @inlang\/cli\b/g, 'bunx --bun @inlang/cli'],
  [/\bnpx @inlang\/paraglide-js\b/g, 'bunx --bun @inlang/paraglide-js'],
]

await Promise.all(
  targets.map(async (target) => {
    let content
    try {
      content = await readFile(new URL(`../${target}`, import.meta.url), 'utf8')
    } catch {
      return
    }

    let next = content
    for (const [pattern, replacement] of rules)
      next = next.replace(pattern, replacement)

    if (next !== content) {
      await writeFile(new URL(`../${target}`, import.meta.url), next)
      console.log(`[normalize-i18n-docs] ${target}: bun/bunx applied`)
    }
  }),
)
