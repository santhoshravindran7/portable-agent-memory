# /import-memory — Import Memories from a .pam File

Import memories from a portable `.pam` file — bring context from another AI agent or a previous export.

## Usage

```
/import-memory <filepath>
```

## Behavior

When the user runs `/import-memory`:

1. **Validate the file**: Check that the specified file exists and has a `.pam` extension.

2. **Call `pam_import`** with the filepath.

3. **Report results**: Show how many memories were imported, broken down by type (episodic, semantic, procedural, working).

4. **Verify integrity**: Call `pam_verify` to confirm the imported memories pass cryptographic verification.

5. **Summarize**: Briefly describe the imported context so the user knows what knowledge is now available.

## Examples

```
/import-memory project-context.pam
→ Imports memories from the file

/import-memory ~/shared/team-knowledge.pam
→ Imports shared team context
```

## Arguments

- `$ARGUMENTS` — Path to the `.pam` file to import. Required.
