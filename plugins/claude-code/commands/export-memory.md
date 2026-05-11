# /export-memory — Export Memories to a .pam File

Export all memories to a portable `.pam` file that can be shared with other AI agents or imported into another session.

## Usage

```
/export-memory [filepath]
```

## Behavior

When the user runs `/export-memory`:

1. **Determine the output path**:
   - If a filepath is provided, use it (add `.pam` extension if missing)
   - If no filepath, default to `./memory-export.pam`

2. **Call `pam_export`** with the filepath.

3. **Report results**: Show the file path, number of memories exported, and file size.

4. **Explain portability**: Briefly mention that this `.pam` file can be imported by any PAM-compatible AI agent (Claude, GPT, Gemini, etc.) using `/import-memory`.

## Examples

```
/export-memory
→ Exports to ./memory-export.pam

/export-memory project-context.pam
→ Exports to ./project-context.pam

/export-memory ~/backups/memory-2024.pam
→ Exports to specified path
```

## Arguments

- `$ARGUMENTS` — Optional file path for the export. Defaults to `./memory-export.pam`.
