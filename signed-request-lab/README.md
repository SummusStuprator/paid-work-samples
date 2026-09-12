# Why a valid RSA signature can fail at the receiver

An offline diagnostic example, written by an AI coding assistant. No vendor API is contacted. All messages are synthetic and RSA keys are generated in memory for each run, never saved or printed.

```sh
node --test diagnose.test.mjs
node diagnose.mjs
```

No installation or credentials needed. Tested with Node 24.15.0.

The sender signs one UTF-8 byte sequence. The example then verifies it after changes that can occur in an integration: JSON reformatting, field reordering, a trailing newline, coercing an identifier to a number, and changing the character encoding. Each changed message fails verification. The original message also fails with the wrong public key. A transport test signs the final serialized buffer and passes that same buffer to a fake receiver.

The JSON output records synthetic-message SHA-256 hashes and boolean verification outcomes. A matching message hash rules out a message-byte mismatch in this controlled example; it does **not** prove that the vendor algorithm, key, signature encoding, timestamp, path or authentication fields are correct. A wrong-key case demonstrates that distinction.

## Applying the diagnostic to a real integration

First obtain the vendor's documented signing algorithm, padding, canonical message format and signature encoding, together with a public or safely redacted test vector. This example deliberately chooses RSA-SHA256, PKCS#1 v1.5 and the raw JSON body. Those choices are illustrative, **not a claim about BIGO or any other vendor's protocol**. Some APIs sign canonical fields, a digest or a method/path/body combination instead.

Use an agreed synthetic request to compare the bytes entering the signer with the bytes expected by the verifier. Avoid recording private keys, authorization headers or real customer payloads. Message hashes alone can also disclose guessable information; this sample logs only invented data. Then test a vendor-approved diagnostic endpoint using the actual protocol. An IP allowlist failure is a separate layer and cannot be diagnosed by this offline example.

Correct signatures do not make order retries safe. A response timeout may follow successful remote fulfillment. The production integration needs the provider's documented duplicate-reference/idempotency or order-status semantics; if these are unavailable, ambiguous results need reconciliation rather than blind replay. This sample implements no order fulfillment, WordPress plugin, retry engine or live payment operation.

Reference: [Node.js cryptographic signing and verification](https://nodejs.org/docs/latest-v24.x/api/crypto.html#cryptosignalgorithm-data-key-callback). The repository's MIT license applies.
