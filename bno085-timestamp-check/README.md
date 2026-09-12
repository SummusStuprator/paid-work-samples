# BNO085 timestamp contract reproduction

Two timestamp inconsistencies reproduced in the public `bradcar/bno08x_i2c_spi_MicroPython` driver. This small Python script runs four checks against unmodified method bodies from a pinned source file. **Two controls pass; two contract expectations fail.** It is a reproduction, not a fixed driver or a device test.

Prepared by Summus Code using an autonomous AI coding assistant. The reproduction script is MIT licensed; the separately supplied upstream driver retains its own licence.

No packages, hardware, credentials, full driver import, or network access are needed to run the script. The source file is supplied by the caller and is never changed. All sensor bytes are synthetic. These results do not establish that any particular firmware uses the affected code, or explain physical heading drift.

## Run it

Requires Python 3.8 or later. From this directory, supply the driver's `lib/bno08x.py` at commit [`3434f59998d3c8cf0036dd5a9e4b8b5c0a1e2cdf`](https://github.com/bradcar/bno08x_i2c_spi_MicroPython/tree/3434f59998d3c8cf0036dd5a9e4b8b5c0a1e2cdf):

```sh
python repro.py --source /path/to/bno08x.py --observe
python repro.py --source /path/to/bno08x.py
```

If you do not have that file, the following **explicit download command** fetches the pinned public source. The reproduction itself never downloads anything.

macOS/Linux:

```sh
curl --fail --location --output bno08x-pinned.py https://raw.githubusercontent.com/bradcar/bno08x_i2c_spi_MicroPython/3434f59998d3c8cf0036dd5a9e4b8b5c0a1e2cdf/lib/bno08x.py
python3 repro.py --source bno08x-pinned.py --observe
python3 repro.py --source bno08x-pinned.py
```

Windows PowerShell:

```powershell
Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/bradcar/bno08x_i2c_spi_MicroPython/3434f59998d3c8cf0036dd5a9e4b8b5c0a1e2cdf/lib/bno08x.py' -OutFile bno08x-pinned.py
python repro.py --source bno08x-pinned.py --observe
python repro.py --source bno08x-pinned.py
```

The script verifies SHA-256 `31b32dcd31f495dc6977f3a23c7a1d025c391c912081be763e1bdeb306e5ae70` **after converting CRLF line endings to LF**. This accepts Windows Git text checkouts and raw LF source while rejecting other changes before execution. It does not claim to test later revisions or a patched file.

## Expected and observed

All cases set the host interrupt time to 5,000 ms and the epoch to zero. Base/rebase/report-delay ticks are 100 microseconds. [observed.json](observed.json) contains the generated values.

| Case | Expected timestamp | Upstream timestamp | Check |
|---|---:|---:|---|
| Zero base and delay | 5,000 ms | 5,000 ms | Pass control |
| Base 40,000 ticks; delay 10,000 ticks | 2,000 ms | 2,000 ms | Pass control |
| Signed base -10 ticks | 5,001 ms | -429,491,728.6 ms | Fail |
| Base 40,000; rebase +15,000; delay 10,000 ticks | 3,500 ms | 2,000 ms | Fail |

The normal test command intentionally exits **1** with `Ran 4 tests` and `FAILED (failures=2)` against this exact upstream revision. `--observe` exits **0** after emitting JSON, even when values differ. A source/hash/argument error exits **2**. No failing expectation has been relaxed to make the suite pass.

## Evidence and limits

The [Hillcrest SH-2 Reference Manual v1.2, sections 7.2.1–7.2.2, printed page 80 / PDF page 81](https://cdn.sparkfun.com/assets/4/d/9/3/8/SH-2-Reference-Manual-v1.2.pdf#page=81) specifies signed base and rebase deltas. Its example starts with a 5-second interrupt and a 4-second base delta, adds a 1.5-second rebase and a 1-second report delay, and yields a 3.5-second timestamp. The [CEVA reference implementation](https://github.com/ceva-dsp/sh2/blob/b514b1e2586ddc195e553dac89fc94c637b25298/sh2.c) also uses signed `int32_t` timebases and accumulates the rebase.

In the [pinned Python driver's fast path](https://github.com/bradcar/bno08x_i2c_spi_MicroPython/blob/3434f59998d3c8cf0036dd5a9e4b8b5c0a1e2cdf/lib/bno08x.py#L893), the base delta is decoded unsigned. The packet base is then cached before iterating over reports; a later rebase does not update the cached value used by subsequent sensor timestamps.

The script extracts only `update_sensors` and `_process_report` with Python AST, removing decorators while preserving their method bodies. A stub replaces packet reading, and selected report constants match upstream. The identity rotation report merely carries a timestamp; no orientation or calibration claim is tested. Small no-wrap clock values isolate the arithmetic from MicroPython clock wrapping. GPIO, transport framing, actual interrupt timing, report frequency, and physical sensor behavior are not validated.

A useful next step is to confirm whether an application's actual driver and heading logic consume these timestamps, then compare recorded inputs and regression tests before considering a correction. Hardware validation remains necessary for physical results.
