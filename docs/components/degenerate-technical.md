# Degenerate - Technical Implementation Guide

## Overview

Degenerate fights the entropy of documentation by synchronizing documentation across multiple locations, detecting drift between source and copies, and maintaining sanity through automated validation and updates.

## Implementation Details

**Language**: Rust (2024 edition)
**CLI**: `degenerate` binary
**Version Control**: git2 (libgit2 bindings)
**Pattern**: Sync orchestrator with drift detection

### Key Technologies

- **clap**: CLI argument parsing
- **git2**: Git repository operations
- **serde + serde_json**: Configuration and state serialization
- **walkdir**: Recursive file traversal
- **glob**: Pattern matching

## Architecture & Design Patterns

### Sync Configuration

```rust
// src/config.rs
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
pub struct SyncConfig {
    pub sources: Vec<DocumentSource>,
    pub targets: Vec<SyncTarget>,
    pub rules: SyncRules,
}

#[derive(Serialize, Deserialize)]
pub struct DocumentSource {
    pub path: PathBuf,
    pub file_patterns: Vec<String>,  // e.g., ["*.md", "*.txt"]
    pub exclude_patterns: Vec<String>,  // e.g., ["**/node_modules/**"]
}

#[derive(Serialize, Deserialize)]
pub struct SyncTarget {
    pub name: String,
    pub path: PathBuf,
    pub sync_mode: SyncMode,  // OneWay, TwoWay, Mirror
}

#[derive(Serialize, Deserialize)]
pub enum SyncMode {
    OneWay,   // Source → Target only
    TwoWay,   // Bidirectional sync
    Mirror,   // Exact copy (deletes extras in target)
}
```

### Drift Detection

```rust
// src/drift.rs
use std::collections::HashMap;

pub struct DriftDetector {
    repo: Repository,
}

impl DriftDetector {
    pub fn detect_drift(
        &self,
        source: &Path,
        target: &Path
    ) -> Result<DriftReport, Error> {
        let source_files = self.scan_files(source)?;
        let target_files = self.scan_files(target)?;

        let mut report = DriftReport::default();

        // Find modified files
        for (path, source_hash) in &source_files {
            if let Some(target_hash) = target_files.get(path) {
                if source_hash != target_hash {
                    report.modified.push(DriftedFile {
                        path: path.clone(),
                        source_hash: source_hash.clone(),
                        target_hash: target_hash.clone(),
                        diff: self.generate_diff(source, target, path)?
                    });
                }
            } else {
                // File exists in source but not target
                report.missing_in_target.push(path.clone());
            }
        }

        // Find extra files in target
        for path in target_files.keys() {
            if !source_files.contains_key(path) {
                report.extra_in_target.push(path.clone());
            }
        }

        Ok(report)
    }

    fn scan_files(&self, root: &Path) -> Result<HashMap<PathBuf, String>, Error> {
        let mut files = HashMap::new();

        for entry in WalkDir::new(root) {
            let entry = entry?;
            if entry.file_type().is_file() {
                let path = entry.path();
                let hash = self.hash_file(path)?;
                files.insert(path.to_path_buf(), hash);
            }
        }

        Ok(files)
    }

    fn hash_file(&self, path: &Path) -> Result<String, Error> {
        use sha2::{Sha256, Digest};

        let content = fs::read(path)?;
        let hash = Sha256::digest(&content);
        Ok(format!("{:x}", hash))
    }
}

#[derive(Default)]
pub struct DriftReport {
    pub modified: Vec<DriftedFile>,
    pub missing_in_target: Vec<PathBuf>,
    pub extra_in_target: Vec<PathBuf>,
}

pub struct DriftedFile {
    pub path: PathBuf,
    pub source_hash: String,
    pub target_hash: String,
    pub diff: String,
}
```

### Sync Orchestrator

```rust
// src/sync.rs
pub struct SyncOrchestrator {
    config: SyncConfig,
}

impl SyncOrchestrator {
    pub async fn sync(&self) -> Result<SyncReport, Error> {
        let mut report = SyncReport::default();

        for source in &self.config.sources {
            for target in &self.config.targets {
                let sync_result = self.sync_source_to_target(source, target).await?;
                report.results.push(sync_result);
            }
        }

        Ok(report)
    }

    async fn sync_source_to_target(
        &self,
        source: &DocumentSource,
        target: &SyncTarget
    ) -> Result<SyncResult, Error> {
        let drift = DriftDetector::new()
            .detect_drift(&source.path, &target.path)?;

        let mut result = SyncResult {
            target_name: target.name.clone(),
            files_synced: 0,
            files_deleted: 0,
            errors: vec![],
        };

        match target.sync_mode {
            SyncMode::OneWay => {
                // Copy modified and missing files
                for file in &drift.modified {
                    self.copy_file(&file.path, source, target)?;
                    result.files_synced += 1;
                }

                for file in &drift.missing_in_target {
                    self.copy_file(file, source, target)?;
                    result.files_synced += 1;
                }

                // Leave extra files in target alone
            }

            SyncMode::Mirror => {
                // Same as OneWay, but also delete extra files
                self.sync_one_way(&drift, source, target, &mut result)?;

                for file in &drift.extra_in_target {
                    fs::remove_file(file)?;
                    result.files_deleted += 1;
                }
            }

            SyncMode::TwoWay => {
                // Bidirectional sync (conflict resolution required)
                self.sync_bidirectional(&drift, source, target, &mut result)?;
            }
        }

        Ok(result)
    }

    fn copy_file(
        &self,
        path: &Path,
        source: &DocumentSource,
        target: &SyncTarget
    ) -> Result<(), Error> {
        let source_path = source.path.join(path);
        let target_path = target.path.join(path);

        // Create parent directories
        if let Some(parent) = target_path.parent() {
            fs::create_dir_all(parent)?;
        }

        fs::copy(&source_path, &target_path)?;
        Ok(())
    }
}
```

### CLI Interface

```rust
// src/cli.rs
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "degenerate")]
#[command(about = "Fight documentation entropy")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Detect drift between source and targets
    Drift {
        #[arg(long)]
        config: PathBuf,
    },

    /// Sync documentation from sources to targets
    Sync {
        #[arg(long)]
        config: PathBuf,

        #[arg(long)]
        dry_run: bool,
    },

    /// Validate sync configuration
    Validate {
        #[arg(long)]
        config: PathBuf,
    },

    /// Initialize new sync configuration
    Init {
        #[arg(long)]
        output: Option<PathBuf>,
    },
}
```

## Configuration

```toml
# degenerate.toml
[[sources]]
path = "docs/source"
file_patterns = ["*.md", "*.txt"]
exclude_patterns = ["**/node_modules/**", "**/.git/**"]

[[targets]]
name = "component-a"
path = "../component-a/docs"
sync_mode = "OneWay"

[[targets]]
name = "component-b"
path = "../component-b/docs"
sync_mode = "Mirror"

[rules]
conflict_resolution = "PreferSource"  # or "PreferTarget", "Manual"
preserve_timestamps = true
```

## Usage

```bash
# Detect drift
degenerate drift --config degenerate.toml

# Output:
# Drift detected in 3 files:
# - docs/architecture.md (modified)
# - docs/api-reference.md (missing in target: component-a)
# - docs/legacy.md (extra in target: component-b)

# Sync documentation
degenerate sync --config degenerate.toml

# Output:
# Synced to component-a: 2 files
# Synced to component-b: 3 files (1 deleted)

# Dry run (preview changes)
degenerate sync --config degenerate.toml --dry-run

# Validate configuration
degenerate validate --config degenerate.toml
```

## Integration

### Git Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check for documentation drift
degenerate drift --config degenerate.toml

if [ $? -ne 0 ]; then
    echo "Documentation drift detected. Run 'degenerate sync' to fix."
    exit 1
fi
```

## Related Components

All 33GOD components with documentation should use Degenerate to keep docs synchronized.

---

**Quick Reference**:
- Binary: `degenerate`
- Config: `degenerate.toml`
- Repo: `33GOD/degenerate`
