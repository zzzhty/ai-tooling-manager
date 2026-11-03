use atm_core::distribution::runtime::{self, RuntimeSpec};
use std::fs;

fn spec() -> RuntimeSpec {
    RuntimeSpec {
        id: "workflow".into(),
        minimum_python: [3, 11],
        requirements_lock: None,
        imports: vec![],
    }
}
#[test]
fn missing_python_fails_without_creating_state() {
    let temp = tempfile::tempdir().unwrap();
    let manager = temp.path().join("manager");
    assert_eq!(
        runtime::prepare(
            &manager,
            temp.path(),
            &spec(),
            &temp.path().join("missing-python"),
            None,
            true
        )
        .unwrap_err()
        .code,
        "HARNESS_PYTHON_REQUIRED"
    );
    assert!(!manager.exists());
}
#[test]
fn static_lock_validation_needs_no_python_and_confines_paths() {
    let temp = tempfile::tempdir().unwrap();
    let lock = temp.path().join("requirements.lock");
    let mut spec = RuntimeSpec {
        requirements_lock: Some("requirements.lock".into()),
        ..spec()
    };
    fs::write(
        &lock,
        format!("PyYAML==6.0.3 --hash=sha256:{}\n", "a".repeat(64)),
    )
    .unwrap();
    assert_eq!(
        runtime::validate_spec_lock(&spec, temp.path()).unwrap()["PyYAML"],
        "6.0.3"
    );
    for bad in [
        "PyYAML>=6\n",
        "--index-url https://example.test\n",
        "-r ../../requirements.txt\n",
        "PyYAML==6.0.3\n",
        "thing @ https://example.test/a.whl\n",
    ] {
        fs::write(&lock, bad).unwrap();
        assert!(runtime::validate_spec_lock(&spec, temp.path()).is_err());
    }
    for bad in ["../requirements.lock", r"C:\requirements.lock"] {
        spec.requirements_lock = Some(bad.into());
        assert!(runtime::validate_spec_lock(&spec, temp.path()).is_err());
    }
}

// Real provider execution belongs to OMH's cross-repository integration check.
// This Unix stub only observes the process protocol, never implements a venv.
#[cfg(unix)]
#[test]
fn bridge_passes_deployment_paths_as_one_json_argument_and_maps_errors() {
    use std::os::unix::fs::PermissionsExt;
    let temp = tempfile::Builder::new()
        .prefix("TEST_ONLY bridge 空 间 ")
        .tempdir()
        .unwrap();
    let manager = temp.path().join("manager");
    let python = temp.path().join("Python space");
    let provider = temp.path().join("plugins/workflow/scripts/omh_runtime.py");
    fs::create_dir_all(provider.parent().unwrap()).unwrap();
    fs::write(
        &provider,
        b"test-only provider path; stub does not execute it",
    )
    .unwrap();
    fs::write(&python,r#"#!/bin/sh
[ "$1" = "-I" ] && [ "$2" = "-B" ] && [ "$4" = "prepare" ] && [ "$5" = "--request" ] && [ "$#" = 6 ] || exit 2
/usr/bin/printf '%s' "$6" > "$0.request"
/usr/bin/printf '{"error":{"code":"HARNESS_RUNTIME_BUSY","message":"test-only busy"}}'
"#).unwrap();
    fs::set_permissions(&python, fs::Permissions::from_mode(0o755)).unwrap();
    let deployment = temp.path().join("runtime deployment 中文");
    let error = runtime::prepare_at(
        &manager,
        temp.path(),
        &spec(),
        &python,
        Some(&temp.path().join("external venv")),
        true,
        &deployment,
    )
    .unwrap_err();
    assert_eq!(error.code, "HARNESS_RUNTIME_BUSY");
    let request: serde_json::Value =
        serde_json::from_slice(&fs::read(python.with_file_name("Python space.request")).unwrap())
            .unwrap();
    assert_eq!(request["protocol"], 1);
    assert_eq!(request["deploymentRoot"], serde_json::json!(deployment));
    assert_eq!(request["bundleRoot"], serde_json::json!(temp.path()));
    assert_eq!(request["python"], serde_json::json!(python));
    assert_eq!(
        request["externalVenv"],
        serde_json::json!(temp.path().join("external venv"))
    );
    assert_eq!(request["offline"], true);
    assert!(!manager.exists());
    assert!(!deployment.exists());
    fs::remove_file(provider).unwrap();
    assert_eq!(
        runtime::prepare(&manager, temp.path(), &spec(), &python, None, true)
            .unwrap_err()
            .code,
        "HARNESS_RUNTIME_PROVIDER_REQUIRED"
    );
}
