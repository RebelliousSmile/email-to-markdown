//! System tray module for Email to Markdown.
//!
//! This module provides a system tray icon with a context menu
//! for easy access to common operations without using the CLI.

use std::sync::mpsc;

use anyhow::{Context, Result};
use tao::event_loop::{ControlFlow, EventLoopBuilder};
use tray_icon::{
    menu::{Menu, MenuEvent, MenuItem, PredefinedMenuItem, Submenu, accelerator::Accelerator},
    TrayIcon, TrayIconBuilder,
};

use crate::tray_actions::{
    self, ActionResult,
};

/// Menu item identifiers.
mod menu_ids {
    pub const IMPORT_THUNDERBIRD: &str = "import_thunderbird";
    pub const OPEN_CONFIG: &str = "open_config";
    pub const OPEN_DOCUMENTATION: &str = "open_documentation";
    pub const QUIT: &str = "quit";
    pub const EXPORT_PREFIX: &str = "export_";
    pub const SORT_PREFIX: &str = "sort_";
}

/// Run the system tray application.
pub fn run_tray() -> Result<()> {
    // Create event loop
    let event_loop = EventLoopBuilder::new().build();

    // Create the tray icon
    let tray_icon = create_tray_icon()?;

    // Channel for receiving action results
    let (result_sender, result_receiver) = mpsc::channel::<ActionResult>();

    // Menu event receiver
    let menu_channel = MenuEvent::receiver();

    // Run the event loop
    event_loop.run(move |_event, _, control_flow| {
        *control_flow = ControlFlow::Wait;

        // Handle menu events
        if let Ok(event) = menu_channel.try_recv() {
            handle_menu_event(&event.id.0, result_sender.clone());
        }

        // Handle action results (notifications)
        if let Ok(result) = result_receiver.try_recv() {
            show_notification(&result);
        }

        // Keep the tray icon alive
        let _ = &tray_icon;
    });
}

/// Create the system tray icon with menu.
fn create_tray_icon() -> Result<TrayIcon> {
    let menu = create_menu()?;

    let icon = load_icon()?;

    let tray_icon = TrayIconBuilder::new()
        .with_menu(Box::new(menu))
        .with_tooltip("Email to Markdown")
        .with_icon(icon)
        .build()
        .context("Failed to create tray icon")?;

    Ok(tray_icon)
}

/// Create the tray menu.
fn create_menu() -> Result<Menu> {
    let menu = Menu::new();

    // Get account names for submenus
    let accounts = tray_actions::get_account_names().unwrap_or_default();

    // Export submenu
    let export_submenu = Submenu::new("Export compte", true);
    let no_accel: Option<Accelerator> = None;

    if accounts.is_empty() {
        let _ = export_submenu.append(&MenuItem::with_id(
            "no_accounts",
            "(no accounts configured)",
            false,
            no_accel.clone(),
        ));
    } else {
        for account in &accounts {
            let id = format!("{}{}", menu_ids::EXPORT_PREFIX, account);
            let _ = export_submenu.append(&MenuItem::with_id(
                id,
                account,
                true,
                no_accel.clone(),
            ));
        }
    }
    menu.append(&export_submenu)?;

    // Sort submenu
    let sort_submenu = Submenu::new("Trier emails", true);
    if accounts.is_empty() {
        let _ = sort_submenu.append(&MenuItem::with_id(
            "no_accounts_sort",
            "(no accounts configured)",
            false,
            no_accel.clone(),
        ));
    } else {
        for account in &accounts {
            let id = format!("{}{}", menu_ids::SORT_PREFIX, account);
            let _ = sort_submenu.append(&MenuItem::with_id(
                id,
                account,
                true,
                no_accel.clone(),
            ));
        }
    }
    menu.append(&sort_submenu)?;

    // Separator
    menu.append(&PredefinedMenuItem::separator())?;

    // Import Thunderbird
    menu.append(&MenuItem::with_id(
        menu_ids::IMPORT_THUNDERBIRD,
        "Import Thunderbird",
        true,
        no_accel.clone(),
    ))?;

    // Open config
    menu.append(&MenuItem::with_id(
        menu_ids::OPEN_CONFIG,
        "Ouvrir config",
        true,
        no_accel.clone(),
    ))?;

    // Documentation
    menu.append(&MenuItem::with_id(
        menu_ids::OPEN_DOCUMENTATION,
        "Documentation",
        true,
        no_accel.clone(),
    ))?;

    // Separator
    menu.append(&PredefinedMenuItem::separator())?;

    // Quit
    menu.append(&MenuItem::with_id(
        menu_ids::QUIT,
        "Quitter",
        true,
        no_accel,
    ))?;

    Ok(menu)
}

/// Handle menu item clicks.
fn handle_menu_event(id: &str, result_sender: mpsc::Sender<ActionResult>) {
    match id {
        menu_ids::IMPORT_THUNDERBIRD => {
            tray_actions::action_import_thunderbird(result_sender);
        }
        menu_ids::OPEN_CONFIG => {
            if let Err(e) = tray_actions::action_open_config() {
                let _ = result_sender.send(ActionResult::Error(format!(
                    "Failed to open config: {}",
                    e
                )));
            }
        }
        menu_ids::OPEN_DOCUMENTATION => {
            if let Err(e) = tray_actions::action_open_documentation() {
                let _ = result_sender.send(ActionResult::Error(format!(
                    "Failed to open documentation: {}",
                    e
                )));
            }
        }
        menu_ids::QUIT => {
            std::process::exit(0);
        }
        id if id.starts_with(menu_ids::EXPORT_PREFIX) => {
            let account_name = id.strip_prefix(menu_ids::EXPORT_PREFIX).unwrap();
            tray_actions::action_export(account_name.to_string(), result_sender);
        }
        id if id.starts_with(menu_ids::SORT_PREFIX) => {
            let account_name = id.strip_prefix(menu_ids::SORT_PREFIX).unwrap();
            tray_actions::action_sort(account_name.to_string(), result_sender);
        }
        _ => {}
    }
}

/// Load the tray icon.
fn load_icon() -> Result<tray_icon::Icon> {
    // Try to load from file first
    let icon_paths = [
        "assets/icon.ico",
        "assets/icon.png",
    ];

    for path in &icon_paths {
        if std::path::Path::new(path).exists() {
            if let Ok(icon) = load_icon_from_file(path) {
                return Ok(icon);
            }
        }
    }

    // Fall back to embedded icon
    create_default_icon()
}

/// Load icon from a file.
fn load_icon_from_file(path: &str) -> Result<tray_icon::Icon> {
    let img = image::open(path).context("Failed to load icon image")?;
    let rgba = img.to_rgba8();
    let (width, height) = rgba.dimensions();

    tray_icon::Icon::from_rgba(rgba.into_raw(), width, height)
        .context("Failed to create icon from image")
}

/// Create a simple default icon (a colored square).
fn create_default_icon() -> Result<tray_icon::Icon> {
    // Create a simple 32x32 icon with an email-like appearance
    let size = 32u32;
    let mut rgba = vec![0u8; (size * size * 4) as usize];

    // Fill with a blue color (email icon style)
    for y in 0..size {
        for x in 0..size {
            let idx = ((y * size + x) * 4) as usize;

            // Create a simple envelope shape
            let is_border = x < 2 || x >= size - 2 || y < 2 || y >= size - 2;
            let is_envelope_top = y < size / 3 && (x as i32 - size as i32 / 2).abs() < (y as i32 + 2);
            let is_inner = !is_border && y >= 4 && y < size - 4 && x >= 4 && x < size - 4;

            if is_border || is_envelope_top {
                // Blue border
                rgba[idx] = 52;      // R
                rgba[idx + 1] = 120; // G
                rgba[idx + 2] = 246; // B
                rgba[idx + 3] = 255; // A
            } else if is_inner {
                // White interior
                rgba[idx] = 255;     // R
                rgba[idx + 1] = 255; // G
                rgba[idx + 2] = 255; // B
                rgba[idx + 3] = 255; // A
            } else {
                // Blue fill
                rgba[idx] = 52;      // R
                rgba[idx + 1] = 120; // G
                rgba[idx + 2] = 246; // B
                rgba[idx + 3] = 255; // A
            }
        }
    }

    tray_icon::Icon::from_rgba(rgba, size, size).context("Failed to create default icon")
}

/// Show a notification to the user.
fn show_notification(result: &ActionResult) {
    match result {
        ActionResult::Success(message) => {
            // Use rfd for cross-platform message dialog
            rfd::MessageDialog::new()
                .set_title("Email to Markdown")
                .set_description(message)
                .set_level(rfd::MessageLevel::Info)
                .show();
        }
        ActionResult::Error(message) => {
            rfd::MessageDialog::new()
                .set_title("Email to Markdown - Error")
                .set_description(message)
                .set_level(rfd::MessageLevel::Error)
                .show();
        }
    }
}
