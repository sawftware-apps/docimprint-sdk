#!/usr/bin/env node
import { createRequire } from 'node:module'
import { spawn } from 'node:child_process'
import path from 'node:path'

const apiKey = process.env.DOCIMPRINT_API_KEY

if (!apiKey) {
  console.error(
    '[docimprint-mcp] Missing DOCIMPRINT_API_KEY environment variable.\n' +
      'Set it to your DocImprint API key (dr_live_...) and try again.'
  )
  process.exit(1)
}

const require = createRequire(__filename)

let mcpRemoteBin: string
try {
  const mcpRemotePkgJsonPath = require.resolve('mcp-remote/package.json')
  const mcpRemotePkg = require(mcpRemotePkgJsonPath) as {
    bin?: Record<string, string> | string
  }
  const binRelativePath =
    typeof mcpRemotePkg.bin === 'string'
      ? mcpRemotePkg.bin
      : mcpRemotePkg.bin?.['mcp-remote']
  if (!binRelativePath) {
    throw new Error('mcp-remote package.json has no "mcp-remote" bin entry')
  }
  mcpRemoteBin = path.join(path.dirname(mcpRemotePkgJsonPath), binRelativePath)
} catch (err) {
  console.error(
    '[docimprint-mcp] Could not resolve the "mcp-remote" package. ' +
      'Make sure it is installed as a dependency of docimprint.\n' +
      String(err)
  )
  process.exit(1)
}

const child = spawn(
  process.execPath,
  [
    mcpRemoteBin,
    'https://api.docimprint.com/mcp',
    '--header',
    `Authorization: Bearer ${apiKey}`,
  ],
  { stdio: 'inherit', shell: false }
)

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal)
    return
  }
  process.exit(code ?? 1)
})

child.on('error', (err) => {
  console.error('[docimprint-mcp] Failed to start mcp-remote process:', err)
  process.exit(1)
})
