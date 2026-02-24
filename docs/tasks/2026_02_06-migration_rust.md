# Instruction: Migration du projet email-to-markdown vers Rust

## Feature

- **Summary**: Migrer le projet email-to-markdown de Python vers Rust pour améliorer les performances, la sécurité et la portabilité. Créer un exécutable autonome qui peut être utilisé sur différentes plateformes sans dépendances externes.
- **Stack**: `Rust (stable)`, `Cargo`, `Python (pour les tests initiaux)`
- **Branch name**: `migration-rust`

## Existing files

- @archive/python_src/export_emails.py
- @archive/python_src/fix_email_yaml.py
- @archive/python_src/sort_emails.py
- @archive/python_tests/test_basic.py
- @archive/python_tests/test_edge_cases.py

### New file to create

- src/main.rs (point d'entrée principal)
- src/email_export.rs (logique d'export des emails)
- src/fix_yaml.rs (logique de correction des caractères spéciaux)
- src/sort_emails.rs (logique de tri des emails)
- Cargo.toml (fichier de configuration du projet Rust)
- tests/rust_tests.rs (tests unitaires en Rust)

## Implementation phases

### Phase 1: Configuration du projet Rust

> Initialiser un nouveau projet Rust et configurer les dépendances.

1. Créer un nouveau projet Rust avec `cargo new email-to-markdown`.
2. Configurer le fichier `Cargo.toml` avec les dépendances nécessaires (ex: `serde` pour la gestion des fichiers YAML, `regex` pour le traitement des caractères spéciaux).
3. Structurer le projet avec des modules pour chaque fonctionnalité (export, correction, tri).

### Phase 2: Migration de la logique d'export des emails

> Migrer la logique d'export des emails de Python vers Rust.

1. Analyser le code Python dans `archive/python_src/export_emails.py`.
2. Réécrire la logique en Rust dans `src/email_export.rs`.
3. Assurer la compatibilité avec les formats de fichiers existants (ex: CSV, Markdown).
4. Tester la fonctionnalité avec des données d'exemple.

### Phase 3: Migration de la logique de correction des caractères spéciaux

> Migrer la logique de correction des caractères spéciaux de Python vers Rust.

1. Analyser le code Python dans `archive/python_src/fix_email_yaml.py`.
2. Réécrire la logique en Rust dans `src/fix_yaml.rs`.
3. Utiliser des bibliothèques Rust pour la gestion des encodages (ex: `encoding_rs`).
4. Tester la fonctionnalité avec des fichiers YAML contenant des caractères spéciaux.

### Phase 4: Migration de la logique de tri des emails

> Migrer la logique de tri des emails de Python vers Rust.

1. Analyser le code Python dans `archive/python_src/sort_emails.py`.
2. Réécrire la logique en Rust dans `src/sort_emails.rs`.
3. Implémenter des algorithmes de tri efficaces en Rust.
4. Tester la fonctionnalité avec des jeux de données variés.

### Phase 5: Intégration et tests

> Intégrer les modules et écrire des tests unitaires.

1. Créer un point d'entrée principal dans `src/main.rs` pour orchestrer les fonctionnalités.
2. Écrire des tests unitaires dans `tests/rust_tests.rs` pour valider chaque module.
3. Tester l'exécutable final sur différentes plateformes (Windows, Linux, macOS).

### Phase 6: Documentation et déploiement

> Documenter le projet et préparer le déploiement.

1. Rédiger une documentation pour expliquer comment utiliser l'exécutable Rust.
2. Créer un script de déploiement pour générer des exécutables pour différentes plateformes.
3. Mettre à jour le README.md pour refléter les changements.

## Reviewed implementation

- [x] Phase 1: Configuration du projet Rust
- [x] Phase 2: Migration de la logique d'export des emails
- [x] Phase 3: Migration de la logique de correction des caractères spéciaux
- [x] Phase 4: Migration de la logique de tri des emails
- [x] Phase 5: Intégration et tests
- [x] Phase 6: Documentation et déploiement

## Validation flow

1. Cloner le dépôt et naviguer vers le répertoire du projet.
2. Compiler le projet avec `cargo build --release`.
3. Exécuter l'exécutable généré avec `./target/release/email-to-markdown`.
4. Vérifier que les fonctionnalités d'export, de correction et de tri fonctionnent comme attendu.
5. Tester l'exécutable sur différentes plateformes pour s'assurer de la portabilité.

## Estimations

- **Confidence**: 9/10 (Rust est bien adapté pour ce type de migration, et les bibliothèques nécessaires sont matures).
- **Time to implement**: 30-50 heures (selon la complexité des fonctionnalités et des tests).