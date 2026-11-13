# Kotoba Bridge core protocol v1

Private inherited stdin/stdout pipes; no listening port. Each UTF-8 JSON line has
`id`, `version:1`, `method`, then flat method parameters. Responses echo id and
version, with `ok:true,result:{...}` or `ok:false,error:"safe message"`.
The UI must launch the expected bundled executable without a shell, verify hello,
serialize requests, bound reads, and stop if the process exits or version differs.
Keys belong only in configure pipe messages, never argv/logs.

- hello → protocol, name, version
- configure(key, pro, demo) → configured; retains budget, resets context/stability
- ocr(image base64 PNG, tesseract executable path) → text
- observe(text, reset optional) → text, empty until stable and not duplicated
- translate(text) → text, calls, chars
- status → calls, chars
- clear → cleared; clears context/cache/stability, retains budget/key
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
