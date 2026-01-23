# 离线打包 Ollama（最快但体积大）

本项目后端默认通过 `OLLAMA_BASE_URL` 调用 Ollama 的本地 HTTP 服务（通常是 `http://127.0.0.1:11434`）。

要实现“安装即离线可用”，最简单粗暴的方式（方案 A）是：

1) **把后端 API 一起打进桌面安装包**（Tauri sidecar：`pdc-backend`，用于提供 `/api/*`）
2) **把 Ollama 二进制一起打进桌面安装包**（Tauri sidecar：`ollama`，用于提供本地模型服务）
3) **把 Ollama 官方模型缓存目录 (`.ollama/models`) 直接打进安装包**（体积巨大）

## 1) 官方模型目录（用户放到指定路径）

Ollama 默认模型缓存目录通常是：

- macOS / Linux: `~/.ollama/models`
- Windows: `%USERPROFILE%\\.ollama\\models`

如果你希望用其它位置，也可以通过环境变量 `OLLAMA_MODELS` 覆盖。

## 2) 方案 A：把模型直接打进安装包（你选择的方案）

在打包机上先确保本机已通过 Ollama 下载好模型（即 `~/.ollama/models` 已有内容）。

然后把该目录复制到 Tauri bundle resources：

```bash
make ollama-bundle
```

它等价于：

```bash
./scripts/prepare-bundled-ollama-models.sh ~/.ollama/models
```

（可选说明）后端 sidecar 构建脚本位于：

- `scripts/build-backend-sidecar-macos.sh`

复制完成后执行 Tauri 打包：

在 macOS 上，为了让 **干净机器** 也能直接启动 Ollama，你还需要把 Ollama 可执行文件作为 Tauri sidecar 一起打包：

```bash
make ollama-sidecar
```

并把后端 API（FastAPI）也打成 sidecar（否则桌面 UI 会出现 “Load failed”）：

```bash
make backend-sidecar
```

最后再执行打包：

```bash
cd frontend
npm run tauri:build
```

也可以一步到位：

```bash
make tauri-build-offline
```

应用首次启动时，如果用户机器的官方缓存目录为空，会自动把安装包内的 `resources/ollama_models/` 复制到官方目录。

注意：`frontend/src-tauri/resources/ollama_models/` 已被 gitignore，避免误提交超大文件。

## 3) 方案 B：离线模型扩展包（备选）

在一台已下载好模型的机器上，把模型目录打成压缩包：

```bash
./scripts/make-ollama-offline-pack.sh ~/.ollama/models
```

会生成：`dist/ollama-models-<os>-<arch>-YYYYMMDD.tar.gz`

用户安装应用后，把它解压到官方目录：

- macOS / Linux:
  ```bash
  mkdir -p ~/.ollama && tar -xzf dist/ollama-models-*.tar.gz -C ~/.ollama
  ```
- Windows（PowerShell 示例，路径请按实际文件调整）：
  ```powershell
  New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.ollama" | Out-Null
  tar -xzf .\ollama-models-*.tar.gz -C "$env:USERPROFILE\.ollama"
  ```

## 4) 把 Ollama（以及可选模型）打进 Tauri 安装包

本仓库已在 Tauri 配置中开启：

- `bundle.externalBin`: `binaries/ollama`
- `bundle.externalBin`: `binaries/pdc-backend`
- `bundle.resources`: `resources/**`

你需要把各平台的 `ollama` 可执行文件放到：

- `frontend/src-tauri/binaries/`

并按 Tauri sidecar 规范命名（不同平台/架构对应不同文件名）。

可选：如果你想把模型也打进安装包，放到：

- `frontend/src-tauri/resources/ollama_models/`

应用启动时会在 **官方缓存目录为空** 且 **未执行过 seed** 的情况下，把该目录复制到 `~/.ollama/models`（或 Windows 对应目录）。

注意：把模型打进安装包会导致安装包体积非常大、更新成本高。

## 5) 产物类型（是不是只有 DMG？）

不是。

- macOS：默认会生成 `.app` 与 `.dmg`
- Windows：通常会生成 `.msi`（以及/或 NSIS `.exe`，取决于 Tauri bundler 配置与平台能力）
- Linux：常见为 `.deb` / `.rpm` / AppImage（取决于安装的打包依赖）

注意：不同平台的安装包 **通常需要在对应平台上构建**（例如 Windows 的 `.msi` 一般在 Windows 上打）。
