# Testing Strategy - Memory Bank

## Structure des tests

Un seul fichier de tests d'intégration : `tests/rust_tests.rs`.
Pas de `tests/utils.rs` ni de `tests/test_data/` — les données de test sont inlinées ou générées via `tempfile`.

Les tests unitaires de certains modules sont directement dans `src/` (`#[cfg(test)] mod tests`).

---

## Modules de test dans `tests/rust_tests.rs`

### `utils_tests`
Teste les fonctions de `src/utils.rs` :
- `limit_quote_depth` : suppression des citations profondes
- `get_short_name` : extraction des initiales depuis `"John Doe <john@example.com>"` → `"JD"`
- `extract_emails`, `normalize_line_breaks`
- `hash_md5_prefix` : longueur et cohérence
- `sanitize_filename` : absence des caractères interdits
- `decode_imap_utf7` : `"INBOX"` inchangé, `"INBOX.&AOk-"` → `"INBOX.é"`
- `is_signature_image` : détection par nom, taille, content-type

### `config_tests`
Teste `SortConfig` et `Config` depuis `src/config.rs` :
- `SortConfig::default()` : présence des mots-clés par défaut
- `Config::validate()` sur liste vide : ok
- `SortConfig::is_whitelisted()` : correspondance exacte, domaine (`@company.com`), préfixe (`boss@`)
- `SortConfig` save/load JSON roundtrip via `tempfile`

### `settings_tests`
Teste la fusion `accounts.yaml` + `settings.yaml` :
- `Settings::default()` : tous les champs None/vide
- `Settings` save/load YAML roundtrip via `tempfile`
- `Settings::load()` sur chemin inexistant → `Settings::default()`
- `Config::load_with_settings()` : `export_directory` = `export_base_dir / account.name`
- `Config::load_with_settings()` : defaults (`quote_depth`, `collect_contacts`) appliqués
- `Config::load_with_settings()` : surcharge par compte (`folder_name`, `quote_depth`)
- `Config::load_with_settings()` sans settings.yaml → erreur de validation (`export_directory` vide)

### `email_export_tests`
Teste `src/email_export.rs` avec de vrais bytes RFC 2822 parsés par `mailparse` :
- `analyze_email_type()` : Direct (1 destinataire), Newsletter (sujet contient "Newsletter"), Group (2+ destinataires)
- `ContactsCollector::add()` : séparation direct/group
- `ExportStats::default()` : compteurs à zéro

### `fix_yaml_tests`
Teste `src/fix_yaml.rs` :
- `fix_complex_yaml_tags()` : suppression de `!!python/object:`, des ancres `&anchor`
- `extract_frontmatter()` : frontmatter valide, sans délimiteur fermant, sans délimiteur ouvrant

### `sort_emails_tests`
Teste `src/sort_emails.rs` :
- `Category::to_string()` : "delete", "summarize", "keep"
- `EmailSortType::to_string()` : "direct", "newsletter", "group"
- `EmailSorter::new()` : stats initialement à zéro

### `edge_case_tests`
Cas limites sur les utilitaires :
- Email vide, caractères spéciaux, Unicode dans le nom
- Email avec partie locale très longue → résultat ≤ 3 chars
- `normalize_line_breaks` : jamais plus de 2 sauts consécutifs
- `is_signature_image` : valeurs exactement aux seuils

### `network_tests`
Teste `src/network.rs` :
- `NetworkConfig::default()` : `max_retries=3`, `connect_timeout=30s`, `read_timeout=60s`
- `ProgressIndicator::new()` et `update()` / `inc()` : pas de panique

---

## Pattern de test pour la config (avec `tempfile`)

```rust
#[test]
fn test_config_merge_defaults_applied() {
    let temp = TempDir::new().unwrap();

    let accounts_yaml = "accounts:\n  - name: TestAccount\n    server: imap.example.com\n    port: 993\n    username: user@example.com\n";
    std::fs::write(temp.path().join("accounts.yaml"), accounts_yaml).unwrap();

    let settings_yaml = "export_base_dir: /tmp/emails\ndefaults:\n  quote_depth: 3\n  collect_contacts: true\n";
    std::fs::write(temp.path().join("settings.yaml"), settings_yaml).unwrap();

    let config = Config::load_with_settings(
        &temp.path().join("accounts.yaml"),
        &temp.path().join("settings.yaml"),
    ).unwrap();
    assert_eq!(config.accounts[0].quote_depth, 3);
    assert!(config.accounts[0].collect_contacts);
}
```

---

## Lancer les tests

```bash
# Tous les tests
cargo test

# Un module spécifique
cargo test settings_tests

# Un test précis
cargo test test_config_merge_defaults_applied

# Avec sortie stdout
cargo test -- --nocapture
```

---

## Couverture actuelle

89 tests, 0 échec. Modules non couverts par les tests :
- `thunderbird.rs` : nécessite Thunderbird installé, testé manuellement
- `tray.rs` / `tray_actions.rs` : nécessite un event loop GUI, testé manuellement
- `email_export.rs` → `ImapExporter` : nécessite un serveur IMAP réel
