Based on all of the research we just did please create a implementation plan in a file called coding-prompt.md
this will be the prompt we send to the actual coding agent, we expect this prompt to include all the relevant information from the research we just did. so the agent can reliably build the entire feature end to end including tests

We want to implement the new folder tool and the additions to the batch tool in one go

include all the core features we just discussed including:
Non-empty folder deletion (with force flag)
Wikilink auto-update on folder move
Add aioshutil for non-blocking operations
add symlink support

File format:

Describe the feature and the problem its solving:

User story:

State the solution and why we picked this approach:

List of relevant files from the codebase the agent MUST read to understand the codebase patterns:

List of relevant researched urls in the following format:

- [Documentation Link 1](https://example.com/doc1)
  - [Anchor tag]
  - [Short summary]

Implementation Plan:

- Foundational work needed:
- Core implementation needed:
- Integration work needed:

Step by step task list:

<For tool implementations:

- Define Pydantic schemas in `schemas.py`
- Implement tool with structured logging and type hints
- Register tool with Pydantic AI agent
- Create unit tests in `tests/tools/<name>/test_<module>.py`
- Add integration test in `tests/integration/` if needed>

Testing:
See `CLAUDE.md` for complete testing requirements.

Describe the testing strategy in detail:

- unit
- integration
- end-to-end

Edge cases for testing:

- [Edge case 1]
- [Edge case 2]

Acceptence criteria:

- [Acceptence criteria 1]
- [Acceptence criteria 2]

Validation:
list commands you'll use to validate with 100% confidence the feature is implemented correctly with zero regressions.
See README.md for linting and typechecking commands, include tests like unit and curl for e2e

When you have written the file in the above format, output a message with:

- List of the work you just did in a concise bullet
- Include a list to the file you created
