import { copyFileSync, existsSync, mkdirSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

const sourceDir = 'gif'
const targetDir = 'public'

if (!existsSync(sourceDir)) {
  process.exit(0)
}

mkdirSync(targetDir, { recursive: true })

for (const name of readdirSync(sourceDir)) {
  if (name.toLowerCase().endsWith('.gif')) {
    copyFileSync(join(sourceDir, name), join(targetDir, name))
  }
}
