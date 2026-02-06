# Troubleshooting

Ce document liste les problemes courants lies a l'environnement de developpement ou au systeme, et non a l'application elle-meme.

## Table des matieres

- [Problemes de compilation](#problemes-de-compilation)
  - [Windows: Erreur de linker "extra operand"](#windows-erreur-de-linker-extra-operand)
  - [Windows: MSVC non trouve](#windows-msvc-non-trouve)
- [Problemes d'execution](#problemes-dexecution)
  - [System tray: Icone non visible](#system-tray-icone-non-visible)
  - [Certificats SSL/TLS](#certificats-ssltls)
- [Problemes de configuration](#problemes-de-configuration)
  - [Mot de passe non reconnu](#mot-de-passe-non-reconnu)
  - [Dossiers IMAP avec caracteres speciaux](#dossiers-imap-avec-caracteres-speciaux)

---

## Problemes de compilation

### Windows: Erreur de linker "extra operand"

**Symptome:**
```
error: linking with `link.exe` failed: exit code: 1
link: extra operand '...'
Try 'link --help' for more information.
```

**Cause:**
Le `link.exe` invoque est celui de Git Bash, Cygwin ou MSYS2 (commande GNU `link`) au lieu du linker MSVC.

**Solutions (par ordre de preference):**

#### Solution 1: Utiliser le Developer Command Prompt (recommande)

1. Ouvrir le menu Demarrer
2. Chercher "Developer Command Prompt for VS" ou "x64 Native Tools Command Prompt"
3. Compiler depuis cette invite de commandes:
   ```cmd
   cd C:\chemin\vers\email-to-markdown
   cargo build --features tray
   ```

#### Solution 2: Specifier le chemin du linker MSVC

1. Trouver le chemin de `link.exe` MSVC:
   ```cmd
   # Dans Developer Command Prompt:
   where link.exe
   ```

2. Ajouter dans `.cargo/config.toml`:
   ```toml
   [target.x86_64-pc-windows-msvc]
   linker = "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Tools\\MSVC\\14.38.33130\\bin\\Hostx64\\x64\\link.exe"
   ```

#### Solution 3: Utiliser la toolchain GNU avec MSYS2

1. Installer MSYS2: https://www.msys2.org/
2. Dans MSYS2:
   ```bash
   pacman -S mingw-w64-x86_64-toolchain
   ```
3. Ajouter au PATH: `C:\msys64\mingw64\bin`
4. Installer la toolchain:
   ```bash
   rustup toolchain install stable-x86_64-pc-windows-gnu
   rustup default stable-x86_64-pc-windows-gnu
   ```

#### Solution 4: Script PowerShell pour fixer le PATH temporairement

Creer un fichier `build.ps1`:
```powershell
# Trouve et ajoute MSVC au debut du PATH
$vsPath = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -latest -property installationPath
$vcToolsPath = Get-ChildItem "$vsPath\VC\Tools\MSVC" | Sort-Object -Descending | Select-Object -First 1
$linkPath = "$($vcToolsPath.FullName)\bin\Hostx64\x64"
$env:PATH = "$linkPath;$env:PATH"

# Build
cargo build --features tray
```

---

### Windows: dlltool.exe not found

**Symptome:**
```
error: error calling dlltool 'dlltool.exe': program not found
```

**Cause:**
La toolchain GNU (`stable-x86_64-pc-windows-gnu`) necessite les outils MinGW qui ne sont pas inclus.

**Solution:**
Installer MSYS2 et les outils MinGW:

1. Telecharger et installer MSYS2: https://www.msys2.org/
2. Ouvrir "MSYS2 MINGW64" depuis le menu Demarrer
3. Installer les outils:
   ```bash
   pacman -S mingw-w64-x86_64-toolchain
   ```
4. Ajouter au PATH systeme: `C:\msys64\mingw64\bin`
5. Redemarrer le terminal

---

### Windows: MSVC non trouve / C++ build tools manquants

**Symptomes:**
```
error: linker `link.exe` not found
```
ou
```
Erreur: link.exe MSVC non trouve dans Visual Studio
```

**Cause:**
Les outils de build C++ de Visual Studio ne sont pas installes ou incomplets.

**Solution:**

1. Ouvrir **Visual Studio Installer** (chercher dans le menu Demarrer)
2. Cliquer sur **Modifier** a cote de votre installation
3. Cocher **"Desktop development with C++"** (Developpement Desktop en C++)
4. Dans les composants individuels, verifier que ces elements sont coches:
   - MSVC v143 - VS 2022 C++ x64/x86 build tools
   - Windows 11 SDK (ou Windows 10 SDK)
5. Cliquer sur **Modifier** pour installer
6. Redemarrer le terminal

**Alternative: Installation minimale**

Si vous n'avez pas Visual Studio:
1. Telecharger "Build Tools for Visual Studio" depuis:
   https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
2. Executer l'installateur
3. Selectionner "C++ build tools"
4. Installer et redemarrer

---

## Problemes d'execution

### System tray: Icone non visible

**Symptome:**
L'application demarre mais aucune icone n'apparait dans la barre d'etat systeme.

**Causes possibles:**

1. **Windows: Zone de notification masquee**
   - Cliquer sur la fleche dans la barre des taches pour voir les icones cachees
   - Parametres > Personnalisation > Barre des taches > Zone de notification

2. **Linux: Pas de support systray**
   - Certains environnements de bureau (GNOME) ne supportent pas nativement le systray
   - Installer une extension comme "AppIndicator" ou "TopIcons Plus"

3. **macOS: Permissions**
   - Verifier les permissions dans Preferences Systeme > Securite et confidentialite

---

### Certificats SSL/TLS

**Symptome:**
```
error: certificate verify failed
```
ou
```
error: unable to get local issuer certificate
```

**Causes et solutions:**

1. **Certificats systeme non a jour**
   - Windows: Executer Windows Update
   - Linux: `sudo apt update && sudo apt install ca-certificates`
   - macOS: Mettre a jour macOS

2. **Proxy d'entreprise avec inspection SSL**
   - Ajouter le certificat racine de l'entreprise aux certificats de confiance
   - Contacter l'administrateur reseau

3. **Serveur IMAP avec certificat auto-signe**
   - Non supporte actuellement (necessite une connexion TLS valide)

---

## Problemes de configuration

### Mot de passe non reconnu

**Symptome:**
```
Error: No password found for ACCOUNT_NAME. Check your .env file.
```

**Verifications:**

1. **Fichier .env present**
   - Le fichier `.env` doit etre a la racine du projet ou dans le repertoire d'execution

2. **Nom de variable correct**
   ```env
   # Format attendu (en majuscules, underscores)
   GMAIL_PASSWORD=motdepasse
   # ou
   GMAIL_APPLICATION_PASSWORD=motdepasse
   ```

3. **Caracteres speciaux**
   - Si le mot de passe contient des caracteres speciaux, l'entourer de guillemets:
   ```env
   GMAIL_PASSWORD="mot=de#passe!"
   ```

4. **Mot de passe d'application (Gmail, Outlook)**
   - Les comptes avec 2FA necessitent un mot de passe d'application
   - Gmail: https://myaccount.google.com/apppasswords
   - Outlook: https://account.microsoft.com/security

---

### Dossiers IMAP avec caracteres speciaux

**Symptome:**
```
Error: Folder not found: Éléments envoyés
```

**Cause:**
Les noms de dossiers IMAP utilisent un encodage UTF-7 modifie.

**Solutions:**

1. **Utiliser le nom encode**
   - L'application devrait decoder automatiquement les noms
   - Si le probleme persiste, verifier les logs en mode debug: `cargo run -- export --debug`

2. **Ignorer le dossier problematique**
   ```yaml
   ignored_folders:
     - "Éléments envoyés"
   ```

---

## Obtenir de l'aide

Si votre probleme n'est pas liste ici:

1. Executer en mode debug pour plus d'informations:
   ```bash
   RUST_BACKTRACE=1 cargo run -- export --debug
   ```

2. Ouvrir une issue sur GitHub avec:
   - Description du probleme
   - Message d'erreur complet
   - Systeme d'exploitation et version
   - Version de Rust (`rustc --version`)
