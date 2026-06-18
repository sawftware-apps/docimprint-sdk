export class DocImprintError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId: string | undefined

  constructor(message: string, status: number, code: string, requestId?: string) {
    super(message)
    this.name = 'DocImprintError'
    this.status = status
    this.code = code
    this.requestId = requestId
  }
}
