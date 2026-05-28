# Karpathy LLM Wiki

Build and maintain a personal knowledge base using LLMs. Ingest sources, compile structured wiki articles, query with citations, and lint for consistency. Based on Andrej Karpathy's idea that LLMs should maintain wikis rather than re-searching raw documents every time.

| | |
| --- | --- |
| **Owner** | CT AIA FRZ |
| **Version** | 1.0.0 |
| **Category** | Knowledge Management |
| **Requires** | Web access (for ingesting URLs) |
| **Compatible with** | GitHub Copilot, Claude Code |
| **Upstream** | [Astro-Han/karpathy-llm-wiki](https://github.com/Astro-Han/karpathy-llm-wiki) (MIT) |

## Installation

Download the `wiki` folder from the [AC Skills Marketplace](../) and place it in your project's skill directory:

| Platform | Scope | Install path |
| --- | --- | --- |
| GitHub Copilot | Project | `.github/skills/wiki/` |
| GitHub Copilot | Personal | `~/.copilot/skills/wiki/` |
| Claude Code | Project | `.claude/skills/wiki/` |
| Claude Code | Personal | `~/.claude/skills/wiki/` |

No dependencies, no credentials -- the skill works purely with local markdown files.

## Quick start

**1. Ingest your first source** -- give the skill a URL, a file, or pasted text:

> "Ingest this article: <https://example.com/attention-is-all-you-need>"

The skill stores the source in `raw/`, then compiles or updates the right knowledge pages in `wiki/`.

**2. Ask your wiki a question:**

> "What do I know about attention mechanisms?"

The skill searches the wiki and answers with citations linking back to your markdown pages.

**3. Keep the wiki healthy:**

> "Lint my wiki"

Checks for broken links, missing index entries, stale cross-references, and related issues.

## How it works

The skill manages two directories in your project:

- **`raw/`** -- Immutable source material organized by topic
- **`wiki/`** -- Compiled knowledge articles that compound over time

Three core operations:

| Operation | What it does |
| --- | --- | --- |
| **Ingest** | Fetch a source into `raw/`, compile it into a wiki article, cascade-update related articles |
| **Query** | Search the wiki and answer with citations; optionally archive answers as new wiki pages |
| **Lint** | Check index integrity, fix broken links, report heuristic quality issues |

## What's included

```text
wiki/
├── SKILL.md                          # AI instructions
├── README.md                         # This file
├── LICENSE                           # MIT (upstream)
└── references/
    ├── article-template.md           # Wiki article format
    ├── archive-template.md           # Archived query format
    ├── index-template.md             # Wiki index format
    └── raw-template.md               # Raw source format
```

## Credits

Forked from [Astro-Han/karpathy-llm-wiki](https://github.com/Astro-Han/karpathy-llm-wiki), licensed under MIT.

For the full skill reference, see [SKILL.md](./SKILL.md).

## License

Upstream: MIT. Internal distribution: Atlas Copco Group.
