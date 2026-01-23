# Frontend (Vue3 + Vite)

## Web dev

```bash
cd frontend
npm i
npm run dev
```

## Desktop dev (Tauri)

```bash
cd frontend
npm run tauri:dev
```

Notes:
- `tauri:dev` will auto-start the backend if `http://127.0.0.1:8000/health` is not reachable.
- Backend logs (when auto-started) go to `/tmp/pdc-backend-dev.log`.
- If you prefer to run backend yourself, start it first (e.g. `make backend`), then run `npm run tauri:dev`.

## Desktop build artifacts (macOS / Windows / Linux)

Not DMG-only.

- macOS: `.app` + `.dmg`
- Windows: typically `.msi` (and/or NSIS `.exe`, depending on bundler config)
- Linux: typically `.deb` / `.rpm` / AppImage

In general, build installers on the target OS.

## Offline desktop build (Scheme A, huge)

See [../docs/offline-ollama.md](../docs/offline-ollama.md).

macOS one-shot:

```bash
cd ..
make tauri-build-offline
```
