#[path = "../icon.rs"]
mod icon;
use std::{fs, io::Cursor};

fn decode(bytes: &[u8]) -> (u32, Vec<u8>) {
    let mut reader = png::Decoder::new(Cursor::new(bytes)).read_info().unwrap();
    assert_eq!(reader.info().color_type, png::ColorType::Rgba);
    let mut pixels = vec![0; reader.output_buffer_size().unwrap()];
    let frame = reader.next_frame(&mut pixels).unwrap();
    assert_eq!(frame.width, frame.height);
    pixels.truncate(frame.buffer_size());
    (frame.width, pixels)
}

#[test]
fn native_containers_preserve_rgba_sizes_and_repeatable_exports() {
    let temp = tempfile::tempdir().unwrap();
    icon::write_icons(temp.path()).unwrap();
    let files: Vec<_> = fs::read_dir(temp.path())
        .unwrap()
        .map(|p| {
            let path = p.unwrap().path();
            let bytes = fs::read(&path).unwrap();
            let modified = fs::metadata(&path).unwrap().modified().unwrap();
            (path, bytes, modified)
        })
        .collect();
    icon::write_icons(temp.path()).unwrap();
    for (path, bytes, modified) in files {
        assert_eq!(fs::read(&path).unwrap(), bytes);
        assert_eq!(fs::metadata(path).unwrap().modified().unwrap(), modified);
    }
    let ico = fs::read(temp.path().join("icon.ico")).unwrap();
    assert_eq!(&ico[..6], &[0, 0, 1, 0, 8, 0]);
    for entry in ico[6..134].as_chunks::<16>().0 {
        let size = if entry[0] == 0 { 256 } else { entry[0] as u32 };
        let len = u32::from_le_bytes(entry[8..12].try_into().unwrap()) as usize;
        let offset = u32::from_le_bytes(entry[12..16].try_into().unwrap()) as usize;
        assert_eq!(decode(&ico[offset..offset + len]).0, size);
        assert_eq!(
            &ico[offset..offset + len],
            fs::read(temp.path().join(format!("icon-{size}.png"))).unwrap()
        );
    }
    let icns = fs::read(temp.path().join("icon.icns")).unwrap();
    assert_eq!(&icns[..4], b"icns");
    assert_eq!(
        u32::from_be_bytes(icns[4..8].try_into().unwrap()) as usize,
        icns.len()
    );
    let mut offset = 8;
    let expected = [
        (b"icp4", 16),
        (b"icp5", 32),
        (b"icp6", 64),
        (b"ic07", 128),
        (b"ic08", 256),
        (b"ic09", 512),
        (b"ic10", 1024),
        (b"ic11", 32),
        (b"ic12", 64),
        (b"ic13", 256),
        (b"ic14", 512),
    ];
    for (kind, size) in expected {
        assert_eq!(&icns[offset..offset + 4], kind);
        let len = u32::from_be_bytes(icns[offset + 4..offset + 8].try_into().unwrap()) as usize;
        assert_eq!(decode(&icns[offset + 8..offset + len]).0, size);
        assert_eq!(
            &icns[offset + 8..offset + len],
            fs::read(temp.path().join(format!("icon-{size}.png"))).unwrap()
        );
        offset += len;
    }
    assert_eq!(offset, icns.len());
    for size in [16, 20, 24, 32, 48, 64, 128, 256, 512, 1024] {
        let (width, pixels) =
            decode(&fs::read(temp.path().join(format!("icon-{size}.png"))).unwrap());
        assert_eq!(width, size);
        assert_eq!(pixels[3], 0, "transparent corners");
        assert!(
            pixels
                .as_chunks::<4>()
                .0
                .iter()
                .any(|p| p[3] > 0 && p[3] < 255),
            "antialiased edges"
        );
    }
    // Small-size regression: handle opening, lid seam and terminal prompt
    // must remain distinct after coverage sampling, not collapse into a blob.
    let (_, pixels) = decode(&fs::read(temp.path().join("icon-16.png")).unwrap());
    let pixel = |x: usize, y: usize| &pixels[(y * 16 + x) * 4..(y * 16 + x + 1) * 4];
    assert!(pixel(5, 3)[0] > 180 && pixel(5, 3)[1] < 140, "coral handle");
    assert!(pixel(8, 4)[0] < 40, "open handle");
    assert!(pixel(8, 6)[0] > 220, "white lid");
    assert!(pixel(8, 7)[0] < 100, "separate lid and body");
    assert!(pixel(12, 9)[0] > 220, "white body");
    assert!(pixel(7, 10)[0] < 100, "dark terminal chevron");
    assert!(
        pixel(9, 11)[0] > 220 && pixel(9, 11)[1] < 180,
        "coral cursor"
    );
}
