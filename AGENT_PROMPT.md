# 🤖 AI Agent Initial Prompt

Use this prompt when starting a new AI agent session to implement the OVOS-EnMS project.

---

## First Prompt (Context Review)

```
I'm working on an industrial voice assistant project that integrates Open Voice OS (OVOS) with an Energy Management System (EnMS).

I'm attaching three critical documents:

1. **Master Plan** (OVOS-ENMS-ULTIMATE-IMPLEMENTATION.md) - The authoritative 6-week implementation roadmap
2. **EnMS API Documentation** (ENMS-API-DOCUMENTATION-FOR-OVOS.md) - Complete API reference with 90+ endpoints
3. **Test Questions** (test-questions.md) - 118 test queries we need to handle

Please carefully review all three documents and confirm:

1. You understand the project architecture (LLM-first with Qwen3-1.7B, zero-trust validator, multi-tier routing)
2. You understand the integration model (external OVOS skill, no core modifications)
3. You understand the current phase (Phase 1 - LLM Core & EnMS Integration)
4. You understand the current milestone (Week 1 - Skill Scaffold + LLM Parser + Validator)
5. You understand the agent workflow (9-step core loop in the master plan)

After reviewing, provide a brief summary of:
- The project goal
- The current phase and deliverable
- The next 3-5 tasks you'll work on
- Any questions or clarifications you need before starting

Do NOT start implementing yet. Just review and confirm understanding.
```

---

## Second Prompt (Start Implementation)

After the agent confirms full understanding, use this prompt to begin:

```
Perfect! Now let's begin implementation.

Please follow the Agent Workflow defined in the master plan:

1. Open the master plan (OVOS-ENMS-ULTIMATE-IMPLEMENTATION.md)
2. Locate the current milestone: Week 1 – Skill Scaffold + LLM Parser + Validator
3. Work through tasks in listed order (Days 1-2, then 3-4, then 5-7)
4. Mark completed tasks with [x] in the master plan
5. Update the "Last Updated" timestamp after each work session
6. Log key decisions to Decision_Log.md
7. Update your internal TODO list
8. After finishing the current task or milestone, immediately move to the next one

Start with Days 1-2: Environment & Skill Scaffold.

Important reminders:
- This is a real implementation, not a tutorial
- Create actual working code, not placeholders
- Test each component as you build it
- Update the master plan checkboxes as you complete tasks
- Continue autonomously through all tasks unless you hit a blocker

Begin now with the first unchecked task in Week 1, Days 1-2.
```

---

## Notes for the Agent Session

- **Workspace**: `/home/ubuntu/ovos/`
- **Master Plan Location**: `docs/OVOS-ENMS-ULTIMATE-IMPLEMENTATION.md`
- **EnMS API Docs**: `docs/ENMS-API-DOCUMENTATION-FOR-OVOS.md`
- **Test Queries**: `docs/test-questions.md`

The agent should:
- Create `enms-ovos-skill/` directory structure
- Implement actual Python code with proper types (Pydantic, mypy)
- Create `Decision_Log.md` when making first architectural decision
- Update master plan progress regularly
- Continue autonomously until phase completion or hitting a blocker

---

## Expected Agent Behavior

### ✅ Good Agent
- Reads all three documents thoroughly
- Summarizes understanding before starting
- Marks checkboxes as tasks complete
- Creates real, working code
- Tests components
- Updates timestamps
- Logs decisions
- Moves to next task without prompting

### ❌ Bad Agent
- Skips reading documentation
- Starts coding without understanding architecture
- Creates placeholder code ("# TODO: implement this")
- Doesn't update master plan checkboxes
- Waits for permission to continue
- Doesn't test code
- Ignores the agent workflow

---

**Ready to launch! 🚀**
