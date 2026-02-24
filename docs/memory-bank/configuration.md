# Configuration - Memory Bank

## Overview

La configuration est répartie en trois fichiers dans le répertoire système de l'application.
Le chemin est déterminé automatiquement par la crate `dirs` :

| Plateforme | Chemin                                              |
|------------|-----------------------------------------------------|
| Windows    | `%APPDATA%\email-to-markdown\`                      |
| macOS      | `~/Library/Application Support/email-to-markdown/` |
| Linux      | `~/.config/email-to-markdown/`                      |

La fonction `app_config_dir()` dans `config.rs` retourne ce chemin.

---

## Fichiers de configuration

### `accounts.yaml` — Connexion IMAP

Généré automatiquement par `import` (ou `import --extract-passwords`).
Contient **uniquement** les informations de connexion, jamais les paramètres de comportement.

```yaml
accounts:
  - name: Gmail
    server: imap.gmail.com
    port: 993
    username: user@gmail.com
    ignored_folders:
      - "[Gmail]/Spam"
      - "[Gmail]/Trash"
      - "[Gmail]/All Mail"
      - "[Gmail]/Drafts"

  - name: Outlook
    server: outlook.office365.com
    port: 993
    username: user@outlook.com
    ignored_folders:
      - Junk
      - Deleted Items
```

**Champs obligatoires** : `name`, `server`, `port`, `username`
**Champs optionnels** : `ignored_folders` (défaut : liste vide)

---

### `settings.yaml` — Comportement de l'application

Éditable via **Paramètres…** dans le tray ou directement.
Contient le répertoire d'export et les paramètres de comportement (globaux et par compte).

```yaml
# Répertoire racine — chaque compte crée un sous-dossier automatiquement
export_base_dir: C:/Users/VotreNom/Documents/Emails

# Comportement par défaut pour tous les comptes
defaults:
  quote_depth: 1              # Profondeur max des citations à conserver
  skip_existing: true         # Ne pas ré-exporter les emails déjà présents
  collect_contacts: false     # Générer un CSV des contacts
  skip_signature_images: true # Ignorer les images de signature/logo
  delete_after_export: false  # Supprimer du serveur après export

# Surcharges par compte (optionnel)
# accounts:
#   Gmail:
#     folder_name: gmail        # Nom du sous-dossier (défaut : nom du compte)
#     delete_after_export: false
#   Outlook:
#     collect_contacts: true
```

**`export_directory` résolu** = `export_base_dir` / `folder_name` (ou `account.name` si non défini)

---

### `.env` — Mots de passe

```bash
GMAIL_PASSWORD=votre_mot_de_passe
GMAIL_APPLICATION_PASSWORD=xxxx-xxxx-xxxx-xxxx  # prioritaire sur _PASSWORD

OUTLOOK_PASSWORD=votre_mot_de_passe
```

Convention : `{NOM_DU_COMPTE_EN_MAJUSCULES}_PASSWORD`
Les caractères `@`, `.`, `-` dans le nom sont remplacés par `_`.

---

## Structures Rust (`config.rs`)

### `RawAccount`
Désérialisé depuis `accounts.yaml`. Connexion uniquement.

### `AccountBehavior`
Tous les champs sont `Option<T>`. Utilisé à la fois dans `Settings::defaults` et `Settings::accounts`.

### `Settings`
Chargé depuis `settings.yaml`. Contient `export_base_dir`, `defaults: AccountBehavior`, `accounts: HashMap<String, AccountBehavior>`.

### `Account`
Struct résolu après fusion `RawAccount` + `Settings`. N'est jamais réécrit sur disque.
`export_directory` est calculé lors de la fusion.

### `Config`
Conteneur de `Vec<Account>`. Chargé via `Config::load()` (chemin système) ou `Config::load_with_settings()` (pour les tests).

---

## Chargement

1. `Config::load(accounts_path)` appelle `load_with_settings(accounts_path, &settings_path())`
2. Lecture de `accounts.yaml` → `Vec<RawAccount>`
3. Lecture de `settings.yaml` → `Settings` (ou `Settings::default()` si absent)
4. Fusion via `merge_account()` pour chaque compte
5. Injection des mots de passe depuis les variables d'environnement
6. Validation (`Config::validate()`)

---

## Validation

- `name` non vide
- `server` non vide
- `username` non vide
- `export_directory` non vide (échoue si `export_base_dir` n'est pas défini dans settings.yaml)
- `port` ≠ 0

---

## Tests

Voir `mod settings_tests` dans `tests/rust_tests.rs` :
- `test_settings_save_load_roundtrip`
- `test_config_merge_export_dir_from_base`
- `test_config_merge_defaults_applied`
- `test_config_merge_per_account_overrides_folder_name`
- `test_config_merge_no_settings_uses_hardcoded_defaults`
