# Releasing and privacy

**English** · [简体中文](../releasing.md)

The v0.1.0 release folder is reassembled from an allowlist of explicitly listed source files. Paths in the code and docs are parameters or generic templates; host-specific configuration lives in `*.local.json`.

The release contains the source code, configuration templates, docs, skill, tests and example media. Credentials, SSH configuration and keys, host fingerprint files, paths containing local user names, historical archives, raw deployment configuration, installed environments, large plugin and model files, remote jobs and logs all stay outside the package. WAV files keep only the PCM format and sample data; MIDI files are regenerated with the standard library and hold only performance events and part names.

```bash
python scripts/audit_release.py .
python scripts/build_release.py --out ../release-artifacts
```

The builder packages the pre-listed files and, once the audit passes, writes the ZIP, the tar.gz and their SHA-256 values. Archives use relative paths and fixed timestamps; file owners, extended attributes and Git history stay outside the archives. `MANIFEST.sha256` verifies the files inside the package, and the archives' own checksums are in the separate `SHA256SUMS.txt`.

The auditor checks for key formats, common tokens, personal folders, host-name patterns, private network addresses, excluded files and symbolic links. Its report lists only categories and relative file names, leaving any suspected credential values where they are. Pattern scans cover the common forms and work together with the allowlist assembly and a manual review.

The wheel contains the command-line tool. The full source ZIP/tar contains the skill, setup scripts, docs, tests and demos; use it to create the GitHub repository. Upload the contents of the release folder, and keep your working folder, installed environments and `config.local.json` on your own machine.
