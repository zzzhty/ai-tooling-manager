//! Static declaration validation and a process bridge to the OMH-owned runtime protocol.
use crate::{Error, Result};
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeMap,
    ffi::OsString,
    fs,
    io::Read,
    path::{Component, Path, PathBuf},
    process::{Command, Stdio},
    sync::mpsc,
    thread,
    time::{Duration, Instant},
};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct RuntimeSpec {
    pub id: String,
    pub minimum_python: [u32; 2],
    #[serde(default)]
    pub requirements_lock: Option<String>,
    #[serde(default)]
    pub imports: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct PreparedRuntime {
    pub id: String,
    pub identity: String,
    pub root: PathBuf,
    pub python: PathBuf,
    pub external: bool,
    /// New managed environments record the explicit deployment root. Old
    /// receipts retain their original identities and default manager location.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub deployment_root: Option<PathBuf>,
}

fn invalid() -> Error {
    Error::new(
        "HARNESS_RUNTIME_SPEC",
        "Python payload 的 runtime 声明或锁定依赖无效。",
    )
}
fn python_missing() -> Error {
    Error::new(
        "HARNESS_PYTHON_REQUIRED",
        "选定 payload 需要声明版本的 Python；请显式提供可执行解释器绝对路径，ATM 不会下载解释器。",
    )
}
fn runtime_bad() -> Error {
    Error::new(
        "HARNESS_RUNTIME_INVALID",
        "Python payload 环境与声明不符；现有有效环境和引用保持不变。",
    )
}
fn portable_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 100
        && id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
}
fn is_link(metadata: &fs::Metadata) -> bool {
    if metadata.file_type().is_symlink() {
        return true;
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        if metadata.file_attributes() & 0x400 != 0 {
            return true;
        }
    }
    false
}
/// Refuse linked/reparse ancestors of locations ATM will write. Interpreters may
/// themselves be ordinary platform symlinks; no interpreter path is ever written.
fn checked_path(path: &Path) -> Result<()> {
    if !path.is_absolute() || path.components().any(|c| matches!(c, Component::ParentDir)) {
        return Err(invalid());
    }
    for ancestor in path.ancestors() {
        match fs::symlink_metadata(ancestor) {
            Ok(metadata) if is_link(&metadata) => return Err(invalid()),
            Ok(_) => {}
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(error.into()),
        }
    }
    Ok(())
}

fn lock_bytes(spec: &RuntimeSpec, bundle_root: &Path) -> Result<Vec<u8>> {
    if !portable_id(&spec.id)
        || spec.minimum_python[0] != 3
        || spec.minimum_python[1] < 11
        || spec.imports.iter().any(|name| {
            name.is_empty() || !name.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'_')
        })
    {
        return Err(invalid());
    }
    match &spec.requirements_lock {
        None => Ok(Vec::new()),
        Some(relative) => {
            let path = Path::new(relative);
            if relative.is_empty()
                || relative.contains('\\')
                || path
                    .components()
                    .any(|c| !matches!(c, Component::Normal(_)))
            {
                return Err(invalid());
            }
            let root = fs::canonicalize(bundle_root).map_err(Error::io)?;
            let full = root.join(path);
            checked_path(&full)?;
            let metadata = fs::metadata(&full).map_err(Error::io)?;
            if !metadata.is_file() || metadata.len() > 1024 * 1024 {
                return Err(invalid());
            }
            fs::read(full).map_err(Error::io)
        }
    }
}

/// Restricted, hash-locked requirement grammar. Index/URL/editable directives and
/// unpinned transitive dependencies are deliberately rejected before subprocesses.
pub fn validate_spec_lock(
    spec: &RuntimeSpec,
    bundle_root: &Path,
) -> Result<BTreeMap<String, String>> {
    parse_lock(&lock_bytes(spec, bundle_root)?)
}
fn parse_lock(bytes: &[u8]) -> Result<BTreeMap<String, String>> {
    let text = std::str::from_utf8(bytes).map_err(|_| invalid())?;
    let joined = text.replace("\\\r\n", " ").replace("\\\n", " ");
    let mut packages = BTreeMap::new();
    for line in joined.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let mut words = line.split_whitespace();
        let requirement = words.next().ok_or_else(invalid)?;
        let (name, version) = requirement.split_once("==").ok_or_else(invalid)?;
        if name.is_empty()
            || !name
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.'))
            || version.is_empty()
            || !version
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'+' | b'!' | b'-' | b'_'))
        {
            return Err(invalid());
        }
        let hashes: Vec<_> = words.collect();
        if hashes.is_empty()
            || hashes.iter().any(|hash| {
                hash.strip_prefix("--hash=sha256:").is_none_or(|digest| {
                    digest.len() != 64 || !digest.bytes().all(|c| c.is_ascii_hexdigit())
                })
            })
            || packages
                .insert(name.to_owned(), version.to_owned())
                .is_some()
        {
            return Err(invalid());
        }
    }
    Ok(packages)
}

fn bounded_run(program: &Path, args: &[OsString], timeout: Duration) -> Result<Vec<u8>> {
    let mut command = Command::new(program);
    command
        .args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        command.process_group(0);
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child = command.spawn().map_err(|_| python_missing())?;
    #[cfg(windows)]
    let _job = match crate::usage::process::WindowsJob::attach(&child) {
        Ok(job) => job,
        Err(_) => {
            let _ = child.kill();
            let _ = child.wait();
            return Err(runtime_bad());
        }
    };
    let mut stdout = child.stdout.take().ok_or_else(runtime_bad)?;
    let (sender, receiver) = mpsc::channel();
    thread::spawn(move || {
        let mut bytes = Vec::new();
        let mut buffer = [0; 8192];
        while let Ok(length) = stdout.read(&mut buffer) {
            if length == 0 {
                break;
            }
            let keep = length.min((65537usize).saturating_sub(bytes.len()));
            bytes.extend_from_slice(&buffer[..keep]);
        }
        let _ = sender.send(bytes);
    });
    let start = Instant::now();
    let mut output = None;
    loop {
        if output.is_none() {
            output = receiver.try_recv().ok();
        }
        match child.try_wait() {
            Ok(Some(status)) if output.is_some() => {
                let bytes = output.unwrap();
                return if status.success() && bytes.len() <= 65536 {
                    Ok(bytes)
                } else {
                    Err(runtime_bad())
                };
            }
            Err(_) => {
                let _ = child.kill();
                let _ = child.wait();
                return Err(runtime_bad());
            }
            _ => {}
        }
        if start.elapsed() >= timeout {
            #[cfg(unix)]
            unsafe {
                libc::kill(-(child.id() as i32), libc::SIGKILL);
            }
            let _ = child.kill();
            let _ = child.wait();
            return Err(Error::new(
                "HARNESS_RUNTIME_TIMEOUT",
                "Python payload 环境准备超时；旧引用未切换。",
            ));
        }
        thread::sleep(Duration::from_millis(10));
    }
}

// The provider is content-addressed with the selected OMH bundle. Static import
// validates bytes only; only explicit runtime preparation/verification executes it.
const PROVIDER: &str = "plugins/workflow/scripts/omh_runtime.py";
fn invoke(
    python: &Path,
    bundle: &Path,
    operation: &str,
    request: serde_json::Value,
) -> Result<PreparedRuntime> {
    if !python.is_absolute() || !python.is_file() {
        return Err(python_missing());
    }
    let provider = bundle.join(PROVIDER);
    if !provider.is_file() {
        return Err(Error::new(
            "HARNESS_RUNTIME_PROVIDER_REQUIRED",
            "此内容版本没有 OMH runtime 协议；请显式选择支持双模式的内容发布。",
        ));
    }
    let output = bounded_run(
        python,
        &[
            "-I".into(),
            "-B".into(),
            provider.into_os_string(),
            operation.into(),
            "--request".into(),
            request.to_string().into(),
        ],
        Duration::from_secs(480),
    )?;
    let value: serde_json::Value = serde_json::from_slice(&output).map_err(|_| runtime_bad())?;
    if let Some(error) = value.get("error") {
        let code = error["code"].as_str().unwrap_or("HARNESS_RUNTIME_INVALID");
        return Err(match code {
            "HARNESS_PYTHON_REQUIRED" => python_missing(),
            "HARNESS_RUNTIME_SPEC" => invalid(),
            "HARNESS_RUNTIME_BUSY" => Error::new(
                "HARNESS_RUNTIME_BUSY",
                "OMH runtime 正在准备或无法取得独占锁。",
            ),
            "HARNESS_RUNTIME_TIMEOUT" => Error::new(
                "HARNESS_RUNTIME_TIMEOUT",
                "OMH runtime 准备超时；旧引用保持不变。",
            ),
            "HARNESS_RUNTIME_OFFLINE_MISSING" => Error::new(
                "HARNESS_RUNTIME_OFFLINE_MISSING",
                "离线 wheel 缓存未满足锁定依赖。",
            ),
            _ => runtime_bad(),
        });
    }
    serde_json::from_value(value["ok"].clone()).map_err(|_| runtime_bad())
}

/// ATM supplies explicit bootstrap Python and runtime deployment root, distinct
/// from client skill targets. OMH performs all venv/dependency/probe operations.
pub fn prepare(
    manager_home: &Path,
    bundle_root: &Path,
    spec: &RuntimeSpec,
    interpreter: &Path,
    external_venv: Option<&Path>,
    offline: bool,
) -> Result<PreparedRuntime> {
    prepare_at(
        manager_home,
        bundle_root,
        spec,
        interpreter,
        external_venv,
        offline,
        &manager_home.join("runtimes"),
    )
}

pub fn prepare_at(
    manager_home: &Path,
    bundle_root: &Path,
    spec: &RuntimeSpec,
    interpreter: &Path,
    external_venv: Option<&Path>,
    offline: bool,
    deployment_root: &Path,
) -> Result<PreparedRuntime> {
    invoke(
        interpreter,
        bundle_root,
        "prepare",
        serde_json::json!({
            "protocol":1, "spec":spec, "python":interpreter,
            "deploymentRoot":deployment_root, "bundleRoot":bundle_root,
            "externalVenv":external_venv, "offline":offline,
            "wheelCache":manager_home.join("cache/wheels")
        }),
    )
}
/// Pure projection of the protocol binding. It starts no interpreter. The copied
/// OMH launcher owns override resolution, validation and script startup.
pub fn binding_artifacts(
    bundle: &super::source::Bundle,
    root: &Path,
    prepared: &BTreeMap<String, PreparedRuntime>,
) -> Result<Vec<super::Artifact>> {
    if !bundle.files.contains_key(PROVIDER) {
        return Ok(Vec::new());
    }
    let mut files = Vec::new();
    for name in ["omh_runtime.py", "run.sh", "run.ps1"] {
        files.push(super::Artifact {
            path: root.join(".omh-runtime").join(name),
            bytes: bundle
                .files
                .get(&format!("plugins/workflow/scripts/{name}"))
                .ok_or_else(invalid)?
                .clone(),
        });
    }
    for group in bundle.manifest["runtimeGroups"]
        .as_array()
        .ok_or_else(invalid)?
    {
        let spec: RuntimeSpec = serde_json::from_value(group.clone()).map_err(|_| invalid())?;
        if !portable_id(&spec.id) {
            return Err(invalid());
        }
        let locked = match &spec.requirements_lock {
            Some(path) => String::from_utf8(bundle.files.get(path).ok_or_else(invalid)?.clone())
                .map_err(|_| invalid())?,
            None => String::new(),
        };
        let binding = prepared.get(&spec.id);
        files.push(super::Artifact {
            path: root.join(".omh-runtime").join(format!("{}.json", spec.id)),
            bytes: serde_json::to_vec(
                &serde_json::json!({"protocol":1,"spec":spec,"prepared":binding,"lock":locked}),
            )
            .map_err(|_| invalid())?,
        });
        files.push(super::Artifact {
            path: root
                .join(".omh-runtime")
                .join(format!("{}.python", spec.id)),
            bytes: format!(
                "{}\n",
                binding
                    .map(|r| r.python.to_string_lossy().into_owned())
                    .unwrap_or_default()
            )
            .into_bytes(),
        });
    }
    Ok(files)
}
