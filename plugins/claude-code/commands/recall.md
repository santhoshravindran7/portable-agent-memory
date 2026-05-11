# /recall — Search Memories

Search your Portable Agent Memory for relevant context.

## Usage

```
/recall [query]
```

## Behavior

When the user runs `/recall`:

1. **Call `pam_recall`** with the provided query (or empty string to retrieve all memories).

2. **Display the results** in a clear, organized format grouped by memory type:
   - 🧠 **Semantic** (facts & preferences)
   - 📅 **Episodic** (events & interactions)
   - 📋 **Procedural** (workflows & how-tos)
   - 🎯 **Working** (current context & goals)

3. If no results are found, say so and suggest what kinds of things can be remembered.

4. If the query is empty, show a summary of all stored memories with counts by type.

## Examples

```
/recall deployment
→ Shows all memories related to deployment

/recall
→ Shows summary of all memories

/recall user preferences
→ Shows remembered preferences
```

## Arguments

- `$ARGUMENTS` — Optional search query. If omitted, returns all memories.
