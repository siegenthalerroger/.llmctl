# .llmctl marketplace

The installable side of [`.llmctl`](https://github.com/siegenthalerroger/.llmctl), my collection of guidance for AI assistants. The plugins cover research, coding, infrastructure, product work and design. Pick the ones you need; adding the marketplace does not install the whole collection.

Start with [Before you start](#before-you-start), then choose your setup:

| Where you work | Install with |
| --- | --- |
| ChatGPT desktop, including Codex | [Desktop setup](#chatgpt-desktop) |
| Claude Desktop or Cowork | [Desktop setup](#claude-desktop) |
| Codex in the terminal | [Codex CLI](#codex-cli) |
| Claude Code | [Claude Code](#claude-code) |
| A project managed with APM | [APM](#apm) |

## Pick your plugins

| Plugin | What it helps with |
| --- | --- |
| `llmctl-core` | Research, troubleshooting, planning work and writing agent guidance |
| `llmctl-workflow` | Code delivery: TDD, worktrees, reviews, merge conflicts and linting |
| `llmctl-ops` | Helm, Kubernetes and OpenTofu/Terraform |
| `llmctl-product` | Writing epic and feature PRDs |
| `llmctl-design` | Design direction, colour, typography and presentations |
| `llmctl-travel` | Destination timing checks, trip planning, entry requirements and itineraries |

`core` is the general baseline. Add `workflow` for code work, and the domain plugins where they fit.

Each plugin carries a calendar version, `YYYY.M.N` — the year, the month, and which release of that package it was within the month. The catalogue in [apm.yml](apm.yml) lists what is published.

## Before you start

Install or update the assistant you want to use and sign in to it. For ChatGPT desktop and the terminal options below, you also need [Git](https://git-scm.com/downloads) so the app can download the marketplace.

Check Git in Terminal on macOS/Linux or PowerShell on Windows:

```sh
git --version
```

If it is missing, install it with `brew install git` on macOS with Homebrew, or `winget install --id Git.Git -e --source winget` on Windows. On Linux, use your distribution's package manager. Reopen your terminal and fully quit and reopen the desktop app after installation.

This repository is public. You do not need a GitHub login to download it over HTTPS. [GitHub CLI](https://cli.github.com/) is useful if you want to open issues or contribute a pull request later; it is not an installation prerequisite.

## Desktop setup

### ChatGPT desktop

Open the [ChatGPT desktop app](https://learn.chatgpt.com/docs/app) and go to **Plugins**.

1. Choose **Add marketplace**.
2. Enter the source below, use `main` for **Git ref**, and leave **Sparse paths** empty.
3. Add the marketplace, then select `llmctl-marketplace` and install the plugins you want.
4. Start a new conversation to use them.

```text
https://github.com/siegenthalerroger/.llmctl-marketplace.git
```

The desktop app can use the plugins in Codex. You do not need the Codex CLI for this setup. See OpenAI's [plugin guide](https://learn.chatgpt.com/docs/plugins) for supported surfaces and plugin management.

### Claude desktop

In [Claude Desktop](https://claude.com/download), open **Customize → Plugins**. For Cowork, open the Cowork tab first.

1. Under **Personal plugins**, open **+ → Add marketplace** (some versions label this menu **Add**).
2. Choose to add from a repository and enter the URL below.
3. Sync the marketplace, browse its plugins and install the ones you want.
4. Start a new conversation to use them.

```text
https://github.com/siegenthalerroger/.llmctl-marketplace.git
```

See Claude's [plugin guide](https://support.claude.com/en/articles/13837440-use-plugins-in-claude) for the current menus and available features.

### Give it a try

With `llmctl-core` installed and enabled, start a new conversation and ask:

```text
Help me turn a recurring correction I give my assistant into a reusable skill.
```

The assistant should use the authoring guidance and help you decide what belongs in the skill. If it does not find that guidance, check that the plugin is enabled and start a fresh conversation.

## Terminal and project setup

Run the shell commands in your terminal. Replace `PLUGIN_NAME` with a name from the [plugin table](#pick-your-plugins), such as `llmctl-core`.

### Codex CLI

Install the [Codex CLI](https://developers.openai.com/codex/cli/) if you do not have it, then run:

```sh
codex plugin marketplace add https://github.com/siegenthalerroger/.llmctl-marketplace.git
codex plugin add PLUGIN_NAME@llmctl-marketplace
codex plugin list
```

Start a new Codex session after installation. Within a session, `/plugins` opens the plugin browser.

### Claude Code

Install [Claude Code](https://code.claude.com/docs/en/setup), then run:

```sh
claude plugin marketplace add https://github.com/siegenthalerroger/.llmctl-marketplace.git
claude plugin install PLUGIN_NAME@llmctl-marketplace
```

If you already have a Claude Code conversation open, use these commands there instead:

```text
/plugin marketplace add https://github.com/siegenthalerroger/.llmctl-marketplace.git
/plugin install PLUGIN_NAME@llmctl-marketplace
```

Start a new session after installation. Use `/plugin` to browse and manage plugins.

### APM

Use [APM](https://github.com/microsoft/apm#installation) to manage a project's dependencies in `apm.yml` and `apm.lock.yaml`. Install it first, then register the marketplace:

```sh
apm marketplace add https://github.com/siegenthalerroger/.llmctl-marketplace.git --name llmctl-marketplace
apm marketplace browse llmctl-marketplace
```

From your project directory, install the plugin for your assistant:

```sh
apm install "PLUGIN_NAME@llmctl-marketplace" --target codex
```

Use `--target claude` or `--target copilot` for those tools, or a comma-separated list such as `--target codex,claude`. Add `-g` if you want a user-level installation instead of a project dependency.

For a shared project, commit the resulting `apm.yml` and `apm.lock.yaml`. APM records a concrete Git dependency and its resolved version, so another checkout can install it with:

```sh
apm install --frozen --target codex
```

See the [APM marketplace reference](https://microsoft.github.io/apm/reference/cli/marketplace/) for discovery and update commands.

## What to expect

Skills and commands are the main content to expect from these bundles. The bundles also carry agents and instructions, but which components load depends on the host. If you need direct deployment of the source package's agents, rules or MCP configuration, use the [source README's APM instructions](https://github.com/siegenthalerroger/.llmctl#deploy).

## Improve the guidance

Corrections and ideas belong in [`.llmctl`](https://github.com/siegenthalerroger/.llmctl). Open an issue with what you asked the assistant to do and what needed correcting, or send a focused PR. A rough draft is welcome.

The plugin bundles, marketplace manifests and [third-party notices](THIRD-PARTY-NOTICES.md) are generated from that source. Edit the source files under `packages/`; the [development and publishing guide](https://github.com/siegenthalerroger/.llmctl#developing-and-publishing) explains how to work on them and regenerate this repository.

## Licensing

Split, inherited from `.llmctl` — **CC-BY-SA-4.0** for the markdown content (skills, agents, instructions, references) and **MIT** for scripts and config. See [LICENSE](LICENSE); full texts are in [LICENSES/](LICENSES/) and inside every bundle.

The content half is copyleft: adapt a skill from a bundle and your adaptation must be CC-BY-SA-4.0 too, with attribution and a note that you changed it. Using it as-is, commercially or not, is unrestricted.

Two things are **not** covered by that split, and both are enumerated in the generated [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md): files carrying their own `license:` frontmatter field, and the third-party skills bundles vendor as APM dependencies (MIT and Apache-2.0). Each bundle ships only the licence texts it actually needs, plus an `apm.lock.yaml` recording the upstream `repo_url`, resolved commit, and a SHA-256 for every file it carries.
