import test from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPairSync } from 'node:crypto';
import { demonstration, signBytes, verifyBytes } from './diagnose.mjs';

for (const result of demonstration()) {
  test(result.case, () => assert.equal(result.actual_verifies, result.expected_verifies));
}

test('transport uses the same bytes that were signed, without serializing twice', () => {
  const { publicKey, privateKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
  const wireBody = Buffer.from(JSON.stringify({ reference: 'demo-002', quantity: 3 }), 'utf8');
  const signature = signBytes(wireBody, privateKey).toString('base64');
  const fakeReceiver = ({ body, signatureBase64 }) => verifyBytes(body, Buffer.from(signatureBase64, 'base64'), publicKey);
  assert.equal(fakeReceiver({ body: wireBody, signatureBase64: signature }), true);
  assert.equal(fakeReceiver({ body: Buffer.concat([wireBody, Buffer.from(' ')]), signatureBase64: signature }), false);
});

test('a modified signature fails even if the message fingerprint is unchanged', () => {
  const { publicKey, privateKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
  const message = Buffer.from('synthetic message');
  const signature = signBytes(message, privateKey);
  signature[0] ^= 1;
  assert.equal(verifyBytes(message, signature, publicKey), false);
});
