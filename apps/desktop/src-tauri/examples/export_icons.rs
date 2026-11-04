#[path = "../icon.rs"]
mod icon;

fn main() -> std::io::Result<()> {
    let path = std::env::args_os()
        .nth(1)
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("icons"));
    icon::write_icons(&path)?;
    println!("Exported ATM icons to {}", path.display());
    Ok(())
}
