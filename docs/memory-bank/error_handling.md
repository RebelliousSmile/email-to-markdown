# Error Handling - Memory Bank

## Stratégie globale

Deux approches coexistent selon le module :

- **`thiserror`** : pour les erreurs de domaine exportées publiquement (`config.rs`)
- **`anyhow`** : pour les erreurs opérationnelles où le contexte est plus important que le type (`email_export.rs`, `thunderbird.rs`, `tray_actions.rs`, `main.rs`)

---

## `config.rs` — `ConfigError` (thiserror)

Seul type d'erreur custom du projet. Exporté publiquement.

```rust
#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("Failed to read config file: {0}")]
    FileReadError(#[from] std::io::Error),

    #[error("Failed to parse YAML: {0}")]
    YamlParseError(#[from] serde_yaml::Error),

    #[error("Account not found: {0}")]
    AccountNotFound(String),

    #[error("No password found for account: {0}")]
    NoPassword(String),

    #[error("Configuration validation error: {0}")]
    ValidationError(String),
}
```

`FileReadError` et `YamlParseError` utilisent `#[from]` pour la conversion automatique via `?`.

---

## `email_export.rs` — `anyhow::Result`

Pas de type d'erreur custom. Toutes les fonctions retournent `anyhow::Result<T>`.
Le contexte est ajouté avec `.context("message")` :

```rust
// Exemple réel dans tray_actions.rs
let config = Config::load(&config::accounts_yaml_path())
    .context("Failed to load configuration")?;

exporter.connect()
    .context("Failed to connect to IMAP server")?;
```

---

## `thunderbird.rs` — `anyhow::Result`

Même approche. Pas de `ThunderbirdError` — toutes les fonctions retournent `anyhow::Result<T>`.
Exemple :

```rust
pub fn list_profiles() -> Result<Vec<ThunderbirdProfile>> {
    let profiles_dir = get_thunderbird_profiles_dir()
        .context("Could not determine Thunderbird profiles directory")?;
    // ...
}
```

---

## `tray_actions.rs` — `ActionResult`

Les actions du tray ne propagent pas d'erreurs vers l'event loop — elles les convertissent en `ActionResult::Error(String)` pour affichage via `rfd::MessageDialog` :

```rust
let action_result = match result {
    Ok(message) => ActionResult::Success("Export terminé".to_string(), message),
    Err(e)      => ActionResult::Error(format!("Export error: {}", e)),
};
```

---

## Validation de configuration

La validation est centralisée dans `Config::validate()`. Elle est appelée automatiquement à la fin de `Config::load_with_settings()`. Les règles :

| Champ              | Règle                             | Erreur                    |
|--------------------|-----------------------------------|---------------------------|
| `name`             | non vide                          | `ValidationError`         |
| `server`           | non vide                          | `ValidationError`         |
| `username`         | non vide                          | `ValidationError`         |
| `export_directory` | non vide (dépend de settings.yaml)| `ValidationError`         |
| `port`             | ≠ 0                               | `ValidationError`         |

---

## Ce qui n'existe pas

- Pas de `ExportError` custom dans `email_export.rs`
- Pas de `ThunderbirdError` custom dans `thunderbird.rs`
- Pas de système de codes d'erreur numériques
- Pas de logging structuré — les erreurs sont affichées via `eprintln!` ou `rfd::MessageDialog`
