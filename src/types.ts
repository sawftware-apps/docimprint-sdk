export type ExtractMode =
  | 'extract'
  | 'summarize'
  | 'qa'
  | 'invoice'
  | 'translate'
  | 'claim-check'
  | 'compare'
  | 'describe'
  | 'extract-structured'

export type Confidence = 'high' | 'medium' | 'low'

export interface Citation {
  quote: string
  paragraphs: number[]
  chunk_id?: string
  page?: number
  artifact?: string
  char_start?: number
  char_end?: number
  confidence: Confidence
}

export interface CitedField<T = unknown> {
  value: T
  confidence: Confidence
  citations: Citation[]
}

export interface CitedKeyPoint {
  text: string
  citations: Citation[]
}

export interface ClaimCheckResult {
  claim: string
  status: 'supported' | 'contradicted' | 'not_found'
  evidence: { quote: string; paragraphs: number[] }
  confidence: Confidence
}

export interface InvoiceResult {
  merchant: string | null
  date: string | null
  line_items: Array<{
    description: string
    quantity: number | null
    unit_price: number | null
    total: number
  }>
  subtotal: number | null
  tax: number | null
  total: number | null
}

export interface StoredArtifact {
  r2_key: string
  size: number
  sha256: string
  content_type: string
  url?: string
}

export interface ManifestSignatureBlock {
  signature: string
  signer_address: string
  key_id: string
  algorithm: 'secp256k1-eip191'
  signed_at: string
}

// ── Extract ──────────────────────────────────────────────────────────────────

export interface ExtractRequest {
  source: string
  mode?: ExtractMode
  store?: boolean
  include?: string[]
  question?: string
  claims?: string[]
  schema?: Record<string, unknown>
  target_lang?: string
  compare_bundle_id?: string
  previous_bundle_id?: string
  parent_bundle_id?: string
  collection_id?: string
  retention?: string
  async?: boolean
  webhook?: string
  notarize?: boolean
  pages?: string
  max_tokens?: number
  legal_hold?: boolean
  monitor?: { mode: 'diff' | 'always'; webhook_url: string }
  idempotency_key?: string
}

export interface ExtractResponse {
  bundle_id: string
  mode: ExtractMode
  status: 'complete' | 'queued'
  job_id?: string
  manifest_sha256?: string
  signature?: ManifestSignatureBlock
  merkle_root?: string
  summary?: string
  key_points?: string[]
  summary_cited?: CitedField<string>
  key_points_cited?: CitedKeyPoint[]
  answer?: string
  answer_cited?: CitedField<string>
  claim_results?: ClaimCheckResult[]
  translated_text?: string
  description?: string
  text_visible?: string
  structured_data?: Record<string, unknown>
  structured_data_cited?: Record<string, CitedField>
  invoice?: InvoiceResult
  invoice_cited?: Record<string, CitedField>
  artifacts: Record<string, StoredArtifact>
  metadata: {
    title: string
    word_count: number
    final_url: string
    pages?: number
  }
  model_used?: string
  strategy?: 'full' | 'truncated' | 'chunked'
  idempotent_replay?: true
  collection_id?: string
  monitor_id?: string
}

// ── Focused endpoints ─────────────────────────────────────────────────────────

export interface SummarizeRequest {
  source: string
  store?: boolean
  webhook_url?: string
  idempotency_key?: string
}

export interface SummarizeResponse {
  bundle_id?: string
  summary: string
  key_points: string[]
  model_used?: string
}

export interface QARequest {
  source: string
  question: string
  store?: boolean
  idempotency_key?: string
}

export interface QAResponse {
  bundle_id?: string
  answer: string
  answer_cited?: CitedField<string>
  confidence: Confidence
  model_used?: string
}

export interface TranslateRequest {
  source: string
  target_lang: string
  store?: boolean
  idempotency_key?: string
}

export interface TranslateResponse {
  bundle_id?: string
  translated_text: string
  model_used?: string
}

export interface CheckClaimsRequest {
  source: string
  claims: string[]
  store?: boolean
  idempotency_key?: string
}

export interface CheckClaimsResponse {
  bundle_id?: string
  claim_results: ClaimCheckResult[]
  model_used?: string
}

export interface DescribeRequest {
  source: string
  store?: boolean
  idempotency_key?: string
}

export interface DescribeResponse {
  bundle_id?: string
  description: string
  text_visible?: string
  objects?: string[]
  model_used?: string
}

// ── Jobs ──────────────────────────────────────────────────────────────────────

export type JobType = 'extract' | 'extract_batch' | 'index_collection'
export type JobStatusValue = 'queued' | 'processing' | 'complete' | 'failed' | 'cancelled'

export interface Job {
  id: string
  type: JobType
  status: JobStatusValue
  progress_pct: number
  progress_message: string | null
  bundle_id: string | null
  collection_id: string | null
  error: string | null
  created_at: string
  completed_at: string | null
}

export interface ListJobsOptions {
  status?: JobStatusValue
  limit?: number
  offset?: number
}

// ── Collections ───────────────────────────────────────────────────────────────

export interface Collection {
  id: string
  name: string
  created_at: string
}

export interface CreateCollectionRequest {
  name: string
}

export interface AddToCollectionRequest {
  bundle_id: string
}

export interface SearchCollectionRequest {
  query: string
  limit?: number
}

export interface SearchResult {
  bundle_id: string
  chunk_id: string
  score: number
  text: string
  metadata?: Record<string, unknown>
}

export interface SearchCollectionResponse {
  results: SearchResult[]
}

export interface AskCollectionRequest {
  question: string
  limit?: number
}

export interface AskCollectionResponse {
  answer: string
  answer_cited?: CitedField<string>
  sources: Array<{ bundle_id: string; chunk_id: string; text: string }>
  model_used?: string
}

// ── Verify ────────────────────────────────────────────────────────────────────

export interface VerifyResponse {
  valid: boolean
  bundle_id: string
  manifest_sha256: string
  signature_valid: boolean
  artifacts_valid: boolean
  checked_at: string
  tamper_details?: string[]
}

// ── Notarize ──────────────────────────────────────────────────────────────────

export interface NotarizeResponse {
  tx_hash: string
  block_number: number
  network: string
  eas_attestation_uid?: string
  attested_at: string
}
