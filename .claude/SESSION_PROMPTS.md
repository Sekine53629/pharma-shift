# Session Recovery Prompts

## Quick Resume (paste at session start)

```
Read CONTEXT.md, then run `git log --oneline -15` and `git status --short`.
Summarize the current project state and what I should work on next.
```

## Full Recovery (after long break or lost context)

```
I'm resuming work on this project. Please:
1. Read CONTEXT.md for the last known state
2. Run `git log --oneline -20` to see recent commits
3. Run `git diff --stat` to check uncommitted changes
4. Run `git branch --show-current` to confirm branch
5. Briefly summarize: where we left off, what's done, what's next
Then wait for my instructions.
```

## Pre-Compact Checkpoint (run before manual /compact)

```
Before I compact, please update CONTEXT.md with:
- Current task progress and subtask status
- All files modified in this session
- Any decisions we made and why
- Known issues we encountered
- Exact next steps to resume
Then commit CONTEXT.md.
```

## End-of-Session Wrap-up

```
Session is ending. Please:
1. Update CONTEXT.md with final state of all tasks
2. List any uncommitted changes
3. Commit CONTEXT.md with message "checkpoint: session end - [brief summary]"
4. Give me a one-paragraph summary of what was accomplished
```

## Post-Compact Verification

```
Context was just compacted. Please verify your state:
1. Read CONTEXT.md
2. Confirm you know: current branch, active task, last changes, next steps
3. If anything is unclear, tell me what's missing
```

## Task Switch Prompt

```
I'm switching to a different task. Before we switch:
1. Update CONTEXT.md with current task state
2. Commit with "checkpoint: pausing [task name]"
3. Then /clear and start fresh for the new task
```
