# Coding Agent Prompts and Platform

Deliverables (a) and (b). Record every prompt given to a coding agent, in order, with the date and who in the team ran it. Paste prompts exactly as typed.

## Platform

| Item | Detail |
|---|---|
| Editor used in the lab | VSCode on Ubuntu (Classroom 2) |
| Coding agent for the initial build | Claude (Cowork mode, Anthropic) |
| Coding agent inside VSCode | _fill in: e.g. GitHub Copilot / Claude Code / Cline / none_ |
| Team members | Rajat, _member 2_, _member 3_ |

## Prompt log

### Session 1: scoping and full build (Claude Cowork)

**Prompt 1** (Rajat)
> Go through this file properly understand the scope of project. The working title and process is mentioned in the file itself, see if you can improve upon it if necessary. Let me know if your properly understand it all if not then ask questions for better understanding.
> Parser: Docling
> Use OllamaCloud and LlamaIndex

Attached: `AABA_Proj3.pdf` (earlier ChatGPT planning conversation with the project roadmap).

**Clarifications answered by the team:** Ubuntu is required by the faculty; documents will be synthetic, generated from a ground-truth fact sheet; adopt ablation experiments and a Streamlit UI and drop the analytics dashboard; the original faculty brief would be shared.

**Prompt 2** (Rajat)
> [Pasted the full faculty brief]
> Please note: Ubuntu is installed in lab (Classroom 2) so I'll be making the project there instead of my MacBook.

**Clarifications answered:** lab has sudo, Docker and persistent files; add role-based access; deadline under 2 days.

**Prompt 3** (Rajat)
> Yes start

The agent then produced: the synthetic corpus generator and fact sheet, the Docling parser with catalogue and SHA-256 skip logic, the fidelity validator, LlamaIndex indexing into Qdrant with table-row nodes, the RAG engine with role filters, department fan-out, citations and not-found handling, the Ollama Cloud client with cache and retry, the Streamlit app, the evaluation and ablation runner, the vector DB benchmark, `setup.sh` and the docs in this folder.

### Session 2: lab run and fixes (fill in)

| # | Date | Member | Tool | Prompt (exact text) | What changed |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |

## Notes on how the agent was used

- The team reviewed and ran every generated file on the lab machine before submission.
- Evaluation numbers in the report come only from runs on the lab machine, not from the agent's sandbox.
- _Add anything the team changed by hand._
