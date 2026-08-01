#!/usr/bin/env node
// Static checks for Mermaid blocks, plus a real parse via `mmdc` when it is on PATH.
//
//   node check-mermaid.mjs README.md docs/*.md diagram.mmd
//
// Exits 1 if any block has an error. Warnings never fail the run — they flag
// things that parse on current Mermaid but may not on the reader's renderer.
//
// Requires Node 18+. No dependencies.

import { readFileSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join, extname } from 'node:path';

// Opening keywords, mirroring the diagram detectors in
// packages/mermaid/src/diagrams/*/[*D]etector.ts on `develop`.
//   stable      — safe anywhere
//   aliased     — plain and `-beta` spellings both parse; `-beta` is the
//                 spelling older embedded renderers accept
//   beta        — the `-beta` suffix is mandatory and the type is recent
//   external    — needs a package registered by the host
const KEYWORDS = [
  [/^(flowchart|graph)\b/, 'stable'],
  [/^sequenceDiagram\b/, 'stable'],
  [/^classDiagram(-v2)?\b/, 'stable'],
  [/^stateDiagram(-v2)?\b/, 'stable'],
  [/^erDiagram\b/, 'stable'],
  [/^journey\b/, 'stable'],
  [/^gantt\b/, 'stable'],
  [/^pie\b/, 'stable'],
  [/^quadrantChart\b/, 'stable'],
  [/^requirement(Diagram)?\b/, 'stable'],
  [/^gitGraph\b/, 'stable'],
  [/^C4(Context|Container|Component|Dynamic|Deployment)\b/, 'stable'],
  [/^mindmap\b/, 'stable'],
  [/^timeline\b/, 'stable'],
  [/^kanban\b/, 'stable'],
  [/^eventmodeling\b/, 'stable'],
  [/^info\b/, 'stable'],
  [/^architecture(-beta)?\b/, 'aliased'],
  [/^block(-beta)?\b/, 'aliased'],
  [/^sankey(-beta)?\b/, 'aliased'],
  [/^packet(-beta)?\b/, 'aliased'],
  [/^xychart(-beta)?\b/, 'aliased'],
  [/^treemap(-beta)?\b/, 'aliased'],
  [/^ishikawa(-beta)?\b/i, 'aliased'],
  [/^radar-beta\b/, 'beta'],
  [/^venn-beta\b/, 'beta'],
  [/^wardley-beta\b/i, 'beta'],
  [/^cynefin-beta\b/, 'beta'],
  [/^treeView-beta\b/, 'beta'],
  [/^swimlane-beta\b/, 'beta'],
  [/^railroad(-(ebnf|abnf|peg))?-beta\b/i, 'beta'],
  [/^zenuml\b/, 'external'],
];

/** Pull every fenced `mermaid` block out of a Markdown file. */
function extractBlocks(text, path) {
  if (['.mmd', '.mermaid'].includes(extname(path).toLowerCase())) {
    return [{ path, line: 1, source: text }];
  }
  const blocks = [];
  const lines = text.split(/\r?\n/);
  let open = null;
  for (let i = 0; i < lines.length; i++) {
    const fence = /^(\s*)(```+|~~~+)\s*(\S*)/.exec(lines[i]);
    if (!fence) continue;
    if (open === null) {
      if (/^mermaid\b/i.test(fence[3])) open = { marker: fence[2][0], indent: fence[1], start: i };
    } else if (fence[2][0] === open.marker && !fence[3]) {
      blocks.push({
        path,
        line: open.start + 2,
        source: lines.slice(open.start + 1, i).map((l) => l.slice(open.indent.length)).join('\n'),
      });
      open = null;
    }
  }
  return blocks;
}

/** First line that declares the diagram type: past any frontmatter, comments and blanks. */
function headerLine(source) {
  let lines = source.split('\n');
  if (/^\s*---\s*$/.test(lines[0] ?? '')) {
    const close = lines.findIndex((l, i) => i > 0 && /^\s*---\s*$/.test(l));
    if (close > 0) lines = lines.slice(close + 1);
  }
  return lines.find((l) => l.trim() && !l.trim().startsWith('%%'))?.trim() ?? '';
}

function checkBlock(block) {
  const findings = [];
  const header = headerLine(block.source);
  const match = KEYWORDS.find(([re]) => re.test(header));

  if (!header) {
    findings.push(['error', 'block is empty']);
  } else if (!match) {
    findings.push(['error', `unrecognised opening keyword: ${JSON.stringify(header.split(/\s/)[0])}`]);
  } else if (match[1] === 'aliased' && !/-beta\b/.test(header)) {
    findings.push(['warn', 'plain keyword — the -beta spelling also parses and is what older renderers accept']);
  } else if (match[1] === 'beta') {
    findings.push(['warn', 'beta-only diagram type — confirm the target renderer is current enough']);
  } else if (match[1] === 'external') {
    findings.push(['warn', 'external diagram type — the host must register a separate package']);
  }

  if (/%%\{\s*init\s*:/.test(block.source)) {
    findings.push(['warn', '%%{init}%% is deprecated since v10.5.0 — use the frontmatter config: key']);
  }
  if (!/^\s*accTitle\s*:/m.test(block.source)) {
    findings.push(['warn', 'no accTitle: — the diagram has no accessible name']);
  }
  if (!/^\s*accDescr\s*[:{]/m.test(block.source)) {
    findings.push(['warn', 'no accDescr — the diagram has no accessible description']);
  }
  const odd = block.source
    .split('\n')
    .map((l, i) => [i, (l.match(/"/g) ?? []).length])
    .filter(([, n]) => n % 2 === 1);
  for (const [i] of odd) {
    findings.push(['warn', `odd number of double quotes on block line ${i + 1}`]);
  }
  return findings;
}

/** Real parse, only when mmdc is already installed — never auto-installs. */
function makeParser() {
  const probe = spawnSync('mmdc', ['--version'], { shell: process.platform === 'win32' });
  if (probe.status !== 0) return null;
  const dir = mkdtempSync(join(tmpdir(), 'mermaid-check-'));
  return {
    run(source) {
      const input = join(dir, 'block.mmd');
      writeFileSync(input, source, 'utf8');
      const out = spawnSync('mmdc', ['-i', input, '-o', join(dir, 'block.svg'), '-q'], {
        encoding: 'utf8',
        shell: process.platform === 'win32',
      });
      if (out.status === 0) return null;
      return (out.stderr || out.stdout || 'mmdc failed').trim().split('\n').slice(0, 3).join(' ');
    },
    cleanup: () => rmSync(dir, { recursive: true, force: true }),
  };
}

const files = process.argv.slice(2);
if (files.length === 0) {
  console.error('usage: node check-mermaid.mjs <file.md|file.mmd> ...');
  process.exit(2);
}

const parser = makeParser();
let errors = 0;
let warnings = 0;
let blocks = 0;

for (const path of files) {
  let text;
  try {
    text = readFileSync(path, 'utf8');
  } catch (err) {
    console.error(`ERROR ${path}: cannot read (${err.code ?? err.message})`);
    errors++;
    continue;
  }
  for (const block of extractBlocks(text, path)) {
    blocks++;
    const findings = checkBlock(block);
    if (parser) {
      const failure = parser.run(block.source);
      if (failure) findings.unshift(['error', `mmdc: ${failure}`]);
    }
    const where = `${path}:${block.line}`;
    if (findings.length === 0) {
      console.log(`PASS  ${where}`);
      continue;
    }
    for (const [level, message] of findings) {
      console.log(`${level === 'error' ? 'ERROR' : 'WARN '} ${where}  ${message}`);
      if (level === 'error') errors++;
      else warnings++;
    }
  }
}

parser?.cleanup();

const parseNote = parser ? 'rendered with mmdc' : 'static checks only — mmdc not on PATH, no diagram was rendered';
console.log(`\n${blocks} block(s), ${errors} error(s), ${warnings} warning(s) — ${parseNote}`);
process.exit(errors > 0 ? 1 : 0);
