# /remember — Store a Memory

Store information in your Portable Agent Memory for future sessions.

## Usage

```
/remember <text to remember>
```

## Behavior

When the user runs `/remember`, do the following:

1. **Analyze the text** to determine the best memory type:
   - If it describes an event or something that happened → `episodic`
   - If it states a fact, preference, or piece of knowledge → `semantic`
   - If it describes a process, workflow, or how-to → `procedural`
   - If it describes current goals, tasks, or work in progress → `working`

2. **Call `pam_remember`** with the text and determined type.

3. **Confirm** what was stored in a brief, friendly message. Include the memory type used.

## Examples

```
/remember I prefer dark mode and Fira Code font
→ Stores as semantic: "User prefers dark mode and Fira Code font"

/remember We decided to use PostgreSQL instead of MongoDB for the user service
→ Stores as episodic: decision event

/remember To deploy: run make build, then kubectl apply -f k8s/prod/
→ Stores as procedural: deployment workflow

/remember Currently working on the auth module, need to finish JWT refresh
→ Stores as working: current task context
```

## Arguments

- `$ARGUMENTS` — The text to remember. Required.
