# Design Philosophy

## The Terminal Renaissance

The terminal is having a renaissance. Not because of nostalgia for green phosphor screens, but because the most powerful development tools of this era are text-native. Claude Code runs in your terminal. AI coding assistants stream their work as prose. Developers SSH into remote machines, pair through tmux, and live in the command line more than ever before.

We built graphical IDEs for decades. Now the most advanced coding tools run in monospace text.

In this world, there is a curious gap: we want to *see* things -- charts, images, diagrams, visual diffs -- without leaving the terminal. dapple exists to fill that gap.

## The LLM's Native Tongue

Large language models think in text. They read text, generate text, reason through text. There is exactly one computing interface that is pure text end to end: the terminal.

When an AI assistant needs to use a tool, it runs a command. When it needs to understand a tool, it reads `--help`. When it needs to compose operations, it pipes stdout into stdin. No adapters, no accessibility APIs, no screenshot-and-OCR loops. The interface between the LLM and the tool is the same interface you use: a text stream.

This is not a workaround. It is native fluency.

GUI tools require translation layers for AI agents. An LLM using a graphical application needs to capture the screen, interpret the pixels, map visual elements to semantic actions, and simulate clicks and keystrokes. Every step introduces latency and failure modes. The tool was designed for a human with a mouse; the LLM is working through an adapter.

CLI tools require no translation at all. The LLM reads the same help text you read, constructs the same commands you construct, and parses the same output you parse. The bandwidth between the LLM and the tool is the full capacity of the text stream -- structured data, error messages, progress indicators, everything.

Consider the asymmetry: to use a GUI tool, an AI agent needs a vision model, a screen interpreter, a mouse simulator, and a recovery strategy for when the interface changes. To use a CLI tool, it needs `subprocess.run()`.

## Why Text-Native Graphics Matter

AI assistants are remarkable at generating code, but they struggle to show you what they have created. Ask Claude to plot a function and it writes the matplotlib code. But you cannot *see* the plot without switching to a GUI, opening a window, breaking your flow.

This context-switching tax compounds. Remote sessions cannot spawn windows. Containers do not have displays. Screen sharing in pair programming shows terminals fine, but not the matplotlib figures one participant has open.

We need graphics that are *text*. Specifically, graphics that are:

- **Pipe-friendly**: Output that flows through Unix pipelines
- **Serializable**: Text that can be logged, diffed, version-controlled
- **Universal**: Characters that render in any terminal, any font, any platform
- **Inline**: Graphics that appear in the flow of text, not in separate windows

Unicode braille characters, block elements, and terminal graphics protocols all satisfy these constraints to varying degrees. dapple unifies them behind a single API so the tool author does not need to choose -- the user chooses at render time.

When an AI assistant renders a histogram inline with its explanation, it does not spawn a window. It does not save a file. It *says* the picture, inline with its text:

```
Here's the distribution of response times:

                          ...
                      ........
                  ................
..............................................

The p99 latency is 245ms, which suggests...
```

The graphic is part of the text stream. It travels over SSH. It appears in logs. It survives copy-paste. It works in containers, CI runners, and tmux sessions.

## Composability

Unix pipes are function composition. The `|` operator is `f . g` -- the composition operator from mathematics, made executable.

```bash
funcat "sin(x)" -j | funcat "cos(x)" -l
```

This reads: take the output of plotting sin(x), feed it as input to plotting cos(x), and render the combined result. LLMs already think in chains -- "first do X, then do Y with the result of X, then do Z with the result of Y." This is both how chain-of-thought reasoning works and how Unix pipelines work. The structural alignment is not coincidental.

JSON makes the data in those pipes inspectable. When a dapple tool outputs JSON instead of rendering, the output is a structured description of the current state. An LLM can read this, reason about it, and construct the next command accordingly.

```bash
funcat "sin(x)" -j | funcat "cos(x)" --color red -j | funcat "x/3" --color green -l
```

Each stage reads JSON from stdin, applies its operation, and outputs JSON for the next stage. The final stage renders with `-l`. An LLM constructing this pipeline reasons about each step: "Start with sin(x). Overlay cos(x) in red. Add a linear reference in green. Now render."

This is how an engineer thinks too. The CLI pipeline makes that reasoning explicit and executable.

## The Tool Philosophy

dapple and its CLI tools (imgcat, funcat, pdfcat, vidcat, mdcat, datcat, htmlcat) follow three principles that make them usable by both humans and AI agents.

### Help is documentation

Every tool ships with rich `--help` output that includes usage examples, not just flag descriptions. An LLM reading `imgcat --help` learns the tool's interface from the same source a human would. No separate API documentation required.

```bash
imgcat --help
```

The help text is the contract. If it is thorough enough for a human to use the tool without reading further documentation, it is thorough enough for an AI agent.

### Output is data

Every tool that produces structured output supports a `-j` flag for JSON mode. Without `-j`, the tool renders for a human. With `-j`, it emits structured data for the next stage in a pipeline or for machine consumption.

```bash
# Human mode: renders the plot to the terminal
funcat "sin(x)"

# Machine mode: emits JSON describing the plot state
funcat "sin(x)" -j
```

This one-character switch between "display for humans" and "emit structured data for machines" is the connective tissue of the entire toolkit. JSON output means the result is inspectable, debuggable, and -- critically -- LLM-readable.

### Errors are informative

When something goes wrong, the error message tells you what happened and what to do about it. Missing dependency? The error names the package and the pip command to install it. Invalid argument? The error shows the valid options. File not found? The error shows the path that was tried.

```python
raise ImportError(
    "matplotlib is required for MatplotlibAdapter. "
    "Install with: pip install matplotlib"
)
```

Informative errors are even more important for AI agents than for humans. A human can search the web for a cryptic error. An LLM works with what the error message gives it.

## Convergent Evolution

The resurgence of CLI tools is not nostalgia for an earlier era. It is convergent evolution.

When you design a tool for an agent that communicates through text, you arrive at the command line. When you design for composability, you arrive at Unix pipes. When you design for inspectability, you arrive at JSON. When you need graphics in a text-only environment, you arrive at Unicode encodings and ANSI colors.

These are the same design choices the Unix pioneers made, for the same fundamental reason: text is the universal interface. What has changed is not the principle -- it is the number of intelligent agents that operate through text. We have gone from humans at terminals to humans and LLMs at terminals. The tools that serve both well are the tools that take text seriously as a medium.

dapple is built on this conviction. One Canvas, pluggable renderers, stream-based output, immutable configuration, optional dependencies. Each decision follows from the premise that terminal graphics should be as composable, inspectable, and universal as the text they live alongside.

The terminal was always the right shape. Now we have more reasons to notice.
