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

**Exporter un compte spécifique** (utile pour les tests) :
```bash
EXPORT_SPECIFIC_ACCOUNTS="LaContreVoie" python export_emails.py
```

**Exporter plusieurs comptes spécifiques** :
```bash
EXPORT_SPECIFIC_ACCOUNTS="Gmail,LaContreVoie" python export_emails.py
```

## Configuration avancée

### Options disponibles

- **`delete_after_export`** : Supprime les emails après export (désactivé par défaut)
- **`ignored_folders`** : Liste des dossiers à ignorer pendant l'export
- **`quote_depth`** : Profondeur maximale des citations à conserver (par défaut: 1)
- **`skip_existing`** : Ignore les emails déjà exportés (activé par défaut)
- **`collect_contacts`** : Génère un fichier de contacts CSV (désactivé par défaut)
- **`skip_signature_images`** : Ignore les images de signature et logos (désactivé par défaut)

### Options d'exécution

- **`EXPORT_SPECIFIC_ACCOUNTS`** : Variable d'environnement pour exporter uniquement certains comptes (utile pour les tests)
- **`DEBUG_IMAP`** : Active le mode debug pour voir les détails de la connexion IMAP (`true`/`false`)

### Export sélectif pour les tests

Pour tester l'export sur un seul compte sans traiter tous vos comptes email :

**Cas d'usage** :
- Tester un nouveau compte avant de l'ajouter à l'export complet
- Déboguer un problème spécifique à un compte
- Économiser du temps lors des tests

**Fonctionnement** :
- La comparaison des noms de comptes est insensible à la casse
- Vous pouvez utiliser majuscules ou minuscules indifféremment
- Plusieurs comptes peuvent être spécifiés, séparés par des virgules

### Mode debug pour le dépannage

Si vous rencontrez des problèmes de connexion ou d'accès aux dossiers, activez le mode debug :

```bash
DEBUG_IMAP=true EXPORT_SPECIFIC_ACCOUNTS="LaContreVoie" python3 export_emails.py
```

**Ce que vous verrez** :
- Liste complète des dossiers retournés par le serveur IMAP
- Détails de la connexion et de l'authentification
- Informations sur les dossiers traités ou ignorés

**Quand l'utiliser** :
- Si aucun dossier n'est trouvé
- Pour vérifier que le serveur IMAP retourne bien vos dossiers
- Pour diagnostiquer des problèmes d'accès spécifiques

**Exemple** :
```bash
# Exporter uniquement LaContreVoie (insensible à la casse)
EXPORT_SPECIFIC_ACCOUNTS="LaContreVoie" python export_emails.py
EXPORT_SPECIFIC_ACCOUNTS="lacontrevoie" python export_emails.py  # fonctionne aussi

# Exporter Gmail et LaContreVoie uniquement
EXPORT_SPECIFIC_ACCOUNTS="Gmail,LaContreVoie" python export_emails.py
```

**Affichage** :
```bash
🎯 Selected account for export: LaContreVoie
📥 Skipping account: Gmail
📧 Processing account: LaContreVoie → /chemin/vers/export/LaContreVoie
✅ Export completed for LaContreVoie
```

### Gestion des dossiers avec espaces

Le script gère automatiquement les dossiers dont les noms contiennent des espaces ou des caractères spéciaux comme :
- `"INBOX/suivi clients"`
- `"Projets/Client A - Contrat"`
- `"Archives/2023 - Comptes"`

**Pas de configuration supplémentaire nécessaire** - le script s'occupe de tout automatiquement.

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
    collect_contacts: true
    skip_signature_images: true  # Nouvelle option pour ignorer les images de signature
    ignored_folders:
      - "[Gmail]/Spam"
      - "[Gmail]/Trash"
      - "[Gmail]/Drafts"
```

### Filtrage des images de signature

Le script peut maintenant détecter et ignorer automatiquement les images de signature et logos pour éviter d'encombrer vos exports avec des fichiers inutiles.

**Comment ça marche** :
- Détection des noms de fichiers courants (signature.png, logo.jpg, etc.)
- Filtrage des petites images (< 50KB) qui sont généralement des logos
- Ignore les images avec disposition "inline" (images intégrées)
- Filtrage des images génériques (image1.png, img2.jpg, etc.)

**Pour l'activer** :
```yaml
skip_signature_images: true
```

**Exemple de sortie** :
```bash
📁 Exporting INBOX → /chemin/vers/export/INBOX
    Skipping signature image: 'signature.png' (12345 bytes)
    Skipping signature image: 'company_logo.jpg' (8765 bytes)
✅ INBOX: 5 emails exported (2 signature images skipped)
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

Cette option permet de limiter la quantité de texte cité dans les réponses pour garder seulement l'essentiel.

**Exemple** : Avec `quote_depth: 1`, seules les citations directes sont conservées :

```
> Réponse à votre message (conservé)
>> Réponse à la réponse (supprimé)
```

**Pourquoi c'est utile** : Évite d'avoir des emails très longs avec beaucoup de contenu répété.

### Collection des contacts

Le script peut générer automatiquement un fichier de contacts à partir de vos emails, prêt à être importé dans votre client email préféré (Thunderbird, Gmail, Outlook, etc.).

**Pour l'activer** : Ajoutez simplement `collect_contacts: true` dans votre configuration.

**Ce que vous obtenez** :
- Un fichier CSV nommé `contacts_<votre_compte>_<date>.csv`
- Tous vos correspondants organisés avec leur nom, email et type
- Format standard compatible avec la plupart des logiciels

**Exemple** :
```bash
📇 Generated contacts file: contacts_Gmail_2023-11-15.csv
```

**Utilisation** : Importez simplement ce fichier dans votre carnet d'adresses pour avoir tous vos contacts organisés automatiquement.

### Éviter les doublons

Par défaut, le script ignore automatiquement les emails déjà exportés pour éviter les doublons.

**Comment ça marche** :
- Le script vérifie si un email a déjà été sauvegardé
- Si c'est le cas, il le saute et continue avec les autres
- À la fin, vous voyez un résumé clair par dossier

**Ce que vous voyez** :
- `✅ INBOX: 15 emails exported` (tous les emails étaient nouveaux)
- `📊 Sent: 5 exported, 10 skipped` (10 emails étaient déjà sauvegardés)

**Pourquoi c'est utile** :
- Pas de fichiers en double
- Gain de temps lors des exports répétés
- Vous pouvez relancer le script sans risque

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

Chaque email est exporté avec un en-tête YAML contenant les informations essentielles :

```markdown
---
from: expéditeur@domaine.com
to: destinataire@domaine.com
date: 2023-01-01T12:00:00+00:00
subject: Sujet de l'email
tags:
  - INBOX/fonctionnement/opale
attachments:
  - attachments/fonctionnement/opale/email_2023-01-01_EXP_to_DES_fichier.pdf
---

Corps de l'email en texte brut...
```

### Organisation des fichiers

**Noms des fichiers** : Chaque email est sauvegardé avec un nom clair comme `email_2023-11-15_JDO_to_MSM.md` où :
- `2023-11-15` = date de l'email
- `JDO` = initiales de l'expéditeur (John Doe)
- `MSM` = initiales du destinataire (Marie Martin)

**Gestion automatique des doublons** : Si plusieurs emails ont les mêmes caractéristiques, le script ajoute automatiquement un numéro (`_2`, `_3`, etc.) pour éviter les conflits.

**Pièces jointes** : Les fichiers attachés sont organisés dans des dossiers `attachments/` qui suivent la même structure que vos dossiers email.

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

**Erreur de sélection de dossier**
```
❌ Error for Gmail: SELECT command error: BAD [b'Could not parse command']
```

**Solution** : Cette erreur se produit généralement avec des dossiers contenant des espaces ou caractères spéciaux. Le script devrait maintenant gérer cela automatiquement. Si le problème persiste :
1. Vérifiez que vous utilisez la dernière version du script
2. Essayez d'ajouter le dossier problématique à la liste `ignored_folders` temporairement
3. Contactez le support si le problème continue

**Problème de connexion silencieux**
```
📧 Processing account: LaContreVoie → /chemin/vers/export/LaContreVoie
✅ Export completed for LaContreVoie
```

**Solution** : Si le script indique que l'export est terminé mais qu'aucun dossier n'a été traité :
1. Vérifiez que le mot de passe est correct dans votre fichier `.env`
2. Assurez-vous que le serveur IMAP est accessible (`mail.42l.fr:993`)
3. Vérifiez que l'IMAP est activé sur votre compte
4. Essayez de vous connecter manuellement avec un client email pour tester

**Commande pour tester la connexion** :
```bash
# Tester la connexion IMAP manuellement
openssl s_client -connect mail.42l.fr:993 -crlf
```

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