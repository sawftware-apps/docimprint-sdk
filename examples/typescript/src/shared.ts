/** Shared helpers for DocImprint TypeScript demos. */

import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import chalk from 'chalk'
import { config as loadDotenv } from 'dotenv'
import {
  DocImprintClient,
  DocImprintError,
  type ActionReceipt,
  type ActionReceiptRecord,
  type VerifyReceiptResponse,
} from 'docimprint'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/** examples/typescript */
export const PACKAGE_ROOT = path.resolve(__dirname, '..')
/** examples/ */
export const EXAMPLES_ROOT = path.resolve(PACKAGE_ROOT, '..')
export const FIXTURES_DIR = path.join(EXAMPLES_ROOT, 'fixtures')
export const OUT_DIR = path.join(PACKAGE_ROOT, 'out')

export const DEFAULT_BASE_URL = 'https://api.docimprint.com'
export const VERIFY_TOOL_URL = 'https://docimprint.com/tools/verify-bundle'

export function loadConfig(): { apiKey: string; baseUrl: string } {
  loadDotenv({ path: path.join(PACKAGE_ROOT, '.env') })
  loadDotenv()
  const apiKey = (process.env.DOCIMPRINT_API_KEY ?? '').trim()
  if (!apiKey) {
    console.error(
      chalk.red('error:'),
      'DOCIMPRINT_API_KEY is required (copy .env.example → .env and set your key)',
    )
    process.exit(1)
  }
  const baseUrl =
    (process.env.DOCIMPRINT_BASE_URL ?? DEFAULT_BASE_URL).trim() || DEFAULT_BASE_URL
  return { apiKey, baseUrl: baseUrl.replace(/\/$/, '') }
}

export function createClient(apiKey: string, baseUrl: string): DocImprintClient {
  return new DocImprintClient({ apiKey, baseUrl })
}

export function manifestSha256(payload: Record<string, unknown>): string | undefined {
  if (typeof payload.manifest_sha256 === 'string') return payload.manifest_sha256
  const provenance = payload.provenance
  if (provenance && typeof provenance === 'object') {
    const m = (provenance as { manifest_sha256?: unknown }).manifest_sha256
    if (typeof m === 'string') return m
  }
  return undefined
}

export function bundleIdOf(payload: Record<string, unknown>): string | undefined {
  const id = payload.bundle_id ?? payload.id
  return typeof id === 'string' ? id : undefined
}

export function receiptIdOf(
  receipt: ActionReceipt | ActionReceiptRecord | Record<string, unknown> | null | undefined,
): string | undefined {
  if (!receipt || typeof receipt !== 'object') return undefined
  const r = receipt as Record<string, unknown>
  const id = r.receipt_id ?? r.id
  return typeof id === 'string' ? id : undefined
}

export function verifyToolUrl(bundleId: string): string {
  return `${VERIFY_TOOL_URL}?bundle_id=${bundleId}`
}

export function apiVerifyUrl(baseUrl: string, bundleId: string): string {
  return `${baseUrl.replace(/\/$/, '')}/v1/extract/${bundleId}/verify`
}

export type ClaimRow = {
  claim?: string
  status?: string
  verdict?: string
  evidence?: { quote?: string; text?: string; paragraphs?: number[] } | string
  confidence?: string
}

export function claimRows(payload: Record<string, unknown>): ClaimRow[] {
  const result = (payload.result && typeof payload.result === 'object'
    ? payload.result
    : {}) as Record<string, unknown>
  const rows =
    result.claim_results ??
    result.claims ??
    payload.claim_results ??
    payload.claims ??
    []
  return Array.isArray(rows) ? (rows.filter((r) => r && typeof r === 'object') as ClaimRow[]) : []
}

export function assertClaimGotcha(rows: ClaimRow[]): void {
  const statuses = new Set(rows.map((r) => String(r.status ?? r.verdict ?? '').toLowerCase()))
  const hasSupported = statuses.has('supported')
  const hasNegative =
    statuses.has('contradicted') || statuses.has('not_found') || statuses.has('unsupported')
  if (!hasSupported || !hasNegative) {
    throw new DocImprintError(
      `expected a supported claim and a contradicted/not_found claim (got statuses=${[...statuses].sort().join(',')})`,
      0,
      'CLAIM_GOTCHA_MISSING',
    )
  }
}

export function pickReceiptForVerify(
  listed: ActionReceiptRecord[],
  preferredId: string | undefined,
): ActionReceiptRecord | undefined {
  if (preferredId) {
    const hit = listed.find((r) => r.id === preferredId)
    if (hit) return hit
  }
  return listed.find((r) => r.action === 'verify_bundle') ?? listed[listed.length - 1]
}

export function printClaimTable(rows: ClaimRow[]): void {
  console.log(chalk.bold('\nClaim check'))
  for (const item of rows) {
    const status = String(item.status ?? item.verdict ?? 'unknown').toLowerCase()
    const color =
      status === 'supported'
        ? chalk.green
        : status === 'contradicted'
          ? chalk.red
          : chalk.yellow
    let quote = ''
    if (item.evidence && typeof item.evidence === 'object') {
      quote = String(item.evidence.quote ?? item.evidence.text ?? '')
    } else if (typeof item.evidence === 'string') {
      quote = item.evidence
    }
    if (quote.length > 180) quote = `${quote.slice(0, 180)}…`
    console.log(`  ${color(status.padEnd(14))} ${item.claim ?? ''}`)
    if (quote) console.log(chalk.dim(`                 Evidence: "${quote}"`))
  }
  console.log()
}

export function printSharePanel(opts: {
  bundleId: string
  manifest: string | undefined
  baseUrl: string
  receiptVerify: Record<string, unknown> | null
  packPath: string | null
}): void {
  console.log(chalk.cyan.bold('\nShareable artifacts'))
  console.log(`  bundle_id          ${opts.bundleId}`)
  console.log(`  manifest_sha256    ${opts.manifest ?? '—'}`)
  console.log(`  verify (UI)        ${verifyToolUrl(opts.bundleId)}`)
  console.log(`  verify (API)       ${apiVerifyUrl(opts.baseUrl, opts.bundleId)}`)
  if (opts.receiptVerify) {
    console.log(`  receipt_id         ${opts.receiptVerify.receipt_id ?? '—'}`)
    console.log(`  receipt valid      ${opts.receiptVerify.valid}`)
  }
  if (opts.packPath) console.log(`  evidence pack      ${opts.packPath}`)
  console.log()
}

export async function writeEvidencePack(
  bundleId: string,
  payload: Record<string, unknown>,
): Promise<string> {
  await mkdir(OUT_DIR, { recursive: true })
  const packPath = path.join(OUT_DIR, `evidence_pack_${bundleId}.json`)
  await writeFile(packPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
  return packPath
}

export function printError(err: unknown): void {
  if (err instanceof DocImprintError) {
    console.error(chalk.red.bold('DocImprintError'))
    console.error(`  ${err.message}`)
    console.error(
      chalk.dim(
        `  status=${err.status}  code=${err.code}  request_id=${err.requestId ?? '—'}`,
      ),
    )
    return
  }
  console.error(err)
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** Multipart extract — local fixture upload (SDK extract is JSON/URL-only). */
export async function extractUploadedFile(opts: {
  apiKey: string
  baseUrl: string
  fileBytes: Buffer
  filename: string
  mode?: string
  claims?: string[]
  lean?: boolean
  retries?: number
}): Promise<Record<string, unknown>> {
  const {
    apiKey,
    baseUrl,
    fileBytes,
    filename,
    mode = 'extract',
    claims,
    lean = false,
    retries = 2,
  } = opts

  const store = lean ? 'false' : 'true'
  const url = `${baseUrl.replace(/\/$/, '')}/v1/extract?sync=true&store=${store}`
  const contentType = filename.toLowerCase().endsWith('.pdf')
    ? 'application/pdf'
    : filename.toLowerCase().endsWith('.html') || filename.toLowerCase().endsWith('.htm')
      ? 'text/html'
      : 'text/plain'

  const attempts = Math.max(1, retries + 1)
  let lastError: DocImprintError | undefined

  for (let attempt = 0; attempt < attempts; attempt++) {
    const form = new FormData()
    form.set('mode', mode)
    if (claims) form.set('claims', JSON.stringify(claims))
    form.set('file', new Blob([new Uint8Array(fileBytes)], { type: contentType }), filename)

    const res = await fetch(url, {
      method: 'POST',
      headers: { Authorization: `Bearer ${apiKey}` },
      body: form,
    })
    const requestId = res.headers.get('x-request-id') ?? undefined

    let payload: Record<string, unknown> = {}
    try {
      payload = (await res.json()) as Record<string, unknown>
    } catch {
      payload = { message: res.statusText }
    }

    if (res.ok) return payload

    const message = String(payload.message ?? payload.error ?? `HTTP ${res.status}`)
    const code = typeof payload.code === 'string' ? payload.code : 'UNKNOWN_ERROR'
    lastError = new DocImprintError(message, res.status, code, requestId)

    if (
      attempt + 1 < attempts &&
      res.status >= 500 &&
      (code === 'PROCESSING_ERROR' || message.includes('AI response'))
    ) {
      await sleep(1500 * (attempt + 1))
      continue
    }
    throw lastError
  }

  throw lastError ?? new DocImprintError('upload failed', 500, 'UPLOAD_FAILED')
}

export async function requireValidReceipt(
  client: DocImprintClient,
  opts: {
    bundleId: string
    preferredId: string | undefined
    allowMissing: boolean
  },
): Promise<{
  receiptVerify: Record<string, unknown> | null
  receiptRows: ActionReceiptRecord[]
  warnings: string[]
}> {
  const warnings: string[] = []
  const listed = await client.listReceipts(opts.bundleId)
  const receiptRows = listed.receipts ?? []
  const chosen = pickReceiptForVerify(receiptRows, opts.preferredId)
  const chosenId = receiptIdOf(chosen) ?? opts.preferredId

  if (!chosenId) {
    if (opts.allowMissing) {
      warnings.push(
        'no action receipts available — document verify succeeded without a signed receipt',
      )
      return { receiptVerify: null, receiptRows, warnings }
    }
    throw new DocImprintError(
      'expected a signed action receipt after verify; none were returned. Pass --allow-missing-receipt only for environments without signing.',
      0,
      'RECEIPT_MISSING',
    )
  }

  const check: VerifyReceiptResponse = await client.verifyReceipt(chosenId)
  const receiptVerify = {
    receipt_id: check.receipt_id || chosenId,
    valid: Boolean(check.valid),
    signature_valid: check.signature_valid,
    manifest_matches_current: check.manifest_matches_current,
    action: check.action,
    agent_id: check.agent_id,
    manifest_sha256: check.manifest_sha256,
    tampered: check.tampered ?? [],
  }
  if (!check.valid) {
    throw new DocImprintError(
      'action receipt verification failed',
      0,
      'RECEIPT_INVALID',
    )
  }
  return { receiptVerify, receiptRows, warnings }
}

export async function loadFixture(): Promise<{
  fileBytes: Buffer
  claims: string[]
  fixturePath: string
}> {
  const msaPath = path.join(FIXTURES_DIR, 'sample_msa.txt')
  const claimsPath = path.join(FIXTURES_DIR, 'claims.json')
  const fileBytes = await readFile(msaPath)
  const claimsDoc = JSON.parse(await readFile(claimsPath, 'utf8')) as { claims?: unknown }
  const claims = claimsDoc.claims
  if (!Array.isArray(claims) || claims.length < 2) {
    throw new DocImprintError(
      'fixtures/claims.json must contain at least two claim strings',
      0,
      'INVALID_FIXTURE',
    )
  }
  return {
    fileBytes,
    claims: claims.map(String),
    fixturePath: msaPath,
  }
}

export function parseArgs(argv: string[]): {
  notarize: boolean
  allowMissingReceipt: boolean
  url?: string
} {
  const notarize = argv.includes('--notarize')
  const allowMissingReceipt = argv.includes('--allow-missing-receipt')
  const urlIdx = argv.indexOf('--url')
  const url = urlIdx >= 0 ? argv[urlIdx + 1] : undefined
  return { notarize, allowMissingReceipt, url }
}
