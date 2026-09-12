import { constants, generateKeyPairSync, sign, verify, createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';

// Illustrative protocol only: the vendor must specify its algorithm, padding,
// canonical message and signature encoding. This is not a BIGO implementation.
const padding = constants.RSA_PKCS1_PADDING;
export const fingerprint = bytes => createHash('sha256').update(bytes).digest('hex');
export const signBytes = (bytes, privateKey) => sign('sha256', bytes, { key: privateKey, padding });
export const verifyBytes = (bytes, signature, publicKey) => verify('sha256', bytes, { key: publicKey, padding }, signature);

export function demonstration() {
  const { publicKey, privateKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
  const { publicKey: wrongKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
  const text = '{"order_id":"demo-001","recipient":"00042","units":25,"note":"café"}';
  const sent = Buffer.from(text, 'utf8');
  const signature = signBytes(sent, privateKey);
  const reordered = JSON.stringify({ units: 25, recipient: '00042', order_id: 'demo-001', note: 'café' });
  const cases = [
    ['Exact signed UTF-8 bytes', sent, publicKey, true],
    ['Whitespace added after signing', Buffer.from(JSON.stringify(JSON.parse(text), null, 2)), publicKey, false],
    ['Equivalent fields in a different order', Buffer.from(reordered), publicKey, false],
    ['Trailing newline added', Buffer.from(text + '\n'), publicKey, false],
    ['Leading-zero identifier coerced to a number', Buffer.from(text.replace('"00042"', '42')), publicKey, false],
    ['UTF-8 text encoded as Latin-1', Buffer.from(text, 'latin1'), publicKey, false],
    ['Wrong RSA public key', sent, wrongKey, false],
  ];
  return cases.map(([label, received, key, expected]) => ({
    case: label,
    same_message_bytes: sent.equals(received),
    signed_message_sha256: fingerprint(sent),
    received_message_sha256: fingerprint(received),
    expected_verifies: expected,
    actual_verifies: verifyBytes(received, signature, key),
  }));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const results = demonstration();
  console.log(JSON.stringify({ protocol: 'Illustrative RSA-SHA256 / PKCS#1 v1.5 over raw UTF-8 body', network_requests: 0, results }, null, 2));
  if (results.some(r => r.expected_verifies !== r.actual_verifies)) process.exitCode = 1;
}
