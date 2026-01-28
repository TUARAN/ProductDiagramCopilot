# Tauri sidecars (desktop packaging)

This app can launch these processes as Tauri sidecars:

- `ollama` (local model server)
- `pdc-backend` (FastAPI backend that serves `/api/*`)

Tauri expects platform-specific filenames under this directory.

Example filenames (macOS Apple Silicon):

- `ollama-aarch64-apple-darwin`
- `pdc-backend-aarch64-apple-darwin`

These files are generated locally for packaging and are gitignored.

For macOS offline packaging:

- Prepare Ollama sidecar from the installed Ollama.app:
	- `make ollama-sidecar`
- Build backend sidecar via PyInstaller:
	- `make backend-sidecar`
