//! Deterministic native exports from the same geometry used by the web header.
//! No raster master, platform color branches or external image tools.
use serde::Deserialize;
use std::{fs, io, path::Path};

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct RoundedRect {
    x: f64,
    y: f64,
    width: f64,
    height: f64,
    radius: f64,
    bottom_radius: Option<f64>,
}

impl RoundedRect {
    fn contains(&self, x: f64, y: f64) -> bool {
        if x < self.x || y < self.y || x > self.x + self.width || y > self.y + self.height {
            return false;
        }
        let bottom = self.bottom_radius.unwrap_or(self.radius);
        for (cx, cy, radius, corner) in [
            (
                self.x + self.radius,
                self.y + self.radius,
                self.radius,
                x < self.x + self.radius && y < self.y + self.radius,
            ),
            (
                self.x + self.width - self.radius,
                self.y + self.radius,
                self.radius,
                x > self.x + self.width - self.radius && y < self.y + self.radius,
            ),
            (
                self.x + bottom,
                self.y + self.height - bottom,
                bottom,
                x < self.x + bottom && y > self.y + self.height - bottom,
            ),
            (
                self.x + self.width - bottom,
                self.y + self.height - bottom,
                bottom,
                x > self.x + self.width - bottom && y > self.y + self.height - bottom,
            ),
        ] {
            if corner && (x - cx).powi(2) + (y - cy).powi(2) > radius.powi(2) {
                return false;
            }
        }
        true
    }
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Design {
    size: f64,
    background: RoundedRect,
    gradient_start: [u8; 3],
    gradient_end: [u8; 3],
    foreground: [u8; 3],
    accent: [u8; 3],
    shapes: Vec<Shape>,
}

#[derive(Deserialize)]
#[serde(rename_all = "lowercase")]
enum Paint {
    Foreground,
    Accent,
    Background,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Shape {
    paint: Paint,
    rect: Option<RoundedRect>,
    #[serde(default)]
    points: Vec<[f64; 2]>,
    stroke_width: Option<f64>,
}

impl Shape {
    fn paint_at(&self, x: f64, y: f64) -> Option<&Paint> {
        let covered = if let Some(rect) = &self.rect {
            rect.contains(x, y)
        } else if let Some(width) = self.stroke_width {
            // Union of round-capped segments matches SVG round line joins.
            self.points.windows(2).any(|pair| {
                let [a, b] = [pair[0], pair[1]];
                let dx = b[0] - a[0];
                let dy = b[1] - a[1];
                let length_squared = dx * dx + dy * dy;
                let t = if length_squared == 0.0 {
                    0.0
                } else {
                    (((x - a[0]) * dx + (y - a[1]) * dy) / length_squared).clamp(0.0, 1.0)
                };
                (x - a[0] - t * dx).powi(2) + (y - a[1] - t * dy).powi(2) <= (width / 2.0).powi(2)
            })
        } else {
            false
        };
        covered.then_some(&self.paint)
    }
}

fn render(design: &Design, size: u32) -> Vec<u8> {
    // Sample each output size directly. Averaging covered samples (premultiplied
    // alpha) keeps transparent edges free of dark halos on light backgrounds.
    const SAMPLES: u32 = 4;
    let mut pixels = Vec::with_capacity((size * size * 4) as usize);
    for y in 0..size {
        for x in 0..size {
            let mut sum = [0.0; 3];
            let mut covered = 0;
            for sy in 0..SAMPLES {
                for sx in 0..SAMPLES {
                    let px =
                        (x as f64 + (sx as f64 + 0.5) / SAMPLES as f64) * design.size / size as f64;
                    let py =
                        (y as f64 + (sy as f64 + 0.5) / SAMPLES as f64) * design.size / size as f64;
                    if !design.background.contains(px, py) {
                        continue;
                    }
                    covered += 1;
                    let paint = design
                        .shapes
                        .iter()
                        .rev()
                        .find_map(|shape| shape.paint_at(px, py))
                        .unwrap_or(&Paint::Background);
                    let t = ((px + py) / (2.0 * design.size)).clamp(0.0, 1.0);
                    for (i, channel) in sum.iter_mut().enumerate() {
                        *channel += match paint {
                            Paint::Foreground => design.foreground[i] as f64,
                            Paint::Accent => design.accent[i] as f64,
                            Paint::Background => {
                                design.gradient_start[i] as f64 * (1.0 - t)
                                    + design.gradient_end[i] as f64 * t
                            }
                        };
                    }
                }
            }
            for channel in sum {
                pixels.push(if covered == 0 {
                    0
                } else {
                    (channel / covered as f64).round() as u8
                });
            }
            pixels.push((covered as f64 * 255.0 / (SAMPLES * SAMPLES) as f64).round() as u8);
        }
    }
    pixels
}

fn png(design: &Design, size: u32) -> io::Result<Vec<u8>> {
    let mut bytes = Vec::new();
    {
        let mut encoder = png::Encoder::new(&mut bytes, size, size);
        encoder.set_color(png::ColorType::Rgba);
        encoder.set_depth(png::BitDepth::Eight);
        encoder
            .write_header()?
            .write_image_data(&render(design, size))?;
    }
    Ok(bytes)
}

fn write_changed(path: &Path, bytes: &[u8]) -> io::Result<()> {
    if !fs::read(path).is_ok_and(|previous| previous == bytes) {
        fs::write(path, bytes)?;
    }
    Ok(())
}

pub fn write_icons(directory: &Path) -> io::Result<()> {
    let design: Design = serde_json::from_str(include_str!("../src/assets/app-icon.json"))?;
    let sizes = [16u32, 20, 24, 32, 48, 64, 128, 256, 512, 1024];
    let images = sizes
        .iter()
        .map(|&size| png(&design, size))
        .collect::<io::Result<Vec<_>>>()?;
    fs::create_dir_all(directory)?;
    for (&size, bytes) in sizes.iter().zip(&images) {
        write_changed(&directory.join(format!("icon-{size}.png")), bytes)?;
    }
    // Tauri embeds this RGBA image for the Linux window and default app icon.
    write_changed(&directory.join("icon.png"), &images[7])?;

    // PNG-compressed ICO frames, supported by the Windows versions Tauri targets.
    let count = 8usize; // 16 through 256 pixels, including common display scaling.
    let mut ico = vec![0, 0, 1, 0];
    ico.extend((count as u16).to_le_bytes());
    let mut offset = (6 + 16 * count) as u32;
    for (&size, bytes) in sizes.iter().zip(&images).take(count) {
        ico.extend([size as u8, size as u8, 0, 0]); // 0 denotes 256.
        ico.extend(1u16.to_le_bytes());
        ico.extend(32u16.to_le_bytes());
        ico.extend((bytes.len() as u32).to_le_bytes());
        ico.extend(offset.to_le_bytes());
        offset += bytes.len() as u32;
    }
    for bytes in images.iter().take(count) {
        ico.extend(bytes);
    }
    write_changed(&directory.join("icon.ico"), &ico)?;

    let mut elements = Vec::new();
    for (kind, index) in [
        (b"icp4", 0),
        (b"icp5", 3),
        (b"icp6", 5),
        (b"ic07", 6),
        (b"ic08", 7),
        (b"ic09", 8),
        (b"ic10", 9),
        (b"ic11", 3),
        (b"ic12", 5),
        (b"ic13", 7),
        (b"ic14", 8),
    ] {
        let bytes = &images[index];
        elements.extend(kind);
        elements.extend(((bytes.len() + 8) as u32).to_be_bytes());
        elements.extend(bytes);
    }
    let mut icns = b"icns".to_vec();
    icns.extend(((elements.len() + 8) as u32).to_be_bytes());
    icns.extend(elements);
    write_changed(&directory.join("icon.icns"), &icns)
}
