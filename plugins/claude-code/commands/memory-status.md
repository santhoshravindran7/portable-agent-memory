# /memory-status — Show Memory Statistics

Display the current state of your Portable Agent Memory.

## Usage

```
/memory-status
```

## Behavior

When the user runs `/memory-status`:

1. **Call `pam_status`** to retrieve memory statistics.

2. **Display a formatted summary** including:
   - Total memory count
   - Breakdown by type (episodic, semantic, procedural, working)
   - Storage location and file size
   - Integrity status (verified or needs attention)
   - Last modified timestamp

3. **Format as a clean table or card**, for example:

```
📊 Portable Agent Memory Status
─────────────────────────────────
🧠 Semantic:    12 memories
📅 Episodic:    8 memories
📋 Procedural:  3 memories
🎯 Working:     2 memories
─────────────────────────────────
Total:          25 memories
Storage:        ~/.pam/memory.pam (4.2 KB)
Integrity:      ✅ Verified
Last updated:   2024-01-15T10:30:00Z
```

## Arguments

None.
