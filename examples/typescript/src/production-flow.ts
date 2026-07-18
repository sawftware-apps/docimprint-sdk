/**
 * Evidence + receipt deep dive: URL extract → verify → optional notarize → receipt.
 *
 * Usage:
 *   npm run production-flow -- --url https://example.com/contract.pdf
 *   npm run production-flow -- --url https://example.com/contract.pdf --notarize
 */

import chalk from 'chalk'
import {
  apiVerifyUrl,
  bundleIdOf,
  createClient,
  extractUrl,
  loadConfig,
  manifestSha256,
  parseArgs,
  printError,
  printSharePanel,
  receiptIdOf,
  requireValidReceipt,
  verifyToolUrl,
  writeEvidencePack,
} from './shared.js'

async function main(): Promise<void> {
  const { notarize, allowMissingReceipt, url } = parseArgs(process.argv.slice(2))
  if (!url) {
    console.error(chalk.red('error:'), '--url is required')
    process.exit(1)
  }

  const { apiKey, baseUrl } = loadConfig()
  const client = createClient(apiKey, baseUrl)
  const warnings: string[] = []

  console.log(chalk.blue.bold('\nEvidence + receipt'))
  console.log('  Extract a URL into a signed bundle, verify integrity,')
  console.log('  then independently audit the action receipt.\n')

  const extracted = await extractUrl({ apiKey, baseUrl, url, retries: 3 })

  const bundleId = bundleIdOf(extracted)
  if (!bundleId) {
    throw new Error('extract response missing bundle_id')
  }
  const manifest = manifestSha256(extracted)
  console.log(`  bundle_id = ${chalk.cyan(bundleId)}`)
  console.log(`  manifest  = ${chalk.cyan(manifest ?? '—')}`)

  const verified = await client.verify(bundleId)
  if (!verified.valid) {
    throw new Error('bundle verification failed')
  }
  console.log(`  verify   = ${chalk.green('valid')}`)
  const inlineRid = receiptIdOf(verified.receipt ?? null)

  let notarizeSummary: Record<string, unknown> | null = null
  if (notarize) {
    const notarized = await client.notarize(bundleId)
    notarizeSummary = {
      tx_hash: notarized.tx_hash,
      network: notarized.network,
      eas_attestation_uid: notarized.eas_attestation_uid,
      attested_at: notarized.attested_at,
      receipt_id: receiptIdOf(notarized.receipt ?? null),
    }
    console.log('  notarize = done')
  }

  const { receiptVerify, receiptRows, warnings: receiptWarnings } = await requireValidReceipt(
    client,
    {
      bundleId,
      preferredId: inlineRid,
      allowMissing: allowMissingReceipt,
    },
  )
  warnings.push(...receiptWarnings)
  if (receiptVerify) {
    console.log(`  receipt  = ${chalk.green('valid')}`)
  }

  const summary = {
    demo: 'production_flow',
    source_url: url,
    bundle_id: bundleId,
    manifest_sha256: manifest ?? verified.manifest_sha256,
    verify: {
      valid: true,
      manifest_sha256: verified.manifest_sha256 ?? manifest,
      signature_valid: verified.signature_valid,
      artifacts_valid: verified.artifacts_valid,
    },
    notarize: notarizeSummary,
    inline_receipt_id: inlineRid ?? null,
    receipt_list_count: receiptRows.length,
    receipt_verify: receiptVerify,
    links: {
      verify_ui: verifyToolUrl(bundleId),
      verify_api: apiVerifyUrl(baseUrl, bundleId),
    },
    warnings,
  }

  const packPath = await writeEvidencePack(bundleId, summary)
  printSharePanel({
    bundleId,
    manifest: summary.manifest_sha256,
    baseUrl,
    receiptVerify,
    packPath,
  })
  for (const w of warnings) console.warn(chalk.yellow('warning:'), w)
  console.log(JSON.stringify({ ok: true, ...summary }, null, 2))
}

main().catch((err) => {
  printError(err)
  process.exit(1)
})
