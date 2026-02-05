# Email to Markdown Exporter

Un script Python pour exporter vos emails depuis des comptes IMAP vers des fichiers Markdown avec frontmatter YAML.

## Fonctionnalités

- ✅ Export des emails depuis plusieurs comptes IMAP
- ✅ Conversion au format Markdown avec métadonnées YAML
- ✅ Gestion des pièces jointes avec hachage des noms de fichiers
- ✅ Support des dossiers imbriqués
- ✅ Filtrage des dossiers indésirables (spam, corbeille, etc.)
- ✅ Préservation de la structure des dossiers

## Prérequis

- Python 3.7+
- Comptes email avec accès IMAP activé
- Pour Gmail : mot de passe spécifique à l'application (si 2FA activé)

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/votre-utilisateur/email-to-markdown.git
cd email-to-markdown
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Configurer les comptes email

#### a. Créer le fichier `accounts.yaml`

Copiez et modifiez le fichier d'exemple :

```bash
cp accounts.yaml.example accounts.yaml
```

Exemple de configuration :

```yaml
accounts:
  - name: "Gmail"
    server: "imap.gmail.com"
    port: 993
    username: "votre.email@gmail.com"
    export_directory: "/chemin/vers/export/Gmail"
    ignored_folders:
      - "[Gmail]/Spam"
      - "[Gmail]/Trash"
      - "[Gmail]/Drafts"

  - name: "MonAutreCompte"
    server: "imap.votredomaine.com"
    port: 993
    username: "votre@email.com"
    export_directory: "/chemin/vers/export/MonAutreCompte"
    ignored_folders:
      - "Spam"
      - "Trash"
```

#### b. Configurer les mots de passe

Créez un fichier `.env` :

```bash
cp .env.example .env
```

Ajoutez vos mots de passe (un par compte) :

```env
GMAIL_PASSWORD="votre_mot_de_passe_ou_app_password"
MONAUTRECOMPTE_PASSWORD="votre_autre_mot_de_passe"
```

**Pour Gmail avec 2FA** : Vous devez créer un [mot de passe spécifique à l'application](https://support.google.com/accounts/answer/185833)

### 4. Exécuter l'export

```bash
python export_emails.py
```

## Configuration avancée

### Options disponibles

- **`delete_after_export`** : Supprime les emails après export (désactivé par défaut)
- **`ignored_folders`** : Liste des dossiers à ignorer pendant l'export

### Structure des fichiers exportés

```
export_directory/
├── INBOX/
│   ├── email_1.md
│   ├── email_2.md
│   └── attachments/
│       ├── 1_abc123_fichier.pdf
│       └── 2_def456_image.jpg
└── Sent/
    ├── email_3.md
    └── attachments/
        └── 3_ghi789_document.docx
```

### Format des fichiers Markdown

Chaque email est exporté avec un en-tête YAML :

```markdown
---
from: expéditeur@domaine.com
to: destinataire@domaine.com
date: 2023-01-01T12:00:00+00:00
subject: Sujet de l'email
tags:
  - INBOX
attachments:
  - attachments/1_abc123_fichier.pdf
---

Corps de l'email en texte brut...
```

## Dépannage

### Erreurs courantes

**Gmail - Mot de passe spécifique requis**
```
❌ Error for Gmail: b'[ALERT] Application-specific password required
```

**Solution** : Créez un [mot de passe spécifique à l'application](https://support.google.com/accounts/answer/185833) et mettez à jour votre fichier `.env`.

**LaContreVoie - Boucle infinie sur "."**
```
📁 Exporting . → /chemin/vers/export/.
⚠️ Unable to select .
```

**Solution** : Mettez à jour le script avec la dernière version qui filtre les noms de dossiers invalides.

### Journalisation

Le script affiche les progrès et erreurs en temps réel :
- 📧 : Traitement d'un compte
- 📁 : Export d'un dossier
- ⚠️ : Avertissements
- ❌ : Erreurs
- ✅ : Succès

## Contribuer

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## Licence

[MIT License](LICENSE)

## Auteur

Créé avec ❤️ par [Votre Nom](https://github.com/votre-utilisateur)