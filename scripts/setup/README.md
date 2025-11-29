# Setup Scripts

This directory contains one-time setup and migration scripts used during initial project configuration.

## Contents

### **git-init.sh**
Initialize git repository with basic configuration.

```bash
./scripts/setup/git-init.sh
```

### **init-git.sh**
Alternative git initialization script with extended setup.

```bash
./scripts/setup/init-git.sh
```

### **migrate-from-archive.sh**
Migration script used to move code from legacy Archive directory structure to current project layout.

```bash
./scripts/setup/migrate-from-archive.sh
```

## Usage

These scripts were primarily used during initial project setup and are kept for reference.

**For new installations**, use the main setup workflow documented in [../../README.md](../../README.md#-démarrage-rapide) instead.

## Note

Most of these scripts are **one-time use** and have already been executed. They are kept for:
- Historical reference
- Re-setup scenarios (fresh environments)
- Understanding project migration history
