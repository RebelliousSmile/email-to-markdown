# Cross-Platform Support

## Configuration — chemins système

La crate `dirs` (`dirs::config_dir()`) détermine automatiquement le répertoire de config :

| Plateforme | Chemin                                              |
|------------|-----------------------------------------------------|
| Windows    | `%APPDATA%\email-to-markdown\`                      |
| macOS      | `~/Library/Application Support/email-to-markdown/` |
| Linux      | `~/.config/email-to-markdown/`                      |

Fichiers dans ce répertoire : `accounts.yaml`, `settings.yaml`, `.env`, `sort_config.json`.

Les chemins dans les valeurs YAML sont normalisés : `\` → `/` (voir `merge_account()` dans `config.rs`).

## Thunderbird — chemins des profils

Détection automatique dans `thunderbird.rs` via `get_thunderbird_profiles_dir()` :

| Plateforme | Chemin                                                   |
|------------|----------------------------------------------------------|
| Windows    | `%APPDATA%\Thunderbird\Profiles\`                        |
| macOS      | `~/Library/Thunderbird/Profiles/`                        |
| Linux      | `~/.thunderbird/`                                        |

L'extraction des mots de passe (`extract_passwords`) charge `nss3.dll` / `libnss3.so` via `libloading`. Thunderbird doit être fermé.

## Build

```bash
# Toutes plateformes
cargo build --release

# Avec le tray (Windows/macOS/Linux)
cargo build --release --features tray
```

**Linux** — dépendances système requises :
```bash
sudo apt-get install build-essential pkg-config libssl-dev
```

**Linux statique** (musl) :
```bash
rustup target add x86_64-unknown-linux-musl
cargo build --release --target x86_64-unknown-linux-musl
```

## Points d'attention cross-platform

- **Séparateurs de chemin** : toujours utiliser `PathBuf` / `Path`, jamais des littéraux `\` ou `/`
- **Variables d'environnement** : `std::env::var()` — fonctionne identiquement sur toutes les plateformes
- **Noms de fichiers** : `sanitize_filename()` dans `utils.rs` traite les caractères interdits Windows (`< > : " / \ | ? *`)
- **Case-sensitivity** : les noms de dossiers IMAP et de comptes sont comparés en `eq_ignore_ascii_case`
- **Tray** : `tao` + `tray-icon` supportent Windows, macOS, Linux (X11/Wayland)
