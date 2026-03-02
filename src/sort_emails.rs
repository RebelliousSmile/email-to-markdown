use crate::config::SortConfig;
use anyhow::{Context, Result};
use chrono::{DateTime, FixedOffset, Utc};
use serde::{Deserialize, Serialize};
use serde_yaml::Value;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

/// Email sorting category.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Category {
    Delete,
    Summarize,
    Keep,
}

impl std::fmt::Display for Category {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Category::Delete => write!(f, "delete"),
            Category::Summarize => write!(f, "summarize"),
            Category::Keep => write!(f, "keep"),
        }
    }
}

/// Email type classification.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EmailSortType {
    Newsletter,
    MailingList,
    Group,
    Direct,
    Unknown,
}

impl std::fmt::Display for EmailSortType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            EmailSortType::Newsletter => write!(f, "newsletter"),
            EmailSortType::MailingList => write!(f, "mailing_list"),
            EmailSortType::Group => write!(f, "group"),
            EmailSortType::Direct => write!(f, "direct"),
            EmailSortType::Unknown => write!(f, "unknown"),
        }
    }
}

/// Analyzed email data.
#[derive(Debug, Clone, Serialize)]
pub struct EmailData {
    pub file_path: PathBuf,
    pub file_name: String,
    pub file_size: u64,
    pub body_length: usize,
    pub has_attachments: bool,
    pub attachment_count: usize,
    pub date: Option<DateTime<FixedOffset>>,
    pub age_days: Option<i64>,
    pub sender: String,
    pub recipients: Vec<String>,
    pub subject: String,
    pub tags: Vec<String>,
    pub email_type: EmailSortType,
    pub score: i32,
    pub category: Category,
}

/// Sorting statistics.
#[derive(Debug, Default, Serialize)]
pub struct SortStats {
    pub total_emails: usize,
    pub by_category: HashMap<String, usize>,
    pub by_type: HashMap<String, usize>,
    pub by_sender: HashMap<String, usize>,
    pub by_date: HashMap<String, usize>,
}

/// Sorting report.
#[derive(Debug, Serialize)]
pub struct SortReport {
    pub summary: SortSummary,
    pub details: SortDetails,
    pub categories: HashMap<String, Vec<EmailSummary>>,
}

#[derive(Debug, Serialize)]
pub struct SortSummary {
    pub total_emails: usize,
    pub categories: HashMap<String, usize>,
    pub recommendations: HashMap<String, String>,
}

#[derive(Debug, Serialize)]
pub struct SortDetails {
    pub by_type: HashMap<String, usize>,
    pub by_sender: Vec<(String, usize)>,
    pub by_date: HashMap<String, usize>,
}

#[derive(Debug, Serialize)]
pub struct EmailSummary {
    pub file: String,
    pub subject: String,
    pub sender: String,
    pub date: String,
    pub score: i32,
    #[serde(rename = "type")]
    pub email_type: String,
    pub size: u64,
    pub attachments: usize,
}

/// Email sorter.
pub struct EmailSorter {
    base_directory: PathBuf,
    config: SortConfig,
    categories: HashMap<Category, Vec<EmailData>>,
    stats: SortStats,
}

impl EmailSorter {
    pub fn new(base_directory: PathBuf, config: SortConfig) -> Self {
        let mut stats = SortStats::default();
        stats.by_category.insert("delete".to_string(), 0);
        stats.by_category.insert("summarize".to_string(), 0);
        stats.by_category.insert("keep".to_string(), 0);

        EmailSorter {
            base_directory,
            config,
            categories: HashMap::new(),
            stats,
        }
    }

    /// Analyze a single email markdown file.
    pub fn analyze_email_file(&self, file_path: &Path) -> Result<Option<EmailData>> {
        let content = fs::read_to_string(file_path)
            .context("Failed to read file")?;

        // Handle empty or very small files
        if content.trim().len() < 10 {
            println!("  Skipping empty file: {}", file_path.display());
            return Ok(None);
        }

        // Handle files with no frontmatter
        if !content.starts_with("---") {
            println!(
                "  Skipping file with no YAML frontmatter: {}",
                file_path.display()
            );
            return Ok(None);
        }

        // Extract frontmatter and body
        let (frontmatter, body) = match extract_frontmatter(&content) {
            Some(parts) => parts,
            None => {
                println!("  No valid frontmatter in: {}", file_path.display());
                return Ok(None);
            }
        };

        // Parse frontmatter
        let fm: Value = match serde_yaml::from_str(&frontmatter) {
            Ok(v) => v,
            Err(e) => {
                println!("  Could not parse frontmatter: {}...", &e.to_string()[..100.min(e.to_string().len())]);
                return Ok(None);
            }
        };

        let metadata = fs::metadata(file_path)?;

        // Extract fields with null checks
        let subject = fm
            .get("subject")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let sender = fm
            .get("from")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let date_str = fm
            .get("date")
            .and_then(|v| v.as_str())
            .unwrap_or("");

        let attachments = fm
            .get("attachments")
            .and_then(|v| v.as_sequence())
            .map(|s| s.len())
            .unwrap_or(0);

        let tags: Vec<String> = fm
            .get("tags")
            .and_then(|v| v.as_sequence())
            .map(|s| {
                s.iter()
                    .filter_map(|v| v.as_str())
                    .map(String::from)
                    .collect()
            })
            .unwrap_or_default();

        // Parse date
        let date = parse_date(date_str);
        let age_days = date.map(|d| {
            let now = Utc::now();
            (now.signed_duration_since(d.with_timezone(&Utc))).num_days()
        });

        // Determine email type
        let email_type = self.determine_email_type(&subject, &fm);

        // Build email data
        let mut email_data = EmailData {
            file_path: file_path.to_path_buf(),
            file_name: file_path
                .file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .to_string(),
            file_size: metadata.len(),
            body_length: body.len(),
            has_attachments: attachments > 0,
            attachment_count: attachments,
            date,
            age_days,
            sender,
            recipients: Vec::new(),
            subject,
            tags,
            email_type,
            score: 0,
            category: Category::Summarize,
        };

        // Calculate score
        email_data.score = self.calculate_score(&email_data, &body);

        // Determine category
        email_data.category = self.determine_category(&email_data, &body);

        Ok(Some(email_data))
    }

    /// Determine email type from subject and frontmatter.
    fn determine_email_type(&self, subject: &str, _fm: &Value) -> EmailSortType {
        let subject_lower = subject.to_lowercase();

        if subject_lower.contains("newsletter")
            || subject_lower.contains("bulletin")
            || subject_lower.contains("digest")
        {
            EmailSortType::Newsletter
        } else {
            EmailSortType::Direct
        }
    }

    /// Calculate a score for the email.
    fn calculate_score(&self, email_data: &EmailData, body: &str) -> i32 {
        let mut score: i32 = 0;

        // Type weight
        let type_key = email_data.email_type.to_string();
        if let Some(&weight) = self.config.type_weights.get(&type_key) {
            score += weight;
        }

        // Age factors
        if let Some(age) = email_data.age_days {
            if age <= self.config.recent_threshold_days {
                score += 2;
            } else if age >= self.config.old_threshold_days {
                score -= 1;
            }
        }

        // Size factors
        if email_data.body_length <= self.config.small_email_threshold {
            score -= 1;
        } else if email_data.body_length >= self.config.large_email_threshold {
            score += 1;
        }

        // Attachment factors
        if email_data.has_attachments {
            if self.config.keep_with_attachments {
                score += 2;
            } else {
                score -= 1;
            }
        }

        // Subject analysis
        let subject_lower = email_data.subject.to_lowercase();

        // Delete keywords
        let delete_count = self
            .config
            .delete_keywords
            .iter()
            .filter(|k| subject_lower.contains(&k.to_lowercase()))
            .count() as i32;
        score -= delete_count;

        // Keep keywords
        let keep_count = self
            .config
            .keep_keywords
            .iter()
            .filter(|k| subject_lower.contains(&k.to_lowercase()))
            .count() as i32;
        score += keep_count * 2;

        // Sender analysis
        let sender_lower = email_data.sender.to_lowercase();

        if self
            .config
            .delete_senders
            .iter()
            .any(|s| sender_lower.contains(&s.to_lowercase()))
        {
            score -= 3;
        }

        if self
            .config
            .keep_senders
            .iter()
            .any(|s| sender_lower.contains(&s.to_lowercase()))
        {
            score += 3;
        }

        // Body content analysis
        let body_lower = body.to_lowercase();
        let important_keywords = [
            "contract",
            "invoice",
            "legal",
            "urgent",
            "important",
            "confidential",
            "agreement",
            "signature",
            "payment",
        ];

        if important_keywords
            .iter()
            .any(|&k| body_lower.contains(k))
        {
            score += 2;
        }

        score
    }

    /// Determine the category for an email.
    fn determine_category(&self, email_data: &EmailData, body: &str) -> Category {
        // Check whitelist first
        if self.config.is_whitelisted(&email_data.sender) {
            return Category::Keep;
        }

        let subject_lower = email_data.subject.to_lowercase();
        let sender_lower = email_data.sender.to_lowercase();
        let body_lower = body.to_lowercase();

        // Strong delete indicators
        let delete_indicators = email_data.email_type == EmailSortType::Newsletter
            || self
                .config
                .delete_keywords
                .iter()
                .any(|k| subject_lower.contains(&k.to_lowercase()))
            || self
                .config
                .delete_senders
                .iter()
                .any(|s| sender_lower.contains(&s.to_lowercase()));

        // Strong keep indicators
        let keep_indicators = self
            .config
            .keep_keywords
            .iter()
            .any(|k| subject_lower.contains(&k.to_lowercase()))
            || self
                .config
                .keep_senders
                .iter()
                .any(|s| sender_lower.contains(&s.to_lowercase()))
            || (email_data.has_attachments && self.config.keep_with_attachments)
            || ["contract", "invoice", "legal", "urgent", "important"]
                .iter()
                .any(|&k| body_lower.contains(k));

        // Apply rules
        if keep_indicators {
            Category::Keep
        } else if delete_indicators || email_data.score <= -2 {
            Category::Delete
        } else if email_data.score >= 2
            || email_data.body_length > self.config.summarize_max_length
        {
            Category::Keep
        } else {
            Category::Summarize
        }
    }

    /// Sort all emails in the directory.
    pub fn sort_emails(&mut self) -> Result<()> {
        println!("Sorting emails in: {}", self.base_directory.display());

        let entries: Vec<PathBuf> = WalkDir::new(&self.base_directory)
            .into_iter()
            .filter_map(|e| e.ok())
            .filter(|e| {
                e.path().extension().is_some_and(|ext| ext == "md")
                    && !e.path().to_string_lossy().contains("attachments")
            })
            .map(|e| e.path().to_path_buf())
            .collect();

        for file_path in entries {
            if let Some(email_data) = self.analyze_email_file(&file_path)? {
                self.stats.total_emails += 1;

                let category = email_data.category.clone();
                let category_key = category.to_string();
                *self
                    .stats
                    .by_category
                    .entry(category_key)
                    .or_insert(0) += 1;

                let type_key = email_data.email_type.to_string();
                *self.stats.by_type.entry(type_key).or_insert(0) += 1;

                *self
                    .stats
                    .by_sender
                    .entry(email_data.sender.clone())
                    .or_insert(0) += 1;

                if let Some(date) = &email_data.date {
                    let date_key = date.format("%Y-%m").to_string();
                    *self.stats.by_date.entry(date_key).or_insert(0) += 1;
                }

                self.categories
                    .entry(category)
                    .or_default()
                    .push(email_data);
            }
        }

        Ok(())
    }

    /// Generate a sorting report.
    pub fn generate_report(&self) -> SortReport {
        let total = self.stats.total_emails as f64;

        let mut recommendations = HashMap::new();
        if total > 0.0 {
            let delete_pct = (self.stats.by_category.get("delete").unwrap_or(&0) * 100) as f64 / total;
            let summarize_pct = (self.stats.by_category.get("summarize").unwrap_or(&0) * 100) as f64 / total;
            let keep_pct = (self.stats.by_category.get("keep").unwrap_or(&0) * 100) as f64 / total;

            recommendations.insert(
                "delete".to_string(),
                format!("{:.1}% of emails can be deleted", delete_pct),
            );
            recommendations.insert(
                "summarize".to_string(),
                format!("{:.1}% of emails can be summarized", summarize_pct),
            );
            recommendations.insert(
                "keep".to_string(),
                format!("{:.1}% of emails should be kept in full", keep_pct),
            );
        }

        // Get top senders
        let mut sender_counts: Vec<_> = self.stats.by_sender.iter().collect();
        sender_counts.sort_by(|a, b| b.1.cmp(a.1));
        let top_senders: Vec<(String, usize)> = sender_counts
            .into_iter()
            .take(10)
            .map(|(k, v)| (k.clone(), *v))
            .collect();

        // Build category details
        let mut categories = HashMap::new();
        for (category, emails) in &self.categories {
            let summaries: Vec<EmailSummary> = emails
                .iter()
                .map(|e| EmailSummary {
                    file: e
                        .file_path
                        .strip_prefix(&self.base_directory)
                        .unwrap_or(&e.file_path)
                        .to_string_lossy()
                        .to_string(),
                    subject: e.subject.clone(),
                    sender: e.sender.clone(),
                    date: e
                        .date
                        .map(|d| d.format("%Y-%m-%d").to_string())
                        .unwrap_or_else(|| "Unknown".to_string()),
                    score: e.score,
                    email_type: e.email_type.to_string(),
                    size: e.file_size,
                    attachments: e.attachment_count,
                })
                .collect();

            categories.insert(category.to_string(), summaries);
        }

        SortReport {
            summary: SortSummary {
                total_emails: self.stats.total_emails,
                categories: self.stats.by_category.clone(),
                recommendations,
            },
            details: SortDetails {
                by_type: self.stats.by_type.clone(),
                by_sender: top_senders,
                by_date: self.stats.by_date.clone(),
            },
            categories,
        }
    }

    /// Save report to JSON file.
    pub fn save_report(&self, report: &SortReport, output_file: &str) -> Result<PathBuf> {
        let output_path = self.base_directory.join(output_file);
        let content = serde_json::to_string_pretty(report)?;
        fs::write(&output_path, content)?;
        println!("Report saved to: {}", output_path.display());
        Ok(output_path)
    }

    /// Print summary of sorting results.
    pub fn print_summary(&self) {
        println!("\n==================================================");
        println!("EMAIL SORTING SUMMARY");
        println!("==================================================");

        println!("Total emails analyzed: {}", self.stats.total_emails);
        println!(
            "To delete: {}",
            self.stats.by_category.get("delete").unwrap_or(&0)
        );
        println!(
            "To summarize: {}",
            self.stats.by_category.get("summarize").unwrap_or(&0)
        );
        println!(
            "To keep: {}",
            self.stats.by_category.get("keep").unwrap_or(&0)
        );

        if self.stats.total_emails > 0 {
            let total = self.stats.total_emails as f64;
            let delete_pct = (self.stats.by_category.get("delete").unwrap_or(&0) * 100) as f64 / total;
            let summarize_pct = (self.stats.by_category.get("summarize").unwrap_or(&0) * 100) as f64 / total;
            let keep_pct = (self.stats.by_category.get("keep").unwrap_or(&0) * 100) as f64 / total;

            println!("\nPercentages:");
            println!("   Delete: {:.1}%", delete_pct);
            println!("   Summarize: {:.1}%", summarize_pct);
            println!("   Keep: {:.1}%", keep_pct);
        }

        println!("\nEmail types found:");
        let mut types: Vec<_> = self.stats.by_type.iter().collect();
        types.sort_by(|a, b| b.1.cmp(a.1));
        for (email_type, count) in types {
            println!("   {}: {}", email_type, count);
        }

        println!("\nTop senders:");
        let mut senders: Vec<_> = self.stats.by_sender.iter().collect();
        senders.sort_by(|a, b| b.1.cmp(a.1));
        for (sender, count) in senders.iter().take(5) {
            println!("   {}: {}", sender, count);
        }

        println!("==================================================");
    }

    /// Get reference to categories.
    pub fn categories(&self) -> &HashMap<Category, Vec<EmailData>> {
        &self.categories
    }

    /// Get reference to stats.
    pub fn stats(&self) -> &SortStats {
        &self.stats
    }
}

/// Extract frontmatter and body from markdown content.
fn extract_frontmatter(content: &str) -> Option<(String, String)> {
    if !content.starts_with("---") {
        return None;
    }

    let lines: Vec<&str> = content.lines().collect();
    let mut frontmatter_lines = Vec::new();
    let mut body_start = 0;
    let mut found_end = false;

    for (i, line) in lines.iter().enumerate() {
        if i == 0 {
            continue;
        }
        if line.trim() == "---" {
            body_start = i + 1;
            found_end = true;
            break;
        }
        frontmatter_lines.push(*line);
    }

    if !found_end {
        return None;
    }

    let frontmatter = frontmatter_lines.join("\n");
    let body = lines[body_start..].join("\n");

    Some((frontmatter, body))
}

/// Parse date string into DateTime.
fn parse_date(date_str: &str) -> Option<DateTime<FixedOffset>> {
    if date_str.is_empty() {
        return None;
    }

    // Try ISO format first
    if let Ok(dt) = DateTime::parse_from_rfc3339(date_str) {
        return Some(dt);
    }

    // Try other common formats
    let formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"];
    for fmt in &formats {
        if let Ok(naive) = chrono::NaiveDate::parse_from_str(date_str, fmt) {
            let dt = naive
                .and_hms_opt(0, 0, 0)?
                .and_local_timezone(FixedOffset::east_opt(0)?)
                .single()?;
            return Some(dt);
        }
    }

    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_frontmatter() {
        let content = "---\nfrom: test@example.com\nsubject: Test\n---\n\nBody content";
        let result = extract_frontmatter(content);
        assert!(result.is_some());

        let (frontmatter, body) = result.unwrap();
        assert!(frontmatter.contains("from:"));
        assert!(body.contains("Body content"));
    }

    #[test]
    fn test_parse_date_iso() {
        let result = parse_date("2024-01-15T10:30:00+00:00");
        assert!(result.is_some());
    }

    #[test]
    fn test_parse_date_simple() {
        let result = parse_date("2024-01-15");
        assert!(result.is_some());
    }

    #[test]
    fn test_category_display() {
        assert_eq!(Category::Delete.to_string(), "delete");
        assert_eq!(Category::Summarize.to_string(), "summarize");
        assert_eq!(Category::Keep.to_string(), "keep");
    }
}
