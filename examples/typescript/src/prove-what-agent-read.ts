/**
 * Hero demo: prove what an AI agent read — claim-check + evidence + receipt.
 *
 * Usage:
 *   npm run prove
 *   npm run prove -- --notarize
 *   npm run prove -- --allow-missing-receipt
 */

import chalk from 'chalk'
import {
  assertClaimGotcha,
  bundleIdOf,
  claimRows,
  createClient,
  extractUploadedFile,
  loadConfig,
  loadFixture,
  manifestSha256,
  parseArgs,
  printClaimTable,
  printError,
  printSharePanel,
  receiptIdOf,
  requireValidReceipt,
  verifyToolUrl,
  apiVerifyUrl,
  writeEvidencePack,
} from './shared.js'

async function main(): Promise<void> {
  const { notarize, allowMissingReceipt } = parseArgs(process.argv.slice(2))
  const { apiKey, baseUrl } = loadConfig()
  const { fileBytes, claims, fixturePath } = await loadFixture()
  const client = createClient(apiKey, baseUrl)
  const warnings: string[] = []

  console.log(chalk.magenta.bold('\nProve what the agent read'))
  console.log(chalk.bold('Problem'))
  console.log('  An agent asserted two clauses about this MSA.')
  console.log('  A chat log cannot prove either claim — DocImprint can.')
  console.log(chalk.dim(`Fixture: ${fixturePath}\n`))

  console.log(chalk.bold('1/3'), 'Claim-check + store evidence bundle…')
  const claimsResp = await extractUploadedFile({
    apiKey,
    baseUrl,
    fileBytes,
    filename: 'sample_msa.txt',
    mode: 'claim-check',
    claims,
    lean: false,
    retries: 3,
  })
  const rows = claimRows(claimsResp)
  printClaimTable(rows)
  assertClaimGotcha(rows)

  const bundleId = bundleIdOf(claimsResp)
  if (!bundleId) {
    throw new Error('claim-check response missing bundle_id')
  }
  const manifest = manifestSha256(claimsResp)
  console.log(`  bundle_id = ${chalk.cyan(bundleId)}`)
  console.log(`  manifest  = ${chalk.cyan(manifest ?? '—')}\n`)

  console.log(chalk.bold('2/3'), 'Verifying bundle integrity…')
  const verified = await client.verify(bundleId)
  if (!verified.valid) {
    throw new Error('bundle verification failed')
  }
  const inlineRid = receiptIdOf(verified.receipt ?? null)
  console.log(`  valid = ${chalk.green('true')}`)
  if (inlineRid) {
    console.log(`  inline receipt_id = ${chalk.cyan(inlineRid)}`)
  } else {
    warnings.push('verify returned no inline receipt — will try listReceipts next')
  }
  console.log()

  let notarizeSummary: Record<string, unknown> | null = null
  if (notarize) {
    console.log(chalk.cyan.bold('Optional'), 'Notarizing on-chain…')
    const notarized = await client.notarize(bundleId)
    notarizeSummary = {
      tx_hash: notarized.tx_hash,
      network: notarized.network,
      eas_attestation_uid: notarized.eas_attestation_uid,
      attested_at: notarized.attested_at,
      receipt_id: receiptIdOf(notarized.receipt ?? null),
    }
    console.log(`  attestation = ${JSON.stringify(notarizeSummary)}`)
    console.log()
  }

  console.log(chalk.bold('3/3'), 'Independently verifying the action receipt…')
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
    console.log(
      `  receipt valid = ${chalk.green('true')}  ` +
        `(signature_valid=${receiptVerify.signature_valid}, ` +
        `manifest_matches_current=${receiptVerify.manifest_matches_current})`,
    )
  } else {
    console.log(chalk.yellow('  skipped (no receipt)'))
  }

  const pack = {
    demo: 'prove_what_agent_read',
    fixture: 'sample_msa.txt',
    claims_input: claims,
    claim_results: rows,
    bundle_id: bundleId,
    manifest_sha256: manifest ?? manifestSha256(verified as unknown as Record<string, unknown>),
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

  const packPath = await writeEvidencePack(bundleId, pack)
  printSharePanel({
    bundleId,
    manifest: pack.manifest_sha256,
    baseUrl,
    receiptVerify,
    packPath,
  })
  for (const w of warnings) console.warn(chalk.yellow('warning:'), w)
}

main().catch((err) => {
  printError(err)
  process.exit(1)
})
