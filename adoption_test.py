# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0
"""
Adoption test for cloud_dog_logging (PS-40).
Run check_adoption(project_root) to verify a project fully uses cloud_dog_logging.
"""
import pathlib
import subprocess


def _grep(pattern: str, search_path: pathlib.Path, extra_flags: str = "") -> list[str]:
    cmd = f"grep -rn {extra_flags} '{pattern}' {search_path} --include='*.py' | grep -v __pycache__ | grep -v '/archive/' | grep -v '/working/'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return [l for l in result.stdout.strip().split('\n') if l]


def _find_source_dirs(project_root: pathlib.Path) -> list[pathlib.Path]:
    dirs = []
    src = project_root / "src"
    if src.is_dir():
        dirs.append(src)
    crawler = project_root / "crawler"
    if crawler.is_dir():
        dirs.append(crawler)
    return dirs


def check_adoption(project_root: pathlib.Path) -> dict:
    results = {"pass": [], "fail": []}
    source_dirs = _find_source_dirs(project_root)

    if not source_dirs:
        results["fail"].append(f"No source directory found in {project_root}")
        return results

    # 1. cloud_dog_logging imported somewhere in source
    all_imports = []
    for sd in source_dirs:
        all_imports.extend(_grep("cloud_dog_logging", sd))
    for f in project_root.glob("start_*.py"):
        cmd = f"grep -n 'cloud_dog_logging' {f}"
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.stdout.strip():
            all_imports.extend(r.stdout.strip().split('\n'))
    if len(all_imports) > 0:
        results["pass"].append(f"cloud_dog_logging imported ({len(all_imports)} references)")
    else:
        results["fail"].append("cloud_dog_logging NOT imported anywhere in source")

    # 2. ZERO logging.getLogger in source (should use cloud_dog_logging.get_logger)
    bespoke_loggers = []
    for sd in source_dirs:
        hits = _grep("logging.getLogger", sd)
        for h in hits:
            # Allow if it's inside cloud_dog modules themselves
            if "cloud_dog_logging" not in h and "cloud_dog" not in h.split(":")[0]:
                bespoke_loggers.append(h)
    if len(bespoke_loggers) == 0:
        results["pass"].append("No bespoke logging.getLogger calls")
    else:
        results["fail"].append(f"logging.getLogger found (should use cloud_dog_logging.get_logger): {bespoke_loggers}")

    # 3. Structured JSON logging configured - check for setup_logging or setup_logger call
    setup_calls = []
    for sd in source_dirs:
        setup_calls.extend(_grep("setup_logging\\|setup_logger", sd))
    for f in project_root.glob("start_*.py"):
        cmd = f"grep -n 'setup_logging\\|setup_logger' {f}"
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.stdout.strip():
            setup_calls.extend(r.stdout.strip().split('\n'))
    if len(setup_calls) > 0:
        results["pass"].append(f"setup_logging/setup_logger called ({len(setup_calls)} references)")
    else:
        results["fail"].append("No setup_logging/setup_logger call found")

    # 4. server_id / service identity in log config (check defaults.yaml)
    defaults = project_root / "defaults.yaml"
    if defaults.exists():
        content = defaults.read_text()
        if "server_id" in content or "service_name" in content or "service_id" in content:
            results["pass"].append("server_id/service identity in defaults.yaml")
        else:
            results["fail"].append("No server_id/service identity in defaults.yaml logging config")

    # 5. Audit logging configured - check for get_audit_logger or AuditLogger
    audit_refs = []
    for sd in source_dirs:
        audit_refs.extend(_grep("get_audit_logger\\|AuditLogger\\|audit_logger", sd))
    if len(audit_refs) > 0:
        results["pass"].append(f"Audit logging configured ({len(audit_refs)} references)")
    else:
        results["fail"].append("No audit logger usage found (get_audit_logger/AuditLogger)")

    return results
