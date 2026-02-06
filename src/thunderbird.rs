// [1] Import automatique depuis Thunderbird
use anyhow::{Context, Result};
use regex::Regex;
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

use crate::config::Account;

/// Thunderbird profile information
#[derive(Debug, Clone)]
pub struct ThunderbirdProfile {
    pub name: String,
    pub path: PathBuf,
    pub is_default: bool,
}

/// Get Thunderbird profiles directory based on OS
pub fn get_thunderbird_profiles_dir() -> Option<PathBuf> {
    #[cfg(target_os = "windows")]
    {
        env::var("APPDATA")
            .ok()
            .map(|appdata| PathBuf::from(appdata).join("Thunderbird").join("Profiles"))
    }

    #[cfg(target_os = "macos")]
    {
        env::var("HOME")
            .ok()
            .map(|home| PathBuf::from(home).join("Library").join("Thunderbird").join("Profiles"))
    }

    #[cfg(target_os = "linux")]
    {
        env::var("HOME")
            .ok()
            .map(|home| PathBuf::from(home).join(".thunderbird"))
    }

    #[cfg(not(any(target_os = "windows", target_os = "macos", target_os = "linux")))]
    {
        None
    }
}

/// List available Thunderbird profiles
pub fn list_profiles() -> Result<Vec<ThunderbirdProfile>> {
    let profiles_dir = get_thunderbird_profiles_dir()
        .context("Could not determine Thunderbird profiles directory")?;

    let profiles_ini = profiles_dir.parent()
        .unwrap_or(&profiles_dir)
        .join("profiles.ini");

    if !profiles_ini.exists() {
        // Fallback: scan directory for profile folders
        return scan_profile_directories(&profiles_dir);
    }

    parse_profiles_ini(&profiles_ini, &profiles_dir)
}

/// Parse profiles.ini file
fn parse_profiles_ini(ini_path: &Path, base_dir: &Path) -> Result<Vec<ThunderbirdProfile>> {
    let content = fs::read_to_string(ini_path)
        .context("Failed to read profiles.ini")?;

    let mut profiles = Vec::new();
    let mut current_profile: Option<HashMap<String, String>> = None;

    for line in content.lines() {
        let line = line.trim();

        if line.starts_with('[') && line.ends_with(']') {
            // Save previous profile
            if let Some(profile) = current_profile.take() {
                if let Some(p) = build_profile_from_map(&profile, base_dir) {
                    profiles.push(p);
                }
            }

            // Start new profile section
            if line.to_lowercase().starts_with("[profile") {
                current_profile = Some(HashMap::new());
            }
        } else if let Some(ref mut profile) = current_profile {
            if let Some((key, value)) = line.split_once('=') {
                profile.insert(key.trim().to_lowercase(), value.trim().to_string());
            }
        }
    }

    // Don't forget the last profile
    if let Some(profile) = current_profile {
        if let Some(p) = build_profile_from_map(&profile, base_dir) {
            profiles.push(p);
        }
    }

    Ok(profiles)
}

fn build_profile_from_map(map: &HashMap<String, String>, base_dir: &Path) -> Option<ThunderbirdProfile> {
    let name = map.get("name")?.clone();
    let path_str = map.get("path")?;
    let is_relative = map.get("isrelative").map(|s| s == "1").unwrap_or(true);
    let is_default = map.get("default").map(|s| s == "1").unwrap_or(false);

    let path = if is_relative {
        base_dir.join(path_str)
    } else {
        PathBuf::from(path_str)
    };

    Some(ThunderbirdProfile {
        name,
        path,
        is_default,
    })
}

/// Scan directory for profile folders (fallback)
fn scan_profile_directories(profiles_dir: &Path) -> Result<Vec<ThunderbirdProfile>> {
    let mut profiles = Vec::new();

    if profiles_dir.exists() {
        for entry in fs::read_dir(profiles_dir)? {
            let entry = entry?;
            let path = entry.path();

            if path.is_dir() {
                let prefs_file = path.join("prefs.js");
                if prefs_file.exists() {
                    let name = path
                        .file_name()
                        .unwrap_or_default()
                        .to_string_lossy()
                        .to_string();

                    profiles.push(ThunderbirdProfile {
                        name: name.clone(),
                        path,
                        is_default: name.contains("default"),
                    });
                }
            }
        }
    }

    Ok(profiles)
}

/// Extract IMAP accounts from a Thunderbird profile
pub fn extract_accounts(profile: &ThunderbirdProfile) -> Result<Vec<Account>> {
    let prefs_file = profile.path.join("prefs.js");

    if !prefs_file.exists() {
        anyhow::bail!("prefs.js not found in profile: {}", profile.path.display());
    }

    let content = fs::read_to_string(&prefs_file)
        .context("Failed to read prefs.js")?;

    parse_prefs_js(&content)
}

/// Parse prefs.js and extract IMAP account configurations
fn parse_prefs_js(content: &str) -> Result<Vec<Account>> {
    let mut servers: HashMap<String, HashMap<String, String>> = HashMap::new();

    // Pattern: user_pref("mail.server.server1.property", "value");
    let re = Regex::new(r#"user_pref\("mail\.server\.([^.]+)\.([^"]+)",\s*"?([^")]+)"?\);"#)?;

    for cap in re.captures_iter(content) {
        let server_id = cap.get(1).map(|m| m.as_str()).unwrap_or("");
        let property = cap.get(2).map(|m| m.as_str()).unwrap_or("");
        let value = cap.get(3).map(|m| m.as_str()).unwrap_or("");

        servers
            .entry(server_id.to_string())
            .or_default()
            .insert(property.to_string(), value.to_string());
    }

    let mut accounts = Vec::new();

    for (server_id, props) in servers {
        // Only process IMAP accounts
        let server_type = props.get("type").map(|s| s.as_str()).unwrap_or("");
        if server_type != "imap" {
            continue;
        }

        let hostname = match props.get("hostname") {
            Some(h) => h.clone(),
            None => continue,
        };

        let username = props.get("userName").cloned().unwrap_or_default();
        let port = props
            .get("port")
            .and_then(|p| p.parse().ok())
            .unwrap_or(993);

        let name = props
            .get("name")
            .cloned()
            .unwrap_or_else(|| format!("Account_{}", server_id));

        // Clean the name for use as export directory
        let safe_name = sanitize_name(&name);

        accounts.push(Account {
            name: name.clone(),
            server: hostname,
            port,
            username,
            password: None, // Passwords are stored separately in Thunderbird
            export_directory: format!("./exports/{}", safe_name),
            ignored_folders: default_ignored_folders(&name),
            quote_depth: 1,
            skip_existing: true,
            collect_contacts: false,
            skip_signature_images: true,
            delete_after_export: false,
        });
    }

    Ok(accounts)
}

/// Sanitize account name for use as directory name
fn sanitize_name(name: &str) -> String {
    let re = Regex::new(r"[^a-zA-Z0-9_-]").unwrap();
    re.replace_all(name, "_").to_string()
}

/// Get default ignored folders based on account name
fn default_ignored_folders(name: &str) -> Vec<String> {
    let name_lower = name.to_lowercase();

    if name_lower.contains("gmail") {
        vec![
            "[Gmail]/Spam".to_string(),
            "[Gmail]/Trash".to_string(),
            "[Gmail]/All Mail".to_string(),
            "[Gmail]/Drafts".to_string(),
        ]
    } else if name_lower.contains("outlook") || name_lower.contains("hotmail") {
        vec![
            "Junk".to_string(),
            "Deleted Items".to_string(),
            "Drafts".to_string(),
        ]
    } else {
        vec![
            "Spam".to_string(),
            "Trash".to_string(),
            "Junk".to_string(),
            "Drafts".to_string(),
        ]
    }
}

/// Generate accounts.yaml content from extracted accounts
pub fn generate_accounts_yaml(accounts: &[Account]) -> String {
    let mut yaml = String::from("# Auto-generated from Thunderbird configuration\n");
    yaml.push_str("# Review and adjust settings as needed\n");
    yaml.push_str("# Passwords must be added to .env file\n\n");
    yaml.push_str("accounts:\n");

    for account in accounts {
        yaml.push_str(&format!("  - name: \"{}\"\n", account.name));
        yaml.push_str(&format!("    server: \"{}\"\n", account.server));
        yaml.push_str(&format!("    port: {}\n", account.port));
        yaml.push_str(&format!("    username: \"{}\"\n", account.username));
        yaml.push_str(&format!("    export_directory: \"{}\"\n", account.export_directory));
        yaml.push_str("    ignored_folders:\n");
        for folder in &account.ignored_folders {
            yaml.push_str(&format!("      - \"{}\"\n", folder));
        }
        yaml.push_str(&format!("    quote_depth: {}\n", account.quote_depth));
        yaml.push_str(&format!("    skip_existing: {}\n", account.skip_existing));
        yaml.push_str(&format!("    collect_contacts: {}\n", account.collect_contacts));
        yaml.push_str(&format!("    skip_signature_images: {}\n", account.skip_signature_images));
        yaml.push_str(&format!("    delete_after_export: {}\n", account.delete_after_export));
        yaml.push('\n');
    }

    // Add .env reminder
    yaml.push_str("# Add passwords to .env file:\n");
    for account in accounts {
        let env_var = account.name.to_uppercase().replace(' ', "_");
        yaml.push_str(&format!("# {}_PASSWORD=your_password\n", env_var));
    }

    yaml
}

/// Generate .env template from extracted accounts
pub fn generate_env_template(accounts: &[Account]) -> String {
    let mut env = String::from("# Email passwords\n");
    env.push_str("# Replace 'your_password' with actual passwords\n");
    env.push_str("# For Gmail with 2FA, use App Password\n\n");

    for account in accounts {
        let env_var = account.name.to_uppercase().replace(' ', "_").replace('-', "_");
        env.push_str(&format!("{}_PASSWORD=your_password\n", env_var));
        // Also add APPLICATION_PASSWORD variant for Gmail-like accounts
        if account.server.contains("gmail") {
            env.push_str(&format!("{}_APPLICATION_PASSWORD=your_app_password\n", env_var));
        }
    }

    env
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sanitize_name() {
        assert_eq!(sanitize_name("My Email Account"), "My_Email_Account");
        assert_eq!(sanitize_name("test@gmail.com"), "test_gmail_com");
    }

    #[test]
    fn test_default_ignored_folders_gmail() {
        let folders = default_ignored_folders("Gmail");
        assert!(folders.iter().any(|f| f.contains("[Gmail]")));
    }

    #[test]
    fn test_default_ignored_folders_other() {
        let folders = default_ignored_folders("MyMail");
        assert!(folders.contains(&"Spam".to_string()));
        assert!(folders.contains(&"Trash".to_string()));
    }

    #[test]
    fn test_parse_prefs_js() {
        let prefs = r#"
user_pref("mail.server.server1.type", "imap");
user_pref("mail.server.server1.hostname", "imap.gmail.com");
user_pref("mail.server.server1.port", "993");
user_pref("mail.server.server1.userName", "test@gmail.com");
user_pref("mail.server.server1.name", "Gmail");
"#;
        let accounts = parse_prefs_js(prefs).unwrap();
        assert_eq!(accounts.len(), 1);
        assert_eq!(accounts[0].server, "imap.gmail.com");
        assert_eq!(accounts[0].username, "test@gmail.com");
    }
}
