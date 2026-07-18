import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { DocImprintError } from 'docimprint'
import {
  assertClaimGotcha,
  claimRows,
  manifestSha256,
  pickReceiptForVerify,
  receiptIdOf,
} from './shared.js'

describe('shared helpers', () => {
  it('manifestSha256 reads provenance or top-level', () => {
    assert.equal(manifestSha256({ provenance: { manifest_sha256: 'abc' } }), 'abc')
    assert.equal(manifestSha256({ manifest_sha256: 'top' }), 'top')
  })

  it('claimRows normalizes shapes', () => {
    const rows = claimRows({
      result: { claim_results: [{ claim: 'a', status: 'supported' }] },
    })
    assert.equal(rows[0]?.status, 'supported')
  })

  it('assertClaimGotcha requires supported + negative', () => {
    assertClaimGotcha([
      { status: 'supported' },
      { status: 'contradicted' },
    ])
    assert.throws(
      () => assertClaimGotcha([{ status: 'supported' }, { status: 'supported' }]),
      (err: unknown) => err instanceof DocImprintError && err.code === 'CLAIM_GOTCHA_MISSING',
    )
  })

  it('pickReceiptForVerify prefers verify_bundle', () => {
    const chosen = pickReceiptForVerify(
      [
        {
          id: 'rcpt_1',
          bundle_id: 'ev_1',
          agent_id: 'a',
          action: 'get_bundle',
          manifest_sha256: 'x',
          signature: 's',
          signer_address: '0x',
          key_id: 'k',
          algorithm: 'secp256k1-eip191',
          created_at: 't',
        },
        {
          id: 'rcpt_2',
          bundle_id: 'ev_1',
          agent_id: 'a',
          action: 'verify_bundle',
          manifest_sha256: 'x',
          signature: 's',
          signer_address: '0x',
          key_id: 'k',
          algorithm: 'secp256k1-eip191',
          created_at: 't',
        },
      ],
      undefined,
    )
    assert.equal(receiptIdOf(chosen), 'rcpt_2')
  })
})
