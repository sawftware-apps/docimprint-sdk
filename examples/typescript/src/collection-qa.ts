/**
 * RAG demo: index multiple documents into a collection, then ask across them.
 *
 * A collection is DocImprint's multi-document memory — index several evidence
 * bundles once, then search or ask cross-document questions with citations
 * back to the specific bundle + chunk each answer came from. Common pattern
 * for agents doing due diligence, research, or contract review across a
 * folder of documents rather than one file at a time.
 *
 * Usage:
 *   npm run collection-qa
 *   npm run collection-qa -- --url https://example.com/doc2.pdf
 */

import chalk from 'chalk'
import {
  bundleIdOf,
  citedText,
  createClient,
  extractUploadedFile,
  extractUrl,
  loadConfig,
  loadFixture,
  parseArgs,
  printError,
  writeEvidencePack,
} from './shared.js'

const DEFAULT_SECOND_URL = 'https://en.wikipedia.org/wiki/Non-disclosure_agreement'
const DEFAULT_QUESTION = 'What does this document say about termination notice periods?'
const DEFAULT_SEARCH_QUERY = 'termination notice'

function printResultsTable(title: string, rows: Array<Record<string, unknown>>): void {
  console.log(chalk.bold(`\n${title}`))
  for (const row of rows) {
    const bundleId = String(row.bundle_id ?? '—')
    const score = typeof row.score === 'number' ? row.score.toFixed(3) : '—'
    let text = String(row.text ?? '')
    if (text.length > 160) text = `${text.slice(0, 160)}…`
    console.log(`  ${chalk.cyan(bundleId.padEnd(14))} ${score.padEnd(8)} ${text}`)
  }
  console.log()
}

async function main(): Promise<void> {
  const { url } = parseArgs(process.argv.slice(2))
  const secondUrl = url ?? DEFAULT_SECOND_URL
  const { apiKey, baseUrl } = loadConfig()
  const { fileBytes, fixturePath } = await loadFixture()
  const client = createClient(apiKey, baseUrl)

  console.log(chalk.green.bold('\nCollection Q&A (RAG)'))
  console.log(chalk.bold('Problem'))
  console.log('  An agent needs to answer questions across a folder of documents,')
  console.log('  not just one file — and cite which document each answer came from.\n')

  console.log(chalk.bold('1/4'), 'Creating a collection…')
  const collection = (await client.createCollection({
    name: 'Example collection — MSA + web doc',
  })) as unknown as Record<string, unknown>
  const collectionId = String(collection.collection_id ?? collection.id ?? '')
  if (!collectionId) {
    throw new Error('createCollection response missing collection id')
  }
  console.log(`  collection_id = ${chalk.cyan(collectionId)}\n`)

  console.log(chalk.bold('2/4'), 'Indexing documents into the collection…')
  const indexedBundleIds: string[] = []

  const extractedFixture = await extractUploadedFile({
    apiKey,
    baseUrl,
    fileBytes,
    filename: 'sample_msa.txt',
    mode: 'extract',
    lean: false,
  })
  const fixtureBundleId = bundleIdOf(extractedFixture)
  if (!fixtureBundleId) {
    throw new Error('extract response missing bundle_id')
  }
  await client.addToCollection(collectionId, { bundle_id: fixtureBundleId })
  indexedBundleIds.push(fixtureBundleId)
  console.log(`  + ${fixturePath.split('/').pop()} → ${chalk.cyan(fixtureBundleId)}`)

  const extractedUrl = await extractUrl({ apiKey, baseUrl, url: secondUrl, retries: 3 })
  const urlBundleId = bundleIdOf(extractedUrl)
  if (!urlBundleId) {
    throw new Error('extract response missing bundle_id')
  }
  await client.addToCollection(collectionId, { bundle_id: urlBundleId })
  indexedBundleIds.push(urlBundleId)
  console.log(`  + ${secondUrl} → ${chalk.cyan(urlBundleId)}\n`)

  console.log(chalk.bold('3/4'), 'Asking a cross-collection question…')
  const answer = await client.askCollection(collectionId, { question: DEFAULT_QUESTION })
  const { text: answerText } = citedText(answer.answer)
  console.log(chalk.magenta(`\nQ: "${DEFAULT_QUESTION}"`))
  console.log(answerText || '(no answer)')
  if (answer.sources?.length) {
    console.log(chalk.dim(`  ${answer.sources.length} source(s) — see evidence pack for full detail`))
  }
  console.log()

  console.log(chalk.bold('4/4'), 'Raw search across the collection…')
  const search = await client.searchCollection(collectionId, {
    query: DEFAULT_SEARCH_QUERY,
    limit: 5,
  })
  printResultsTable(
    `search: "${DEFAULT_SEARCH_QUERY}"`,
    (search.results ?? []) as unknown as Array<Record<string, unknown>>,
  )

  const pack = {
    demo: 'collection_qa',
    collection_id: collectionId,
    indexed_bundle_ids: indexedBundleIds,
    question: DEFAULT_QUESTION,
    answer: answer.answer,
    sources: answer.sources,
    search_query: DEFAULT_SEARCH_QUERY,
    search_results: search.results,
  }
  const packPath = await writeEvidencePack(collectionId, pack)
  console.log(chalk.dim(`Evidence pack written to ${packPath}`))
}

main().catch((err) => {
  printError(err)
  process.exit(1)
})
