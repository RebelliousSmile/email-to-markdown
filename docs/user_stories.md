# Email to Markdown - User Stories

## Epic: Export et gestion des emails personnels

---

## "Configuration des comptes"

**As a** utilisateur
**I want** configurer mes comptes email soit automatiquement depuis Thunderbird, soit manuellement
**So that** je puisse exporter mes emails sans avoir a rechercher les parametres IMAP

- Acceptance Criteria (import Thunderbird):
  - [x] Given: Thunderbird est installe sur ma machine
  - [x] When: je lance `email-to-markdown import --extract-passwords`
  - [x] Then: le programme detecte automatiquement mon profil Thunderbird par defaut
  - [x] And: genere `accounts.yaml` (connexion uniquement) dans le repertoire systeme (`%APPDATA%\email-to-markdown\` sur Windows)
  - [x] And: ecrit les mots de passe dans `.env` dans le meme repertoire

- Acceptance Criteria (manuel):
  - [x] Given: je n'ai pas Thunderbird ou je prefere configurer manuellement
  - [x] When: je cree `accounts.yaml` dans le repertoire systeme
  - [x] Then: je peux specifier serveur, port, username, dossiers ignores
  - [x] And: les parametres de comportement (quote_depth, skip_existing, etc.) se configurent dans `settings.yaml`
  - [x] And: les mots de passe sont stockes separement dans `.env`

---

## "Choix du repertoire d'export"

**As a** utilisateur
**I want** definir une fois le repertoire racine ou seront exportes tous mes emails
**So that** chaque compte cree automatiquement son propre sous-dossier sans configuration repetitive

- Acceptance Criteria (via tray):
  - [x] Given: l'application tourne dans la barre systeme
  - [x] When: je clique sur "Choisir repertoire d'export…"
  - [x] Then: un selecteur de dossier s'ouvre
  - [x] And: le chemin choisi est sauvegarde dans `export_base_dir` de `settings.yaml`
  - [x] And: chaque compte exportera dans `export_base_dir/<nom_du_compte>/`

- Acceptance Criteria (manuel):
  - [x] Given: je veux configurer sans le tray
  - [x] When: j'edite `settings.yaml` et definis `export_base_dir`
  - [x] Then: tous les comptes utilisent ce repertoire de base

---

## "Export des emails en Markdown"

**As a** utilisateur
**I want** exporter tous mes emails en fichiers Markdown
**So that** je puisse les consulter, rechercher et archiver independamment de mon client email

- Acceptance Criteria:
  - [x] Given: mes comptes sont configures dans `accounts.yaml` et `settings.yaml`
  - [x] When: je lance `email-to-markdown export`
  - [x] Then: tous mes emails sont exportes en fichiers `.md`
  - [x] And: l'arborescence des dossiers IMAP est respectee (INBOX/, Sent/, etc.)
  - [x] And: chaque fichier contient un frontmatter YAML avec les metadonnees (from, to, date, subject)
  - [x] And: le nom du fichier suit le format `email_YYYY-MM-DD_EXPEDITEUR_to_DESTINATAIRE.md`
  - [x] And: les emails deja exportes sont ignores si `skip_existing: true`

---

## "Gestion des pieces jointes"

**As a** utilisateur
**I want** retrouver toutes mes pieces jointes dans un dossier separe
**So that** je puisse acceder aux documents importants sans les images de signature

- Acceptance Criteria:
  - [x] Given: un email contient des pieces jointes
  - [x] When: l'email est exporte
  - [x] Then: les pieces jointes sont sauvegardees dans `attachments/` avec la meme arborescence
  - [x] And: les images de signature (logo, banner, footer < 50KB) sont filtrees si `skip_signature_images: true`
  - [x] And: le fichier Markdown contient des liens vers les pieces jointes

---

## "Collection des contacts"

**As a** utilisateur
**I want** obtenir un fichier CSV avec tous mes contacts
**So that** je puisse identifier mes correspondants et leur type (direct, liste de diffusion, newsletter)

- Acceptance Criteria:
  - [x] Given: l'option `collect_contacts: true` est activee dans `settings.yaml`
  - [x] When: l'export est termine
  - [x] Then: un fichier `contacts_COMPTE_DATE.csv` est genere
  - [x] And: chaque contact a un type: direct, group, newsletter, mailing_list

---

## "Tri des emails"

**As a** utilisateur
**I want** categoriser mes emails exportes en trois categories: supprimer, resumer, garder
**So that** je puisse nettoyer ma boite mail et ne conserver que l'essentiel

- Acceptance Criteria:
  - [x] Given: mes emails ont ete exportes en Markdown
  - [x] When: je lance `email-to-markdown sort --account Gmail`
  - [x] Then: un rapport `sort_report.json` est genere avec trois categories:
    - `delete`: emails a supprimer (newsletters, promotions, spam)
    - `summarize`: emails a resumer (updates, rapports, suivis)
    - `keep`: emails a conserver en entier (contrats, factures, important)
  - [x] And: le tri est base sur des mots-cles, l'expediteur, le type d'email et l'age

---

## "Gestion des listes blanches"

**As a** utilisateur
**I want** definir des contacts en liste blanche
**So that** tous leurs emails soient automatiquement conserves sans tri

- Acceptance Criteria:
  - [x] Given: j'ai configure `sort_config.json` avec une whitelist
  - [x] When: un email provient d'un contact en liste blanche
  - [x] Then: l'email est automatiquement classe dans "keep"
  - [x] And: je peux ajouter:
    - une adresse exacte: `"important@client.com"`
    - un domaine: `"@entreprise.com"`
    - un prefixe: `"directeur@"`

---

## "Gestion des listes noires"

**As a** utilisateur
**I want** definir des contacts ou mots-cles en liste noire
**So that** leurs emails soient automatiquement marques a supprimer

- Acceptance Criteria:
  - [x] Given: j'ai configure `sort_config.json` avec des `delete_senders` et `delete_keywords`
  - [x] When: un email correspond aux criteres de liste noire
  - [x] Then: l'email est automatiquement classe dans "delete"
  - [x] And: je peux definir:
    - des expediteurs: `["newsletter@", "no-reply@", "marketing@"]`
    - des mots-cles dans le sujet: `["unsubscribe", "promotion", "offer"]`

---

## "Interface dans la barre systeme"

**As a** utilisateur
**I want** acceder aux fonctions principales sans ouvrir un terminal
**So that** je puisse exporter et trier mes emails d'un simple clic droit sur l'icone

- Acceptance Criteria:
  - [x] Given: l'application est lancee avec `email-to-markdown tray`
  - [x] Then: une icone enveloppe apparait dans la barre systeme
  - [x] When: je fais un clic droit sur l'icone
  - [x] Then: un menu contextuel s'affiche avec:
    - un sous-menu "Export compte" liste les comptes configures
    - un sous-menu "Trier emails" liste les comptes configures
    - "Import Thunderbird" pour reimporter les comptes
    - "Choisir repertoire d'export…" pour definir `export_base_dir`
    - "Parametres…" pour ouvrir `settings.yaml` dans l'editeur par defaut
    - "Quitter"
  - [x] And: si aucun compte n'est configure, les sous-menus Export et Tri sont desactives
  - [x] And: apres un import, le menu est reconstruit pour refleter les nouveaux comptes
  - [x] And: chaque action affiche une notification modale a la fin (succes ou erreur)

---

## Configuration de reference

### `accounts.yaml` (connexion uniquement)
```yaml
accounts:
  - name: Gmail
    server: imap.gmail.com
    port: 993
    username: mon.email@gmail.com
    ignored_folders:
      - "[Gmail]/Spam"
      - "[Gmail]/Trash"
      - "[Gmail]/All Mail"
```

### `settings.yaml` (comportement)
```yaml
export_base_dir: C:/Users/VotreNom/Documents/Emails

defaults:
  quote_depth: 1
  skip_existing: true
  collect_contacts: false
  skip_signature_images: true
  delete_after_export: false

# accounts:
#   Gmail:
#     collect_contacts: true
```

### `.env` (mots de passe)
```bash
GMAIL_APPLICATION_PASSWORD=xxxx-xxxx-xxxx-xxxx
OUTLOOK_PASSWORD=votre_mot_de_passe
```

### `sort_config.json`
```json
{
  "whitelist": ["important@client.com", "@mon-entreprise.com"],
  "delete_keywords": ["newsletter", "unsubscribe", "promotion"],
  "delete_senders": ["no-reply@", "marketing@"],
  "keep_keywords": ["facture", "contrat", "urgent"],
  "keep_with_attachments": true,
  "recent_threshold_days": 30,
  "old_threshold_days": 365
}
```

---

## Workflow typique

### Via le tray (recommande)
```
1. Lancer : email-to-markdown tray
2. Clic droit → Import Thunderbird → Oui (avec mots de passe)
3. Clic droit → Choisir repertoire d'export… → selectionner un dossier
4. Clic droit → Export compte → Gmail
5. Clic droit → Trier emails → Gmail
```

### Via le CLI
```bash
# 1. Importer depuis Thunderbird
email-to-markdown import --extract-passwords

# 2. Choisir le repertoire d'export dans settings.yaml
# Editer %APPDATA%\email-to-markdown\settings.yaml

# 3. Exporter les emails
email-to-markdown export --account Gmail

# 4. Trier les emails exportes
email-to-markdown sort --account Gmail
```

---

## Resultat attendu

```
C:/Users/VotreNom/Documents/Emails/Gmail/
├── INBOX/
│   ├── email_2024-01-15_JD_to_ME.md
│   └── email_2024-01-16_BOSS_to_ME.md
├── Sent/
│   └── email_2024-01-15_ME_to_CLIENT.md
├── attachments/
│   └── INBOX/
│       └── email_2024-01-15_JD_to_ME_abc123_contrat.pdf
└── sort_report.json
```
