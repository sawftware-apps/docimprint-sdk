import { DocImprintError } from './errors'
import type {
  ExtractRequest,
  ExtractResponse,
  SummarizeRequest,
  SummarizeResponse,
  QARequest,
  QAResponse,
  TranslateRequest,
  TranslateResponse,
  CheckClaimsRequest,
  CheckClaimsResponse,
  DescribeRequest,
  DescribeResponse,
  Job,
  ListJobsOptions,
  Collection,
  CreateCollectionRequest,
  AddToCollectionRequest,
  SearchCollectionRequest,
  SearchCollectionResponse,
  AskCollectionRequest,
  AskCollectionResponse,
  VerifyResponse,
  NotarizeResponse,
} from './types'

const DEFAULT_BASE_URL = 'https://api.docimprint.com'

export interface DocImprintClientOptions {
  apiKey: string
  baseUrl?: string
}

export class DocImprintClient {
  private readonly apiKey: string
  private readonly baseUrl: string

  constructor(options: DocImprintClientOptions) {
    this.apiKey = options.apiKey
    this.baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/$/, '')
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })

    const requestId = res.headers.get('x-request-id') ?? undefined

    if (!res.ok) {
      let code = 'UNKNOWN_ERROR'
      let message = `HTTP ${res.status}`
      try {
        const err = (await res.json()) as { error?: string | { code?: string; message?: string } }
        if (typeof err?.error === 'string') {
          message = err.error
        } else {
          code = err?.error?.code ?? code
          message = err?.error?.message ?? message
        }
      } catch {
        // ignore parse errors
      }
      throw new DocImprintError(message, res.status, code, requestId)
    }

    return res.json() as Promise<T>
  }

  // ── Core ────────────────────────────────────────────────────────────────────

  extract(params: ExtractRequest): Promise<ExtractResponse> {
    return this.request<ExtractResponse>('POST', '/v1/extract', params)
  }

  verify(bundleId: string, quick?: boolean): Promise<VerifyResponse> {
    const qs = quick ? '?quick=true' : ''
    return this.request<VerifyResponse>('GET', `/v1/extract/${bundleId}/verify${qs}`)
  }

  download(bundleId: string): Promise<Response> {
    return fetch(`${this.baseUrl}/v1/extract/${bundleId}/download`, {
      headers: { Authorization: `Bearer ${this.apiKey}` },
    })
  }

  notarize(bundleId: string): Promise<NotarizeResponse> {
    return this.request<NotarizeResponse>('POST', `/v1/extract/${bundleId}/notarize`)
  }

  deleteBundle(bundleId: string, opts?: { acknowledgeNotarized?: boolean }): Promise<void> {
    const qs = opts?.acknowledgeNotarized ? '?acknowledge_notarized=true' : ''
    return this.request<void>('DELETE', `/v1/extract/${bundleId}${qs}`)
  }

  // ── Focused endpoints ────────────────────────────────────────────────────────

  summarize(params: SummarizeRequest): Promise<SummarizeResponse> {
    return this.request<SummarizeResponse>('POST', '/v1/summarize', params)
  }

  qa(params: QARequest): Promise<QAResponse> {
    return this.request<QAResponse>('POST', '/v1/qa', params)
  }

  translate(params: TranslateRequest): Promise<TranslateResponse> {
    return this.request<TranslateResponse>('POST', '/v1/translate', params)
  }

  checkClaims(params: CheckClaimsRequest): Promise<CheckClaimsResponse> {
    return this.request<CheckClaimsResponse>('POST', '/v1/check-claims', params)
  }

  describe(params: DescribeRequest): Promise<DescribeResponse> {
    return this.request<DescribeResponse>('POST', '/v1/describe', params)
  }

  // ── Jobs ────────────────────────────────────────────────────────────────────

  getJob(jobId: string): Promise<Job> {
    return this.request<Job>('GET', `/v1/jobs/${jobId}`)
  }

  getQuota(): Promise<{ credits_remaining: number; credits_total: number; resets_at: string }> {
    return this.request('GET', '/v1/quota')
  }

  listJobs(opts?: ListJobsOptions): Promise<{ jobs: Job[] }> {
    const params = new URLSearchParams()
    if (opts?.status) params.set('status', opts.status)
    if (opts?.limit != null) params.set('limit', String(opts.limit))
    if (opts?.offset != null) params.set('offset', String(opts.offset))
    const qs = params.size > 0 ? `?${params}` : ''
    return this.request<{ jobs: Job[] }>('GET', `/v1/jobs${qs}`)
  }

  // ── Collections ──────────────────────────────────────────────────────────────

  createCollection(params: CreateCollectionRequest): Promise<Collection> {
    return this.request<Collection>('POST', '/v1/collections', params)
  }

  listCollections(): Promise<{ collections: Collection[] }> {
    return this.request<{ collections: Collection[] }>('GET', '/v1/collections')
  }

  addToCollection(collectionId: string, params: AddToCollectionRequest): Promise<void> {
    return this.request<void>('POST', `/v1/collections/${collectionId}/documents`, params)
  }

  searchCollection(
    collectionId: string,
    params: SearchCollectionRequest
  ): Promise<SearchCollectionResponse> {
    const qs = new URLSearchParams({ q: params.query })
    if (params.limit != null) qs.set('limit', String(params.limit))
    return this.request<SearchCollectionResponse>('GET', `/v1/collections/${collectionId}/search?${qs}`)
  }

  askCollection(
    collectionId: string,
    params: AskCollectionRequest
  ): Promise<AskCollectionResponse> {
    return this.request<AskCollectionResponse>(
      'POST',
      `/v1/collections/${collectionId}/ask`,
      params
    )
  }
}
