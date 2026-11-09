mod icon;

fn main() {
    if std::env::var_os("CARGO_FEATURE_DESKTOP").is_none() {
        return;
    }
    println!("cargo:rerun-if-changed=../src/assets/app-icon.json");
    println!("cargo:rerun-if-changed=icon.rs");
    icon::write_icons(std::path::Path::new("icons")).expect("generate ATM terminal toolbox icons");
    tauri_build::try_build(tauri_build::Attributes::new().app_manifest(
        tauri_build::AppManifest::new().commands(&[
            "snapshot",
            "save_key",
            "delete_key",
            "save_target",
            "delete_target",
            "preview",
            "apply_preview",
            "cancel_preview",
            "list_backups",
            "preview_rollback",
            "infer_template",
            "save_template",
            "delete_template",
            "initialize_storage",
            "configure_codex_cli",
            "disconnect_codex_cli",
            "query_codex_usage",
            "query_glm_usage",
            "report_linux_smoke",
        ]),
    ))
    .expect("Tauri build configuration failed");
}
