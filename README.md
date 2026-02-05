# Email to Markdown Exporter

Un script Python pour exporter vos emails depuis des comptes IMAP vers des fichiers Markdown avec frontmatter YAML.

## Fonctionnalités

- ✅ Export des emails depuis plusieurs comptes IMAP
- ✅ Conversion au format Markdown avec métadonnées YAML
- ✅ Gestion des pièces jointes avec hachage des noms de fichiers
- ✅ Support des dossiers imbriqués
- ✅ Filtrage des dossiers indésirables (spam, corbeille, etc.)
- ✅ Préservation de la structure des dossiers
- ✅ Structure des pièces jointes reflétant l'arborescence des emails
- ✅ Contrôle de la profondeur des citations pour réduire le contenu redondant

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
- **`quote_depth`** : Profondeur maximale des citations à conserver (par défaut: 1)
- **`skip_existing`** : Ignore les emails déjà exportés (activé par défaut)

### Exemple de configuration avancée

```yaml
accounts:
  - name: "Gmail"
    server: "imap.gmail.com"
    port: 993
    username: "votre.email@gmail.com"
    export_directory: "/chemin/vers/export/Gmail"
    delete_after_export: false
    quote_depth: 1
    skip_existing: true
    ignored_folders:
      - "[Gmail]/Spam"
      - "[Gmail]/Trash"
      - "[Gmail]/Drafts"
```

### Structure des fichiers exportés

```
export_directory/
├── INBOX/
│   ├── email_1.md
│   ├── email_2.md
│   └── fonctionnement/
│       └── opale/
│           ├── email_3.md
│           └── attachments/
│               └── email_3_abc123_fichier.pdf
├── Sent/
│   ├── email_4.md
│   └── attachments/
│       └── email_4_def456_document.docx
└── attachments/
    ├── 1_abc123_fichier.pdf
    └── 2_def456_image.jpg
```

### Gestion des citations

Le script permet de contrôler la profondeur des citations dans les emails exportés pour éviter le contenu redondant. Par exemple, avec `quote_depth: 3`, seules les citations jusqu'au 3ème niveau seront conservées :

```
> Premier niveau de citation (conservé)
>> Deuxième niveau de citation (conservé)
>>> Troisième niveau de citation (conservé)
>>>> Quatrième niveau de citation (supprimé)
```

### Éviter les doublons

Le script détecte automatiquement les emails déjà exportés pour éviter les doublons. Cette fonctionnalité est activée par défaut avec l'option `skip_existing: true`.

**Fonctionnement** :
- Le script compare les emails à exporter avec les fichiers existants
- Un email est considéré comme déjà exporté s'il existe un fichier avec le même nom de base (date + expéditeur + destinataire)
- Les emails déjà exportés sont ignorés et un message est affiché : `⏭️  Email already exported, skipping: ...`

**Avantages** :
- Évite la duplication des fichiers
- Économise du temps et des ressources
- Permet des exécutions multiples sans risque de doublons

**Désactiver la détection** :
```yaml
skip_existing: false  # Pour forcer la réexportation de tous les emails
```

### Structure des pièces jointes

Les pièces jointes sont maintenant organisées dans une structure de dossiers qui reflète exactement l'arborescence des emails d'origine. Par exemple :

- Un email situé dans `INBOX/fonctionnement/opale/` aura ses pièces jointes dans `attachments/fonctionnement/opale/`
- Un email dans `Sent/` aura ses pièces jointes dans `attachments/Sent/`

Cette organisation permet de :
- Maintenir une correspondance claire entre les emails et leurs pièces jointes
- Faciliter la navigation et la gestion des fichiers
- Conserver le contexte original des pièces jointes

### Format des fichiers Markdown

Chaque email est exporté avec un en-tête YAML :

```markdown
---
from: expéditeur@domaine.com
to: destinataire@domaine.com
date: 2023-01-01T12:00:00+00:00
subject: Sujet de l'email
tags:
  - INBOX/fonctionnement/opale
attachments:
  - attachments/fonctionnement/opale/email_2023-01-01_EXP_to_DES_abc123_fichier.pdf
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

Créé avec ❤️ par [François-Xavier Guillois](https://github.com/RebelliousSmile)