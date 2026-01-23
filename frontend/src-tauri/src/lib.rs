use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::Stdio;
use std::sync::Mutex;
use std::time::Duration;

use tauri::Manager;

#[derive(Default)]
struct Sidecars {
  ollama: Option<std::process::Child>,
  backend: Option<std::process::Child>,
}

impl Drop for Sidecars {
  fn drop(&mut self) {
    if let Some(mut child) = self.ollama.take() {
      let _ = child.kill();
      let _ = child.wait();
    }

    if let Some(mut child) = self.backend.take() {
      let _ = child.kill();
      let _ = child.wait();
    }
  }
}

fn is_port_open(addr: SocketAddr, timeout: Duration) -> bool {
  TcpStream::connect_timeout(&addr, timeout).is_ok()
}

fn official_ollama_models_dir() -> Option<PathBuf> {
  // Ollama's default model cache is under ~/.ollama/models across macOS/Linux.
  // On Windows it is typically %USERPROFILE%\.ollama\models.
  let home = dirs::home_dir()?;
  Some(home.join(".ollama").join("models"))
}

fn is_dir_non_empty(path: &Path) -> bool {
  std::fs::read_dir(path).map(|mut it| it.next().is_some()).unwrap_or(false)
}

fn copy_dir_recursive(src: &Path, dst: &Path) -> std::io::Result<()> {
  if !dst.exists() {
    std::fs::create_dir_all(dst)?;
  }
  for entry in std::fs::read_dir(src)? {
    let entry = entry?;
    let file_type = entry.file_type()?;
    let from = entry.path();
    let to = dst.join(entry.file_name());
    if file_type.is_dir() {
      copy_dir_recursive(&from, &to)?;
    } else if file_type.is_file() {
      if let Some(parent) = to.parent() {
        std::fs::create_dir_all(parent)?;
      }
      // Overwrite behavior: keep it simple and overwrite (installer resource is authoritative).
      std::fs::copy(&from, &to)?;
    }
  }
  Ok(())
}

fn resolve_ollama_executable() -> Option<PathBuf> {
  // When bundled, Tauri places externalBin sidecars next to the main executable.
  // During development, tauri-build copies the matching binaries/*-<triple> into the target dir.
  let exe = std::env::current_exe().ok()?;
  let exe_dir = exe.parent()?;
  let name = if cfg!(windows) { "ollama.exe" } else { "ollama" };
  let candidate = exe_dir.join(name);
  if candidate.exists() {
    return Some(candidate);
  }

  // Fallback to PATH (e.g., when user has system Ollama installed).
  Some(PathBuf::from(name))
}

fn resolve_backend_executable() -> Option<PathBuf> {
  let exe = std::env::current_exe().ok()?;
  let exe_dir = exe.parent()?;
  let name = if cfg!(windows) { "pdc-backend.exe" } else { "pdc-backend" };
  let candidate = exe_dir.join(name);
  if candidate.exists() {
    return Some(candidate);
  }
  Some(PathBuf::from(name))
}

fn seed_models_from_resources_if_present(app: &tauri::AppHandle, models_dir: &Path) -> Result<(), Box<dyn std::error::Error>> {
  // If the app was bundled with a model payload under src-tauri/resources/ollama_models,
  // copy it into the official models dir on first run.
  let resource_dir = app.path().resource_dir()?;
  let bundled = resource_dir.join("ollama_models");

  if !bundled.exists() {
    return Ok(());
  }

  let marker = models_dir.join(".pdc_seeded");
  if marker.exists() {
    return Ok(());
  }

  if is_dir_non_empty(models_dir) {
    // If user already has models, don't overwrite or merge by default.
    return Ok(());
  }

  std::fs::create_dir_all(models_dir)?;
  copy_dir_recursive(&bundled, models_dir)?;
  std::fs::write(marker, b"seeded")?;
  Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      // Global sidecar holder (killed on app exit).
      app.manage(Mutex::new(Sidecars::default()));

      // Start Ollama as a bundled sidecar (fastest offline path).
      // If user already runs Ollama on 127.0.0.1:11434, we leave it alone.
      let ollama_addr: SocketAddr = "127.0.0.1:11434".parse().expect("valid socket addr");
      if !is_port_open(ollama_addr, Duration::from_millis(200)) {
        let models_dir = official_ollama_models_dir().ok_or("Failed to resolve home dir for Ollama models")?;

        // Optional: seed pre-bundled models into official cache dir.
        seed_models_from_resources_if_present(app.handle(), &models_dir)?;

        // Create directory so Ollama doesn't error on missing path when we set OLLAMA_MODELS.
        std::fs::create_dir_all(&models_dir)?;

        // Launch Ollama. Prefer the bundled sidecar (next to the app binary), fallback to PATH.
        let ollama_exe = resolve_ollama_executable().ok_or("Failed to resolve ollama executable")?;
        let mut cmd = std::process::Command::new(ollama_exe);
        cmd
          .args(["serve"])
          .env("OLLAMA_HOST", "127.0.0.1:11434")
          .env("OLLAMA_MODELS", models_dir.to_string_lossy().to_string())
          .stdin(Stdio::null())
          .stdout(Stdio::null())
          .stderr(Stdio::null());

        let child = cmd.spawn()?;
        if let Ok(mut sidecars) = app.state::<Mutex<Sidecars>>().lock() {
          sidecars.ollama = Some(child);
        }
      }

      // Start backend API (required for the UI; packaged app has no separate dev server).
      let backend_addr: SocketAddr = "127.0.0.1:8000".parse().expect("valid socket addr");
      if !is_port_open(backend_addr, Duration::from_millis(200)) {
        let data_dir = app.path().app_data_dir()?;
        std::fs::create_dir_all(&data_dir)?;

        let backend_exe = resolve_backend_executable().ok_or("Failed to resolve backend executable")?;
        let mut cmd = std::process::Command::new(backend_exe);
        cmd
          .args(["--host", "127.0.0.1", "--port", "8000"])
          // Tell backend it's running in desktop mode; it will use SQLite + local storage under this dir.
          .env("PDC_DATA_DIR", data_dir.to_string_lossy().to_string())
          // Ensure backend uses the Ollama instance we manage.
          .env("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
          .stdin(Stdio::null())
          .stdout(Stdio::null())
          .stderr(Stdio::null());

        let child = cmd.spawn()?;

        if let Ok(mut sidecars) = app.state::<Mutex<Sidecars>>().lock() {
          sidecars.backend = Some(child);
        }

        // Wait briefly for readiness to reduce front-end "Load failed" on startup.
        for _ in 0..60 {
          if is_port_open(backend_addr, Duration::from_millis(200)) {
            break;
          }
          std::thread::sleep(Duration::from_millis(250));
        }
      }

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
