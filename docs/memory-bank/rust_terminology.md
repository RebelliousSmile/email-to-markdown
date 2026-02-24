# Terminologie Rust - Memory Bank

## Concepts Fondamentaux de Rust

### Modules et Organisation du Code

#### Modules (`mod`)
- **Définition** : Unités d'organisation de base en Rust
- **Déclaration** : `mod nom_module;` ou `pub mod nom_module;`
- **Fichiers** : Correspondent à des fichiers `.rs` ou dossiers avec `mod.rs`
- **Exemple** :
  ```rust
  // Dans lib.rs
  pub mod email_export;
  pub mod config;
  pub mod thunderbird;
  #[cfg(feature = "tray")]
  pub mod tray;
  ```

#### Feature flags
- **Définition** : Compilent conditionnellement des modules ou dépendances
- **Déclaration** : dans `Cargo.toml` sous `[features]`
- **Usage** : `#[cfg(feature = "tray")]` sur le code concerné
- **Build** : `cargo build --features tray`
- **Exemple dans ce projet** : le module `tray` et ses dépendances (`tao`, `tray-icon`, `rfd`, `image`) ne sont compilés que si `--features tray` est passé

#### Crates
- **Définition** : Unités de compilation et de distribution
- **Types** :
  - **Bibliothèque** : `lib.rs` (crate de type library)
  - **Binaire** : `main.rs` (crate exécutable)
- **Écosystème** : Publiées et partagées via [crates.io](https://crates.io)

#### Traits
- **Définition** : Similaires aux interfaces, définissent des comportements
- **Exemple dans ce projet** : `serde::Serialize` / `serde::Deserialize` sur `Account`, `Settings`, `EmailFrontmatter`, etc.
- **`Default`** : trait implémenté sur `Settings`, `SortConfig`, `ExportStats` pour `::default()`

#### Pattern Matching
- **Utilisation** : Gestion des variantes avec `match`
- **Exemple dans ce projet** :
  ```rust
  match result {
      ActionResult::Success(title, m) => { /* notification */ }
      ActionResult::Imported(m)       => { /* rebuild menu */ }
      ActionResult::Error(m)          => { /* error dialog */ }
  }
  ```

### Gestion de la Visibilité

#### `pub` (Public)
- **Utilisation** : Rendre des éléments accessibles en dehors du module
- **Exemple** :
  ```rust
  pub struct Account {    // Accessible depuis d'autres modules
      pub name: String,   // Champ public
      // password: Option<String> -- marqué #[serde(skip)] mais pub
  }
  ```

#### `use` (Importation)
- **Utilisation** : Importer des éléments dans la portée actuelle
- **Exemple** :
  ```rust
  use crate::config::{Config, Settings, app_config_dir};
  use anyhow::{Context, Result};
  ```

### Gestion des Erreurs

#### `Result<T, E>`
- **Définition** : Type pour les opérations pouvant échouer
- **Dans ce projet** : deux approches coexistent —
  - `Result<T, ConfigError>` (thiserror) pour `config.rs`
  - `anyhow::Result<T>` pour `email_export.rs`, `thunderbird.rs`, `tray_actions.rs`

#### `Option<T>`
- **Définition** : Type pour les valeurs optionnelles
- **Exemple dans ce projet** : tous les champs de `AccountBehavior` sont `Option<T>` pour permettre la fusion avec les defaults

#### `?` (Opérateur de propagation)
- **Utilisation** : Propager les erreurs de manière concise
- **Exemple** :
  ```rust
  let config = Config::load(&accounts_yaml_path())
      .context("Failed to load configuration")?;
  ```

### Propriété et Emprunt

#### Ownership (Propriété)
- **Règle** : Chaque valeur a un propriétaire unique
- **`.clone()`** : utilisé dans ce projet quand une valeur doit être transférée dans un thread tout en restant disponible dans le thread principal

#### Borrowing (Emprunt)
- **Références** :
  - `&T` : Référence immutable (lecture seule)
  - `&mut T` : Référence mutable (lecture/écriture)

#### Threads et `move`
- **`thread::spawn(move || { ... })`** : capture les variables par valeur dans le thread
- **Exemple dans ce projet** : toutes les actions tray (`action_export`, `action_sort`, etc.) s'exécutent dans des threads séparés pour ne pas bloquer l'event loop UI

### Types et Structures

#### Structs
- **Exemple** :
  ```rust
  pub struct Account {
      pub name: String,
      pub server: String,
      pub port: u16,
      pub username: String,
      #[serde(skip)]
      pub password: Option<String>,
      pub export_directory: String,
      // ...
  }
  ```

#### Enums
- **Exemple** :
  ```rust
  pub enum EmailType { Direct, Group, Newsletter, MailingList, Unknown }
  pub enum ActionResult { Success(String, String), Imported(String), Error(String) }
  pub enum Category { Delete, Summarize, Keep }
  ```

#### `#[derive(...)]`
- **Commun dans ce projet** : `Debug`, `Clone`, `Serialize`, `Deserialize`, `Default`
- **`#[serde(skip_serializing_if = "Option::is_none")]`** : omet les champs None dans le YAML généré (utilisé dans `AccountBehavior`)
- **`#[serde(skip)]`** : exclut un champ de la sérialisation/désérialisation (utilisé sur `Account::password`)

### Canaux de communication entre threads

#### `mpsc` (multi-producer, single-consumer)
- **Utilisé dans le tray** : les threads d'action envoient leur résultat vers l'event loop via un `Sender<ActionResult>`
- **Exemple** :
  ```rust
  let (result_sender, result_receiver) = mpsc::channel::<ActionResult>();
  // Dans le thread :
  let _ = result_sender.send(ActionResult::Success(...));
  // Dans l'event loop :
  if let Ok(result) = result_receiver.try_recv() { ... }
  ```

---

## Terminologie Spécifique au Projet

### Modules du Projet
- **`config`** : Configuration — chargement, fusion, validation
- **`email_export`** : Export IMAP → Markdown
- **`thunderbird`** : Import depuis profils Thunderbird
- **`fix_yaml`** : Correction frontmatter YAML Python-spécifique
- **`sort_emails`** : Catégorisation des emails exportés
- **`network`** : Retry, progress indicator
- **`utils`** : Fonctions utilitaires partagées
- **`tray`** *(feature `tray`)* : Event loop et icône système
- **`tray_actions`** *(feature `tray`)* : Handlers des actions du menu

### Types Personnalisés Principaux

| Type | Module | Rôle |
|------|--------|------|
| `RawAccount` | `config` | Données de connexion lues depuis `accounts.yaml` |
| `AccountBehavior` | `config` | Surcharges de comportement (champs `Option<T>`) |
| `Settings` | `config` | Contenu de `settings.yaml` |
| `Account` | `config` | Struct résolu après fusion (jamais écrit sur disque) |
| `Config` | `config` | Conteneur de `Vec<Account>` |
| `SortConfig` | `config` | Règles de tri depuis `sort_config.json` |
| `ConfigError` | `config` | Seul type d'erreur custom du projet |
| `EmailFrontmatter` | `email_export` | Métadonnées YAML d'un email |
| `EmailType` | `email_export` | Direct / Group / Newsletter / MailingList / Unknown |
| `ExportStats` | `email_export` | Compteurs exported/skipped/errors |
| `Category` | `sort_emails` | Delete / Summarize / Keep |
| `ActionResult` | `tray_actions` | Success(title, msg) / Imported(msg) / Error(msg) |

### Erreurs

- **`ConfigError`** (thiserror) : seul type d'erreur custom — `FileReadError`, `YamlParseError`, `AccountNotFound`, `NoPassword`, `ValidationError`
- Tous les autres modules utilisent **`anyhow::Result`** avec `.context("...")`
- Il n'existe **pas** de `ExportError` ni de `ThunderbirdError` dans le code

---

## Ressources

- [The Rust Programming Language](https://doc.rust-lang.org/book/)
- [Rust by Example](https://doc.rust-lang.org/rust-by-example/)
- [anyhow](https://docs.rs/anyhow) / [thiserror](https://docs.rs/thiserror)
- [serde](https://serde.rs)
