# Dev Tools Encyclopedia
- Algorithmes classiques: Informatique - Règles finies pour résoudre un problème. Exemples: Tri (quick, merge, heap), recherche (DFS, BFS, A*). Applications: Programation, optimisation.
- Langages algorithmiques: Informatique - Paradigmes et formalismes. Exemples: Python, C++, Rust, Lisp, Prolog. Applications: Dev logiciel, IA, systèmes.
- Patrons de conception (logiciels): Software design patterns - Solutions génériques réutilisables. Exemples: Singleton, Factory, Observer, MVC. Applications: Architecture logicielle.
- Automatisation Dev: Ingénierie logicielle - Pipelines & CI/CD. Exemples: GitHub Actions, Jenkins, Docker. Applications: DevOps, déploiement.
- Langages spécialisés IA: Programation IA - DSL et frameworks IA. Exemples: PyTorch, TensorFlow, JAX, Julia. Applications: Dév IA avancée.
- Additional: Kubernetes, Terraform, Ansible. Applications: Cloud orchestration, infrastructure as code.

## VS Code Autocomplete Setup Guide (macOS 11.7.10 + Xiaomi Pad 7 Sync)

### Goal (short)
Get fast, reliable, secure autocomplete (IntelliSense + LSP + AI via Codeium) in VS Code on macOS 11.7.10, and be able to send/sync the project to your Xiaomi Pad 7 (device name set as Xiaomi Pad 7) using Xiaomi Share where applicable, plus robust alternatives (Snapdrop / SMB / USB / Git).

### Recommended Extensions
- Codeium — AI completions
- Pylance (ms-python.vscode-pylance) — Python LSP
- ms-python.python — Python tooling
- Rust Analyzer (rust-lang.rust-analyzer) — Rust LSP
- Go (golang.Go) — Go tooling
- ESLint (dbaeumer.vscode-eslint) — JS linting and assist
- C/C++ (ms-vscode.cpptools) — C/C++ LSP
- GitLens (eamodio.gitlens) — Git insights
- vscode-snippets — Language snippet packs
- Remote - SSH / Remote - Tunnels — For remote editing

### Minimal settings.json
```json
{
  "editor.suggestOnTriggerCharacters": true,
  "editor.quickSuggestions": { "other": true, "comments": false, "strings": false },
  "editor.acceptSuggestionOnEnter": "on",
  "editor.tabCompletion": "on",
  "editor.parameterHints.enabled": true,
  "editor.wordBasedSuggestions": true,
  "editor.snippetSuggestions": "top",
  "files.exclude": { "**/.git": true, "**/.venv": true, "**/__pycache__": true },
  "files.watcherExclude": { "**/.git/**": true, "**/node_modules/**": true },
  "git.autofetch": true,
  "git.confirmSync": false,
  "typescript.tsserver.maxTsServerMemory": 4096,
  "typescript.updateImportsOnFileMove.enabled": "always",
  "codeium.enable": true,
  "codeium.completions.enabled": true,
  "codeium.completions.acceptOnEnter": true,
  "codeium.suggestionInline": true,
  "codeium.privacy.localMode": false,
  "telemetry.enableTelemetry": false,
  "telemetry.enableCrashReporter": false
}
```

### Architecture of Completions
Components: Editor UI, Extension Host, Language Server (LSP), AI Provider (Codeium), Local Index, Cache & Ranking, Network.

Flow: Trigger → Context Collection → LSP Query → AI Query → Merge Responses → Ranking → Display → Accept.

### Transfer/Sync to Xiaomi Pad 7
- Enable Xiaomi Share on Pad, set name to Xiaomi Pad 7.
- Alternatives: Snapdrop (recommended), SMB, USB, GitHub/Git.
- Quick Snapdrop: Zip project on Mac, open snapdrop.net, drag to Pad card.

### Using VS Code on Pad
- Run code-server via Termux, open in browser.
- Or use VS Code Remote Tunnel from Mac.

### Workflows
1. Edit on Mac, sync via Git/Snapdrop.
2. Remote tunnel for continuous editing.
3. Offline editing with code-server.

### Useful Commands
- Compress: `zip -r my-project.zip .`
- Push to Git: `git push -u origin main`
- Start tunnel: `code tunnel --start`
- Start code-server: `code-server`