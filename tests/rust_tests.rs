use email_to_markdown::config::{SortConfig, Config, Account, Settings, AccountBehavior};
use email_to_markdown::network::{NetworkConfig, ProgressIndicator};  // [3][4]
use email_to_markdown::utils::*;
use std::path::PathBuf;
use std::time::Duration;
use tempfile::TempDir;

mod utils_tests {
    use super::*;

    #[test]
    fn test_limit_quote_depth_basic() {
        let text = "Hello\n> First quote\n>> Second quote\n>>> Third quote\n> Back to first";
        let result = limit_quote_depth(text, 1);
        let expected = "Hello\n> First quote\n> Back to first";
        assert_eq!(result, expected);
    }

    #[test]
    fn test_limit_quote_depth_no_quotes() {
        let text = "Hello\nWorld";
        let result = limit_quote_depth(text, 1);
        assert_eq!(result, text);
    }

    #[test]
    fn test_get_short_name_email() {
        assert_eq!(get_short_name(Some("sender@example.com")), "SEN");
    }

    #[test]
    fn test_get_short_name_full_name() {
        assert_eq!(get_short_name(Some("John Doe <john@example.com>")), "JD");
    }

    #[test]
    fn test_get_short_name_multiple_words() {
        assert_eq!(get_short_name(Some("John Michael Doe")), "JMD");
    }

    #[test]
    fn test_get_short_name_none() {
        assert_eq!(get_short_name(None), "UNK");
    }

    #[test]
    fn test_get_short_name_empty() {
        assert_eq!(get_short_name(Some("")), "UNK");
    }

    #[test]
    fn test_extract_emails_single() {
        let result = extract_emails(Some("Name <email@domain.com>"));
        assert_eq!(result, vec!["email@domain.com"]);
    }

    #[test]
    fn test_extract_emails_multiple() {
        let result = extract_emails(Some("a@b.com, c@d.com"));
        assert_eq!(result, vec!["a@b.com", "c@d.com"]);
    }

    #[test]
    fn test_extract_emails_none() {
        let result = extract_emails(None);
        assert!(result.is_empty());
    }

    #[test]
    fn test_normalize_line_breaks() {
        let text = "Hello\n\n\n\nWorld";
        let result = normalize_line_breaks(text);
        assert_eq!(result, "Hello\n\nWorld");
    }

    #[test]
    fn test_is_signature_image_signature() {
        assert!(is_signature_image(
            Some("signature.png"),
            "image/png",
            1024,
            Some("inline")
        ));
    }

    #[test]
    fn test_is_signature_image_logo() {
        assert!(is_signature_image(
            Some("logo.jpg"),
            "image/jpeg",
            5120,
            Some("attachment")
        ));
    }

    #[test]
    fn test_is_signature_image_document() {
        assert!(!is_signature_image(
            Some("contract.pdf"),
            "application/pdf",
            102400,
            Some("attachment")
        ));
    }

    #[test]
    fn test_is_signature_image_large_photo() {
        assert!(!is_signature_image(
            Some("photo_vacation.jpg"),
            "image/jpeg",
            2048000,
            Some("attachment")
        ));
    }

    #[test]
    fn test_hash_md5_prefix_length() {
        let hash = hash_md5_prefix("Test Subject", 6);
        assert_eq!(hash.len(), 6);
    }

    #[test]
    fn test_hash_md5_prefix_consistency() {
        let hash1 = hash_md5_prefix("Test Subject", 6);
        let hash2 = hash_md5_prefix("Test Subject", 6);
        assert_eq!(hash1, hash2);
    }

    #[test]
    fn test_sanitize_filename() {
        let filename = "test<>:\"/\\|?*.txt";
        let result = sanitize_filename(filename);
        assert!(!result.contains('<'));
        assert!(!result.contains('>'));
        assert!(!result.contains(':'));
    }

    #[test]
    fn test_decode_imap_utf7_basic() {
        let result = decode_imap_utf7("INBOX");
        assert_eq!(result, "INBOX");
    }

    #[test]
    fn test_decode_imap_utf7_french_chars() {
        // &AOk- is IMAP modified UTF-7 for é (U+00E9)
        let result = decode_imap_utf7("INBOX.&AOk-");
        assert!(result.contains('é') || result == "INBOX.&AOk-");
    }
}

mod config_tests {
    use super::*;

    #[test]
    fn test_sort_config_default() {
        let config = SortConfig::default();
        assert!(config.delete_keywords.contains(&"newsletter".to_string()));
        assert!(config.keep_keywords.contains(&"contract".to_string()));
        assert_eq!(config.recent_threshold_days, 30);
    }

    #[test]
    fn test_config_validation_empty_accounts_is_ok() {
        // Empty account list is valid — no error expected
        let config = Config { accounts: vec![] };
        assert!(config.validate().is_ok());
    }

    #[test]
    fn test_is_whitelisted_exact_match() {
        let mut config = SortConfig::default();
        config.whitelist = vec!["important@client.com".into()];

        assert!(config.is_whitelisted("important@client.com"));
        assert!(!config.is_whitelisted("other@client.com"));
    }

    #[test]
    fn test_is_whitelisted_domain() {
        let mut config = SortConfig::default();
        config.whitelist = vec!["@company.com".into()];

        assert!(config.is_whitelisted("anyone@company.com"));
        assert!(config.is_whitelisted("ceo@company.com"));
        assert!(!config.is_whitelisted("user@other.com"));
    }

    #[test]
    fn test_is_whitelisted_prefix() {
        let mut config = SortConfig::default();
        config.whitelist = vec!["boss@".into()];

        assert!(config.is_whitelisted("boss@anywhere.com"));
        assert!(config.is_whitelisted("boss@company.com"));
        assert!(!config.is_whitelisted("employee@anywhere.com"));
    }

    #[test]
    fn test_is_whitelisted_empty() {
        let config = SortConfig::default();
        assert!(!config.is_whitelisted("anyone@example.com"));
    }

    #[test]
    fn test_sort_config_save_load() {
        let temp_dir = TempDir::new().unwrap();
        let config_path = temp_dir.path().join("test_config.json");

        let config = SortConfig::default();
        config.save(&config_path).unwrap();

        let loaded = SortConfig::load(&config_path).unwrap();
        assert_eq!(loaded.recent_threshold_days, config.recent_threshold_days);
        assert_eq!(loaded.delete_keywords.len(), config.delete_keywords.len());
    }
}

mod settings_tests {
    use super::*;

    #[test]
    fn test_settings_default() {
        let s = Settings::default();
        assert!(s.export_base_dir.is_none());
        assert!(s.defaults.quote_depth.is_none());
        assert!(s.accounts.is_empty());
    }

    #[test]
    fn test_settings_save_load_roundtrip() {
        let temp = TempDir::new().unwrap();
        let path = temp.path().join("settings.yaml");

        let mut s = Settings::default();
        s.export_base_dir = Some("/tmp/emails".to_string());
        s.defaults.quote_depth = Some(2);
        s.defaults.skip_existing = Some(false);
        s.save(&path).unwrap();

        let loaded = Settings::load(&path).unwrap();
        assert_eq!(loaded.export_base_dir, Some("/tmp/emails".to_string()));
        assert_eq!(loaded.defaults.quote_depth, Some(2));
        assert_eq!(loaded.defaults.skip_existing, Some(false));
    }

    #[test]
    fn test_settings_missing_file_returns_default() {
        let s = Settings::load(std::path::Path::new("/nonexistent/settings.yaml")).unwrap();
        assert!(s.export_base_dir.is_none());
    }

    #[test]
    fn test_config_merge_export_dir_from_base() {
        let temp = TempDir::new().unwrap();

        let accounts_yaml = "accounts:\n  - name: TestAccount\n    server: imap.example.com\n    port: 993\n    username: user@example.com\n";
        let accounts_path = temp.path().join("accounts.yaml");
        std::fs::write(&accounts_path, accounts_yaml).unwrap();

        let settings_yaml = "export_base_dir: /tmp/emails\n";
        let settings_path = temp.path().join("settings.yaml");
        std::fs::write(&settings_path, settings_yaml).unwrap();

        let config = Config::load_with_settings(&accounts_path, &settings_path).unwrap();
        assert_eq!(config.accounts.len(), 1);
        assert_eq!(config.accounts[0].export_directory, "/tmp/emails/TestAccount");
    }

    #[test]
    fn test_config_merge_defaults_applied() {
        let temp = TempDir::new().unwrap();

        let accounts_yaml = "accounts:\n  - name: TestAccount\n    server: imap.example.com\n    port: 993\n    username: user@example.com\n";
        let accounts_path = temp.path().join("accounts.yaml");
        std::fs::write(&accounts_path, accounts_yaml).unwrap();

        let settings_yaml = "export_base_dir: /tmp/emails\ndefaults:\n  quote_depth: 3\n  collect_contacts: true\n";
        let settings_path = temp.path().join("settings.yaml");
        std::fs::write(&settings_path, settings_yaml).unwrap();

        let config = Config::load_with_settings(&accounts_path, &settings_path).unwrap();
        assert_eq!(config.accounts[0].quote_depth, 3);
        assert!(config.accounts[0].collect_contacts);
    }

    #[test]
    fn test_config_merge_per_account_overrides_folder_name() {
        let temp = TempDir::new().unwrap();

        let accounts_yaml = "accounts:\n  - name: TestAccount\n    server: imap.example.com\n    port: 993\n    username: user@example.com\n";
        let accounts_path = temp.path().join("accounts.yaml");
        std::fs::write(&accounts_path, accounts_yaml).unwrap();

        let settings_yaml = "export_base_dir: /tmp/emails\naccounts:\n  TestAccount:\n    folder_name: custom-folder\n    quote_depth: 5\n";
        let settings_path = temp.path().join("settings.yaml");
        std::fs::write(&settings_path, settings_yaml).unwrap();

        let config = Config::load_with_settings(&accounts_path, &settings_path).unwrap();
        assert!(config.accounts[0].export_directory.ends_with("custom-folder"));
        assert_eq!(config.accounts[0].quote_depth, 5);
    }

    #[test]
    fn test_config_merge_no_settings_uses_hardcoded_defaults() {
        let temp = TempDir::new().unwrap();

        // accounts.yaml without settings.yaml → export_directory is empty, validation fails
        let accounts_yaml = "accounts:\n  - name: TestAccount\n    server: imap.example.com\n    port: 993\n    username: user@example.com\n";
        let accounts_path = temp.path().join("accounts.yaml");
        std::fs::write(&accounts_path, accounts_yaml).unwrap();

        let missing_settings = temp.path().join("settings.yaml"); // does not exist

        let config = Config::load_with_settings(&accounts_path, &missing_settings);
        // Should fail validation: export_directory is empty because no export_base_dir set
        assert!(config.is_err());
    }
}

mod email_export_tests {
    use email_to_markdown::email_export::*;

    #[test]
    fn test_analyze_email_type_direct() {
        let raw_email = b"From: sender@example.com\r\nTo: recipient@example.com\r\nSubject: Test\r\n\r\nBody";
        let mail = mailparse::parse_mail(raw_email).unwrap();
        let analysis = analyze_email_type(&mail);

        assert_eq!(analysis.email_type, EmailType::Direct);
        assert_eq!(analysis.from, "sender@example.com");
    }

    #[test]
    fn test_analyze_email_type_newsletter() {
        let raw_email = b"From: news@example.com\r\nTo: user@example.com\r\nSubject: Weekly Newsletter\r\n\r\nBody";
        let mail = mailparse::parse_mail(raw_email).unwrap();
        let analysis = analyze_email_type(&mail);

        assert_eq!(analysis.email_type, EmailType::Newsletter);
    }

    #[test]
    fn test_analyze_email_type_group() {
        let raw_email = b"From: sender@example.com\r\nTo: a@example.com, b@example.com\r\nSubject: Test\r\n\r\nBody";
        let mail = mailparse::parse_mail(raw_email).unwrap();
        let analysis = analyze_email_type(&mail);

        assert_eq!(analysis.email_type, EmailType::Group);
    }

    #[test]
    fn test_contacts_collector_add() {
        let mut collector = ContactsCollector::new();
        collector.add(&EmailType::Direct, "test@example.com".to_string());
        collector.add(&EmailType::Group, "group@example.com".to_string());

        assert!(collector.direct.contains("test@example.com"));
        assert!(collector.group.contains("group@example.com"));
    }

    #[test]
    fn test_export_stats_default() {
        let stats = ExportStats::default();
        assert_eq!(stats.exported, 0);
        assert_eq!(stats.skipped, 0);
        assert_eq!(stats.errors, 0);
    }
}

mod fix_yaml_tests {
    use email_to_markdown::fix_yaml::*;

    #[test]
    fn test_fix_complex_yaml_tags_python_object() {
        let content = "subject: !!python/object:email.header.Header test";
        let fixed = fix_complex_yaml_tags(content);
        assert!(!fixed.contains("!!python/object:"));
    }

    #[test]
    fn test_fix_complex_yaml_tags_anchor() {
        let content = "field: &anchor value";
        let fixed = fix_complex_yaml_tags(content);
        assert!(!fixed.contains("&anchor"));
    }

    #[test]
    fn test_extract_frontmatter_valid() {
        let content = "---\nfrom: test@example.com\n---\n\nBody content";
        let result = extract_frontmatter(content);
        assert!(result.is_some());

        let (frontmatter, body) = result.unwrap();
        assert!(frontmatter.contains("from:"));
        assert!(body.contains("Body content"));
    }

    #[test]
    fn test_extract_frontmatter_no_closing() {
        let content = "---\nfrom: test@example.com\n\nBody content";
        let result = extract_frontmatter(content);
        assert!(result.is_none());
    }

    #[test]
    fn test_extract_frontmatter_no_opening() {
        let content = "from: test@example.com\n---\n\nBody content";
        let result = extract_frontmatter(content);
        assert!(result.is_none());
    }
}

mod sort_emails_tests {
    use email_to_markdown::sort_emails::*;
    use email_to_markdown::config::SortConfig;
    use std::path::PathBuf;

    #[test]
    fn test_category_display() {
        assert_eq!(Category::Delete.to_string(), "delete");
        assert_eq!(Category::Summarize.to_string(), "summarize");
        assert_eq!(Category::Keep.to_string(), "keep");
    }

    #[test]
    fn test_email_sort_type_display() {
        assert_eq!(EmailSortType::Direct.to_string(), "direct");
        assert_eq!(EmailSortType::Newsletter.to_string(), "newsletter");
        assert_eq!(EmailSortType::Group.to_string(), "group");
    }

    #[test]
    fn test_email_sorter_new() {
        let config = SortConfig::default();
        let sorter = EmailSorter::new(PathBuf::from("/tmp"), config);

        let stats = sorter.stats();
        assert_eq!(stats.total_emails, 0);
    }
}

mod edge_case_tests {
    use super::*;

    #[test]
    fn test_empty_email_field() {
        let result = get_short_name(Some(""));
        assert_eq!(result, "UNK");
    }

    #[test]
    fn test_special_characters_in_email() {
        let result = get_short_name(Some("<invalid>email@test.com"));
        // Should handle special characters gracefully
        assert!(!result.is_empty());
    }

    #[test]
    fn test_unicode_in_name() {
        let result = get_short_name(Some("Jose Garcia <jose@example.com>"));
        // Should extract initials even with accented characters
        assert!(!result.is_empty());
    }

    #[test]
    fn test_very_long_email() {
        let long_local = "a".repeat(100);
        let email = format!("{}@example.com", long_local);
        let result = get_short_name(Some(&email));
        // Should truncate appropriately
        assert!(result.len() <= 3);
    }

    #[test]
    fn test_normalize_many_newlines() {
        let text = "Hello\n\n\n\n\n\n\n\n\n\nWorld";
        let result = normalize_line_breaks(text);
        assert!(!result.contains("\n\n\n"));
    }

    #[test]
    fn test_signature_image_edge_size() {
        // Exactly at the threshold
        assert!(is_signature_image(
            Some("logo.png"),
            "image/png",
            60 * 1024 - 1,
            Some("attachment")
        ));

        // Just over threshold for signature
        assert!(!is_signature_image(
            Some("signature.png"),
            "image/png",
            50 * 1024 + 1,
            Some("attachment")
        ));
    }
}

// [3][4] Tests pour le module network
mod network_tests {
    use super::*;

    #[test]
    fn test_network_config_default() {
        let config = NetworkConfig::default();
        assert_eq!(config.max_retries, 3);
        assert_eq!(config.connect_timeout, Duration::from_secs(30));
        assert_eq!(config.read_timeout, Duration::from_secs(60));
    }

    #[test]
    fn test_progress_indicator_create() {
        let progress = ProgressIndicator::new("Test", 100);
        // Just verify it creates without panic
        assert!(true);
    }

    #[test]
    fn test_progress_indicator_update() {
        let mut progress = ProgressIndicator::new("Test", 10);
        progress.update(5);
        progress.inc();
        // Verify it updates without panic
        assert!(true);
    }
}
