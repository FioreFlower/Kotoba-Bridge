# Kotoba Bridge core protocol v1

Private inherited stdin/stdout pipes; no listening port. Each UTF-8 JSON line has
`id`, `version:1`, `method`, then flat method parameters. Responses echo id and
version, with `ok:true,result:{...}` or `ok:false,error:"safe message"`.
The UI must launch the expected bundled executable without a shell, verify hello,
serialize requests, bound reads, and stop if the process exits or version differs.
Keys belong only in configure pipe messages, never argv/logs.

- hello → protocol, name, version
- configure(key, pro, demo) → configured; retains budget, resets context/stability
- ocr(image base64 PNG, tesseract executable path, scope optional) → text, cached
  This is also the local-only preview API: no configure/key/translation is required.
- observe(text, reset optional) → text, empty until stable and not duplicated
- translate(text) → text, calls, chars
- status → calls, chars, retry_after_ms, remaining_calls, remaining_chars
  UI should wait cancellation-aware for retry_after_ms, then revalidate current
  foreground/ROI/OCR before requesting translation. No request is auto-retried.
- clear → cleared; clears context/cache/stability, retains budget/key
- forget_key → forgotten; clears key/configuration/context/caches, retains budgets;
  configure is required again afterward, including for demo.
- shutdown → shutdown then exits

OCR accepts PNG up to 2.1 million pixels, invokes Tesseract via stdin/stdout with
jpn and psm 6, 6-second timeout, single OpenMP thread, no shell. No image is sent
to DeepL. Native Tesseract and model deployment remain required.

Requests are processed serially. No automatic network retry or process restart.
UI stop must discard pending results; it cannot unsend an already dispatched HTTP
request. API call reservation happens before dispatch; failures retain reservation.
Restarting the process resets session budget, so it is not an account monthly cap.
The parent UI independently checks foreground/region and verifies post-translation
OCR before displaying results. Core alone has no desktop/window access.

Tests inject HTTP transports. No real API invocation was made. Linux compilation
and Windows x64 cross-compilation do not constitute Windows execution validation.

## v0.2.0 hardening (protocol remains 1)

Request IDs must be positive safe integers or nonempty strings of at most 64
bytes. Input lines remain capped at 12 MiB; encoded response lines at 128 KiB.
Observation text is capped at 2,000 Unicode characters and clears stability on
oversize rejection. Configure rejects whitespace/control/non-ASCII keys and keys
over 4,096 bytes without mutating the existing session. An empty key preserves
an existing key, matching protocol 1; forget_key is explicit and does not refund
or reset budgets. Keys cannot be securely erased from all previous heap copies.

OCR retains one successful text result and a SHA256 request fingerprint in RAM,
not image bytes. The key includes PNG data, engine path and UI-provided scope.
Use a stable scope such as physical ROI coordinates and reset on a new selection.
Repeated identical frames reuse OCR for less than three seconds; different
frames/engines/scopes, expiry, failures, clear, configure, forget_key or
observe(reset=true) invalidate it. Model or binary contents changed at the same
path may take up to three seconds to affect output; clear forces fresh OCR.
This cache is independent of paid translation caching and does not perform any
semantic similarity matching. It reduces repeated process launches but has not
been benchmarked on low-spec Windows hardware.

OCR output is capped at 16 KiB. Child process lifetime is capped at six seconds
with a 500 ms post-exit pipe wait bound. Test fixtures exercise a real local child
process on stdin/stdout without Tesseract, secrets or network access. They do not
validate actual Japanese OCR accuracy or Windows game capture.
