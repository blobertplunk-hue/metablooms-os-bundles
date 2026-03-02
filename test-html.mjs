#!/usr/bin/env node
/**
 * test-html.mjs — MetaBlooms HTML test runner
 *
 * Usage:
 *   node test-html.mjs <file.html|glob> [...files] [options]
 *
 * Options:
 *   --verbose              Print all pass results, not just failures/warnings
 *   --help, -h             Show this help message
 *   --no-browser           Skip Playwright + axe layers (static checks only)
 *   --fail-on-warnings     Exit code 1 if there are any warnings
 *   --timeout=<ms>         Per-layer timeout in milliseconds (default: 30000)
 *   --output=<path>        Write report to a specific path (overrides default)
 *   --format=<type>        Output format: json (default), html, junit
 *   --viewports=<list>     Comma-separated WxH breakpoints (default: 1280x800,375x812,768x1024)
 *   --watch                Re-run when input files change (polling every 1500ms)
 *
 * Layers:
 *   1. html-validate  — static structural validation
 *   2. Static patterns — security/quality regex checks with line numbers
 *   3. Playwright     — real Chromium headless execution
 *   4. axe-core       — WCAG 2A/2AA/2.1A/2.1AA/2.2AA accessibility audit
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync, statSync } from 'fs';
import { resolve, basename, dirname } from 'path';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);

// ─────────────────────────────────────────────
// STEP 1: CLI Argument parsing + --help
// ─────────────────────────────────────────────

function parseArgs(argv) {
  const flags = {
    verbose: false,
    help: false,
    noBrowser: false,
    failOnWarnings: false,
    watch: false,
    timeout: 30000,
    output: null,
    format: 'json',
    viewports: ['1280x800', '375x812', '768x1024'],
  };
  const files = [];

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--verbose' || a === '-v')       flags.verbose = true;
    else if (a === '--help' || a === '-h')      flags.help = true;
    else if (a === '--no-browser')             flags.noBrowser = true;
    else if (a === '--fail-on-warnings')        flags.failOnWarnings = true;
    else if (a === '--watch')                   flags.watch = true;
    else if (a === '--timeout')                 flags.timeout = parseInt(argv[++i], 10);
    else if (a.startsWith('--timeout='))        flags.timeout = parseInt(a.slice('--timeout='.length), 10);
    else if (a === '--output')                  flags.output = argv[++i];
    else if (a.startsWith('--output='))         flags.output = a.slice('--output='.length);
    else if (a === '--format')                  flags.format = argv[++i];
    else if (a.startsWith('--format='))         flags.format = a.slice('--format='.length);
    else if (a === '--viewports')               flags.viewports = argv[++i].split(',');
    else if (a.startsWith('--viewports='))      flags.viewports = a.slice('--viewports='.length).split(',');
    else if (!a.startsWith('--'))               files.push(a);
  }

  return { flags, files };
}

const { flags, files: rawFiles } = parseArgs(process.argv.slice(2));

if (flags.help) {
  console.log(`
Usage: node test-html.mjs <file.html|glob> [...files] [options]

Options:
  --verbose              Print all pass results, not just failures/warnings
  --help, -h             Show this help message
  --no-browser           Skip Playwright + axe layers (static checks only)
  --fail-on-warnings     Exit code 1 if there are any warnings
  --timeout=<ms>         Per-layer timeout in milliseconds (default: 30000)
  --output=<path>        Write report to a specific path (overrides default)
  --format=<type>        Output format: json (default), html, junit
  --viewports=<list>     Comma-separated WxH breakpoints (default: 1280x800,375x812,768x1024)
  --watch                Re-run when input files change (polling every 1500ms)

Examples:
  node test-html.mjs index.html --verbose
  node test-html.mjs "src/**/*.html" --format=html --fail-on-warnings
  node test-html.mjs a.html b.html --no-browser --format=junit
  node test-html.mjs index.html --watch

Config file (.htmltesterrc.json):
  {
    "timeout": 30000,
    "format": "json",
    "failOnWarnings": false,
    "noBrowser": false,
    "viewports": ["1280x800", "375x812"],
    "outputDir": "./test-reports",
    "layer1": { "extraRules": {} },
    "layer2": { "extraPatterns": [] },
    "performanceThresholds": { "domContentLoaded": 3000, "loadComplete": 5000 }
  }
`);
  process.exit(0);
}

if (rawFiles.length === 0) {
  console.error('Usage: node test-html.mjs <file.html> [--verbose]');
  process.exit(1);
}

// ─────────────────────────────────────────────
// STEP 2: Config file loading (.htmltesterrc.json)
// ─────────────────────────────────────────────

function loadConfig(cwd) {
  const configPath = resolve(cwd, '.htmltesterrc.json');
  if (!existsSync(configPath)) return {};
  try {
    return JSON.parse(readFileSync(configPath, 'utf8'));
  } catch (e) {
    console.warn(`[config] Failed to parse .htmltesterrc.json: ${e.message}`);
    return {};
  }
}

const fileConfig = loadConfig(process.cwd());

// Merge config file into flags (CLI flags take precedence)
if (fileConfig.timeout != null && flags.timeout === 30000)         flags.timeout = fileConfig.timeout;
if (fileConfig.format && flags.format === 'json')                  flags.format = fileConfig.format;
if (fileConfig.failOnWarnings && !flags.failOnWarnings)            flags.failOnWarnings = fileConfig.failOnWarnings;
if (fileConfig.noBrowser && !flags.noBrowser)                     flags.noBrowser = fileConfig.noBrowser;
if (fileConfig.viewports && flags.viewports.join(',') === '1280x800,375x812,768x1024')
  flags.viewports = fileConfig.viewports;

const outDir = fileConfig.outputDir || './test-reports';

// ─────────────────────────────────────────────
// STEP 3: Timing infrastructure + run metadata
// ─────────────────────────────────────────────

const RUN_START = Date.now();

const runMeta = {
  startedAt: new Date().toISOString(),
  nodeVersion: process.version,
  platform: process.platform,
  cwd: process.cwd(),
  axeVersion: null,
  htmlValidateVersion: null,
};

try {
  const axePkg = JSON.parse(readFileSync('./node_modules/axe-core/package.json', 'utf8'));
  runMeta.axeVersion = axePkg.version;
} catch {}

try {
  const hvPkg = JSON.parse(readFileSync('./node_modules/html-validate/package.json', 'utf8'));
  runMeta.htmlValidateVersion = hvPkg.version;
} catch {}

// ─────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────

async function withTimeout(label, ms, fn) {
  return Promise.race([
    fn(),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`Layer "${label}" timed out after ${ms}ms`)), ms)
    ),
  ]);
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeXml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&apos;');
}

// STEP 5: Line-number-aware pattern finder
function findPatternWithLines(html, pattern) {
  const found = [];
  const lines = html.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const local = new RegExp(pattern.source, pattern.flags.replace('g', '') + 'g');
    let m;
    while ((m = local.exec(lines[i])) !== null) {
      found.push({ line: i + 1, col: m.index + 1, match: m[0] });
    }
  }
  return found;
}

// STEP 7: Multi-file glob resolution
async function resolveFiles(rawFiles) {
  const resolved = [];
  for (const pattern of rawFiles) {
    if (pattern.includes('*') || pattern.includes('?')) {
      try {
        const { glob } = await import('./node_modules/glob/dist/esm/index.js');
        const matches = await glob(pattern, { absolute: true });
        resolved.push(...matches);
      } catch {
        resolved.push(resolve(pattern));
      }
    } else {
      resolved.push(resolve(pattern));
    }
  }
  return [...new Set(resolved)];
}

// STEP 10: Scoring and grading
function computeScore(results) {
  const score = Math.max(0, 100 - results.failed.length * 10 - results.warnings.length * 3);
  let grade;
  if (score >= 95) grade = 'A+';
  else if (score >= 90) grade = 'A';
  else if (score >= 80) grade = 'B';
  else if (score >= 70) grade = 'C';
  else if (score >= 60) grade = 'D';
  else grade = 'F';
  return { score, grade };
}

// STEP 9: Group axe violations by impact
function groupAxeByImpact(violations) {
  const grouped = { critical: [], serious: [], moderate: [], minor: [] };
  for (const v of violations) {
    const key = v.impact || 'minor';
    (grouped[key] = grouped[key] || []).push(v);
  }
  return grouped;
}

// STEP 11: Diff vs previous run
function diffVsPreviousRun(results, reportDir, baseName) {
  try {
    if (!existsSync(reportDir)) return null;
    const files = readdirSync(reportDir)
      .filter(f => f.startsWith(baseName) && f.endsWith('.json'))
      .sort().reverse();
    if (files.length === 0) return null;
    const prev = JSON.parse(readFileSync(resolve(reportDir, files[0]), 'utf8'));
    return {
      previousReport: files[0],
      failedDelta:   results.failed.length   - (prev.failed?.length   ?? 0),
      warningsDelta: results.warnings.length - (prev.warnings?.length ?? 0),
      scoreDelta:    (results.score ?? 0)    - (prev.score            ?? 0),
      newFailures: results.failed.filter(f =>
        !prev.failed?.some(pf => pf.layer === f.layer && pf.msg === f.msg)),
      resolvedFailures: (prev.failed ?? []).filter(pf =>
        !results.failed.some(f => f.layer === pf.layer && f.msg === pf.msg)),
    };
  } catch {
    return null;
  }
}

// STEP 12: Report builders
function buildJsonReport(results, meta) {
  return JSON.stringify({ formatVersion: 2, meta, ...results }, null, 2);
}

function buildHtmlReport(results, meta) {
  const F = '#d32f2f', W = '#f57c00', P = '#388e3c';
  const violationsHtml = (results.axe?.violations || []).map(v => `
    <details>
      <summary style="color:${v.impact === 'critical' || v.impact === 'serious' ? F : W}">
        [${v.impact}] ${escapeHtml(v.id)}: ${escapeHtml(v.description)}
      </summary>
      <ul>${(v.nodes || []).map(n =>
        `<li><code>${escapeHtml(n.html || '')}</code><br><small>${escapeHtml(n.failureSummary || '')}</small></li>`
      ).join('')}</ul>
      ${v.helpUrl ? `<a href="${escapeHtml(v.helpUrl)}" target="_blank">More info ↗</a>` : ''}
    </details>`).join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HTML Test Report: ${escapeHtml(results.file)}</title>
  <style>
    body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#333}
    h1,h2{border-bottom:1px solid #eee;padding-bottom:.3rem}
    .score{font-size:3rem;font-weight:bold}
    .grAplus,.grA{color:${P}} .grB,.grC{color:${W}} .grD,.grF{color:${F}}
    table{width:100%;border-collapse:collapse;margin-bottom:1rem}
    th,td{text-align:left;padding:.5rem;border-bottom:1px solid #ddd}
    th{background:#f5f5f5}
    .fail{color:${F}} .warn{color:${W}} .pass{color:${P}}
    code{background:#f5f5f5;padding:.1em .3em;border-radius:3px;font-size:.9em;word-break:break-all}
    details{margin:.5rem 0} summary{cursor:pointer;padding:.3rem}
    pre{background:#f5f5f5;padding:1rem;border-radius:4px;overflow-x:auto;font-size:.85em}
    .badge{display:inline-block;padding:.2em .6em;border-radius:3px;color:#fff;font-size:.8em}
    .bf{background:${F}} .bw{background:${W}} .bp{background:${P}}
  </style>
</head>
<body>
  <h1>Test Report: <code>${escapeHtml(results.file)}</code></h1>
  <p>Run: ${meta.startedAt} | Duration: ${results.durationMs ?? 'N/A'}ms | Node ${meta.nodeVersion}</p>
  <p class="score gr${(results.grade || 'F').replace('+', 'plus')}">${results.score ?? '?'}/100
    <span style="font-size:1.5rem">(${results.grade ?? '?'})</span></p>
  <h2>Summary</h2>
  <table>
    <tr><th>Status</th><th>Count</th></tr>
    <tr><td><span class="badge bp">PASS</span></td><td>${results.passed.length}</td></tr>
    <tr><td><span class="badge bw">WARN</span></td><td>${results.warnings.length}</td></tr>
    <tr><td><span class="badge bf">FAIL</span></td><td>${results.failed.length}</td></tr>
  </table>
  <h2>Failures</h2>
  ${results.failed.length > 0
    ? results.failed.map(f => `<p class="fail">&#10060; [${escapeHtml(f.layer)}] ${escapeHtml(f.msg)}</p>`).join('')
    : '<p class="pass">None</p>'}
  <h2>Warnings</h2>
  ${results.warnings.length > 0
    ? results.warnings.map(w => `<p class="warn">&#9888; [${escapeHtml(w.layer)}] ${escapeHtml(w.msg)}</p>`).join('')
    : '<p class="pass">None</p>'}
  <h2>Accessibility (axe-core ${meta.axeVersion ?? 'unknown'})</h2>
  ${violationsHtml || '<p class="pass">No violations found.</p>'}
  ${results.performance ? `
  <h2>Performance</h2>
  <table>
    <tr><th>Metric</th><th>Value</th></tr>
    <tr><td>DOMContentLoaded</td><td>${results.performance.domContentLoaded ?? 'N/A'}ms</td></tr>
    <tr><td>Load Complete</td><td>${results.performance.loadComplete ?? 'N/A'}ms</td></tr>
    <tr><td>First Contentful Paint</td><td>${results.performance.firstContentfulPaint ?? 'N/A'}ms</td></tr>
  </table>` : ''}
  <h2>Environment</h2>
  <pre>${escapeHtml(JSON.stringify(meta, null, 2))}</pre>
</body>
</html>`;
}

function buildJunitReport(results, meta) {
  const cases = [
    ...results.failed.map(f => `    <testcase classname="${escapeXml(f.layer)}" name="${escapeXml(f.msg)}" time="0">
      <failure message="${escapeXml(f.msg)}" type="${escapeXml(f.layer)}"/>
    </testcase>`),
    ...results.warnings.map(w => `    <testcase classname="${escapeXml(w.layer)}" name="${escapeXml(w.msg)}" time="0">
      <skipped message="Warning: ${escapeXml(w.msg)}"/>
    </testcase>`),
    ...results.passed.map(p => `    <testcase classname="${escapeXml(p.layer)}" name="${escapeXml(p.msg)}" time="0"/>`),
  ];
  const total = results.passed.length + results.warnings.length + results.failed.length;
  return `<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="html-test" tests="${total}" failures="${results.failed.length}" time="${((results.durationMs ?? 0) / 1000).toFixed(3)}">
  <testsuite name="${escapeXml(results.file)}" timestamp="${meta.startedAt}" hostname="${meta.platform}">
${cases.join('\n')}
  </testsuite>
</testsuites>`;
}

function writeReport(results, meta, flags, fileName) {
  const ext = flags.format === 'junit' ? 'xml' : flags.format === 'html' ? 'html' : 'json';
  const baseName = fileName.replace(/\.html$/, '');
  const outPath = flags.output
    ? resolve(flags.output)
    : resolve(outDir, `${baseName}-${Date.now()}.${ext}`);
  mkdirSync(dirname(outPath), { recursive: true });
  let content;
  if (flags.format === 'html')  content = buildHtmlReport(results, meta);
  else if (flags.format === 'junit') content = buildJunitReport(results, meta);
  else content = buildJsonReport(results, meta);
  writeFileSync(outPath, content);
  return outPath;
}

// ─────────────────────────────────────────────
// STEP 6: Per-file test orchestrator
// ─────────────────────────────────────────────

async function testFile(absPath, flags) {
  const html = readFileSync(absPath, 'utf8');
  const fileName = basename(absPath);
  const fileStart = Date.now();

  const results = { file: fileName, passed: [], warnings: [], failed: [], timings: {} };

  function pass(layer, msg) {
    results.passed.push({ layer, msg });
    if (flags.verbose) console.log(`  ✅ [${layer}] ${msg}`);
  }
  function warn(layer, msg) {
    results.warnings.push({ layer, msg });
    console.log(`  ⚠️  [${layer}] ${msg}`);
  }
  function fail(layer, msg) {
    results.failed.push({ layer, msg });
    console.log(`  ❌ [${layer}] ${msg}`);
  }

  console.log(`\n=== Testing: ${fileName} ===\n`);

  // ─────────────────────────────────────────────
  // STEP 4: LAYER 1 — html-validate (expanded rules)
  // ─────────────────────────────────────────────
  console.log('[ Layer 1 ] html-validate (static structural)');
  const l1Start = Date.now();

  // STEP 13: Graceful missing dependency
  let HtmlValidate = null;
  try {
    ({ HtmlValidate } = await import('./node_modules/html-validate/dist/esm/index.js'));
  } catch (e) {
    warn('html-validate', `Dependency not available — run: npm install html-validate (${e.message})`);
  }

  if (HtmlValidate) {
    await withTimeout('html-validate', flags.timeout, async () => {
      try {
        const hv = new HtmlValidate({
          rules: {
            // Original
            'no-dup-id':            'error',
            'void-content':         'error',
            'close-order':          'error',
            'no-unknown-elements':  'off',
            'require-sri':          'off',
            // Document structure
            'missing-doctype':      'error',
            'empty-title':          'error',
            'no-multiple-main':     'error',
            // Content quality
            'empty-heading':        'error',
            'no-raw-characters':    'warn',
            // Style / quality
            'no-inline-style':      'warn',
            'attr-quotes':          'warn',
            // Accessibility
            'input-missing-label':  'error',
            // Scripts
            'script-type':          'warn',
            // Config-file extras
            ...((fileConfig.layer1 && fileConfig.layer1.extraRules) || {}),
          },
        });
        const report = await hv.validateString(html);
        if (report.valid) {
          pass('html-validate', 'No structural errors');
        } else {
          for (const result of report.results) {
            for (const msg of result.messages) {
              if (msg.severity === 2) fail('html-validate', `line ${msg.line}: ${msg.message}`);
              else warn('html-validate', `line ${msg.line}: ${msg.message}`);
            }
          }
        }
      } catch (e) {
        if (e.message.includes('parse') || e.message.includes('token')) {
          fail('html-validate', `HTML parse error — file may be malformed: ${e.message}`);
        } else {
          warn('html-validate', `Internal error: ${e.message}`);
        }
      }
    }).catch(e => warn('html-validate', e.message));

    // Deprecated element scan
    const deprecatedTags = ['center', 'font', 'marquee', 'blink', 'strike', 'tt', 'big', 'basefont', 'frame', 'frameset', 'noframes'];
    for (const tag of deprecatedTags) {
      const hits = html.match(new RegExp(`<${tag}[\\s>]`, 'gi'));
      if (hits) warn('html-validate', `Deprecated <${tag}> found (${hits.length}x) — use CSS instead`);
    }
  }

  results.timings.layer1Ms = Date.now() - l1Start;

  // ─────────────────────────────────────────────
  // STEP 5: LAYER 2 — Static patterns (expanded + line numbers)
  // ─────────────────────────────────────────────
  console.log('\n[ Layer 2 ] Static security/quality patterns');
  const l2Start = Date.now();

  const checks = [
    // Security
    { pattern: /\beval\s*\(/g,              label: 'eval() usage',                            level: 'fail', category: 'security' },
    { pattern: /new\s+Function\s*\(/g,      label: 'new Function() usage',                    level: 'fail', category: 'security' },
    { pattern: /innerHTML\s*=/g,            label: 'innerHTML assignment',                     level: 'warn', category: 'security' },
    { pattern: /outerHTML\s*=/g,            label: 'outerHTML assignment',                     level: 'warn', category: 'security' },
    { pattern: /document\.write\s*\(/g,     label: 'document.write()',                         level: 'fail', category: 'security' },
    { pattern: / on\w+\s*=\s*["']/g,        label: 'Inline event handler attr',                level: 'warn', category: 'security' },
    { pattern: /javascript:/gi,             label: 'javascript: URI',                          level: 'fail', category: 'security' },
    { pattern: /localStorage\s*\./g,        label: 'localStorage usage',                       level: 'warn', category: 'security' },
    { pattern: /sessionStorage\s*\./g,      label: 'sessionStorage usage',                     level: 'warn', category: 'security' },
    { pattern: /document\.cookie\b/g,       label: 'document.cookie access',                   level: 'warn', category: 'security' },
    { pattern: /setTimeout\s*\(\s*["'`]/g,  label: 'setTimeout() with string arg (eval-like)', level: 'fail', category: 'security' },
    { pattern: /setInterval\s*\(\s*["'`]/g, label: 'setInterval() with string arg (eval-like)',level: 'fail', category: 'security' },
    { pattern: /(?:api[_-]?key|secret|password|bearer)\s*[:=]\s*["'][^"']{8,}/gi,
                                            label: 'Possible hardcoded credential',             level: 'fail', category: 'security' },
    // Quality
    { pattern: /window\[\s*["']\w+["']\]\s*=/g, label: 'Global window property mutation',     level: 'warn', category: 'quality' },
    { pattern: /var\s+\w+\s*=/g,           label: 'var declarations (use let/const)',           level: 'warn', category: 'quality' },
    { pattern: /console\.log\s*\(/g,        label: 'console.log() left in code',               level: 'warn', category: 'quality' },
    { pattern: /console\.debug\s*\(/g,      label: 'console.debug() left in code',             level: 'warn', category: 'quality' },
    { pattern: /\/\/\s*TODO\b/gi,           label: 'TODO comment found',                       level: 'warn', category: 'quality' },
    { pattern: /\/\/\s*FIXME\b/gi,          label: 'FIXME comment found',                      level: 'warn', category: 'quality' },
    { pattern: /\/\/\s*HACK\b/gi,           label: 'HACK comment found',                       level: 'warn', category: 'quality' },
    { pattern: /debugger\s*;/g,             label: 'debugger statement',                        level: 'fail', category: 'quality' },
    // Deprecated HTML
    { pattern: /<center[\s>]/gi,            label: 'Deprecated <center> element',              level: 'warn', category: 'html' },
    { pattern: /<font[\s>]/gi,              label: 'Deprecated <font> element',                level: 'warn', category: 'html' },
    { pattern: /<marquee[\s>]/gi,           label: 'Deprecated <marquee> element',             level: 'warn', category: 'html' },
    { pattern: /<blink[\s>]/gi,             label: 'Deprecated <blink> element',               level: 'warn', category: 'html' },
    // Config-file extra patterns
    ...((fileConfig.layer2 && fileConfig.layer2.extraPatterns) || []).map(p => ({
      ...p, pattern: new RegExp(p.pattern, p.flags || 'g'),
    })),
  ];

  // Full-document checks (missing structural elements)
  const docChecks = [
    { test: () => !/<!DOCTYPE\s+html/i.test(html),                      label: 'Missing <!DOCTYPE html>',          level: 'fail', category: 'html' },
    { test: () => !/<html[^>]+lang\s*=/i.test(html),                    label: 'Missing lang attribute on <html>', level: 'warn', category: 'html' },
    { test: () => !/<meta[^>]+charset/i.test(html),                     label: 'Missing <meta charset>',           level: 'warn', category: 'html' },
    { test: () => !/<title>[^<]+<\/title>/i.test(html),                 label: 'Missing or empty <title>',         level: 'warn', category: 'html' },
    { test: () => !/<meta[^>]+name\s*=\s*["']viewport["']/i.test(html), label: 'Missing <meta name="viewport">',  level: 'warn', category: 'html' },
  ];

  let securityClean = true;
  for (const { pattern, label, level, category } of checks) {
    const hits = findPatternWithLines(html, pattern);
    if (hits.length > 0) {
      securityClean = false;
      const msg = `[${category}] ${label} (${hits.length}x, first at line ${hits[0].line})`;
      if (level === 'fail') fail('static', msg);
      else warn('static', msg);
    }
  }

  for (const { test, label, level, category } of docChecks) {
    if (test()) {
      if (level === 'fail') fail('static', `[${category}] ${label}`);
      else warn('static', `[${category}] ${label}`);
    }
  }

  if (securityClean) pass('static', 'No flagged security patterns');

  // Missing alt attributes
  const imgNoAlt = (html.match(/<img(?![^>]*\balt\s*=)[^>]*>/gi) || []).length;
  if (imgNoAlt > 0) fail('static', `${imgNoAlt} <img> tag(s) missing alt attribute`);
  else pass('static', 'All <img> tags have alt attributes (or none present)');

  // Dialog divs without role
  const dialogNoRole = (html.match(/<div(?![^>]*role=)[^>]*dialog[^>]*>/gi) || []).length;
  if (dialogNoRole > 0) warn('static', 'Possible dialog div without role attribute');

  results.timings.layer2Ms = Date.now() - l2Start;

  // ─────────────────────────────────────────────
  // STEP 8: LAYER 3 — Playwright (enhanced)
  // ─────────────────────────────────────────────
  console.log('\n[ Layer 3 ] Playwright — Chromium headless execution');
  const l3Start = Date.now();

  // STEP 13: Graceful Playwright import
  let chromium = null;
  if (!flags.noBrowser) {
    try {
      ({ chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs'));
    } catch (e) {
      warn('playwright', `Playwright not available — skipping browser layers (${e.message})`);
    }
  } else {
    warn('playwright', 'Skipped — --no-browser flag set');
  }

  let axeResults = null;

  if (chromium) {
    await withTimeout('playwright+axe', flags.timeout, async () => {
      const browser = await chromium.launch({ headless: true });
      const context = await browser.newContext();
      const page = await context.newPage();

      const consoleErrors = [];
      const consoleWarnings = [];
      const pageErrors = [];
      const networkFailures = [];

      page.on('console', msg => {
        if (msg.type() === 'error')   consoleErrors.push(msg.text());
        if (msg.type() === 'warning') consoleWarnings.push(msg.text());
        if (flags.verbose) console.log(`    [console.${msg.type()}] ${msg.text()}`);
      });
      page.on('pageerror', err => pageErrors.push(err.message));
      page.on('requestfailed', req => networkFailures.push({
        url: req.url(), failure: req.failure()?.errorText ?? 'unknown', resourceType: req.resourceType(),
      }));

      const fileUrl = `file://${absPath}`;
      await page.goto(fileUrl, { waitUntil: 'domcontentloaded', timeout: 10000 }).catch(e => {
        fail('playwright', `Page load failed: ${e.message}`);
      });

      await page.waitForTimeout(500);

      // Uncaught exceptions
      if (pageErrors.length > 0) {
        for (const e of pageErrors) fail('playwright', `Uncaught exception: ${e}`);
      } else {
        pass('playwright', 'No uncaught JS exceptions');
      }

      // Console errors
      if (consoleErrors.length > 0) {
        for (const e of consoleErrors) warn('playwright', `console.error: ${e}`);
      } else {
        pass('playwright', 'No console errors');
      }

      // Console warnings count
      if (consoleWarnings.length > 0) {
        warn('playwright', `${consoleWarnings.length} console.warn() call(s) detected`);
        if (flags.verbose) for (const w of consoleWarnings) console.log(`    [console.warn] ${w}`);
      }
      results.consoleWarnCount = consoleWarnings.length;

      // Network failures
      for (const f of networkFailures) {
        warn('playwright', `Network failure [${f.resourceType}]: ${f.url} — ${f.failure}`);
      }
      if (networkFailures.length === 0) pass('playwright', 'No network failures');

      // Page title
      const pageTitle = await page.title();
      if (!pageTitle || !pageTitle.trim()) fail('playwright', 'Page has no <title> or title is empty');
      else pass('playwright', `Page title: "${pageTitle}"`);

      // Meta viewport
      const hasMetaViewport = await page.evaluate(() => !!document.querySelector('meta[name="viewport"]'));
      if (!hasMetaViewport) warn('playwright', 'Missing <meta name="viewport"> — page may not be mobile-responsive');
      else pass('playwright', 'Meta viewport tag present');

      // Performance metrics
      const perf = await page.evaluate(() => {
        const t = performance.timing;
        const paints = performance.getEntriesByType('paint');
        return {
          domContentLoaded: t.domContentLoadedEventEnd - t.navigationStart,
          loadComplete:     t.loadEventEnd - t.navigationStart,
          firstPaint:            paints.find(e => e.name === 'first-paint')?.startTime ?? null,
          firstContentfulPaint:  paints.find(e => e.name === 'first-contentful-paint')?.startTime ?? null,
        };
      });
      results.performance = perf;
      const perfThresh = fileConfig.performanceThresholds || { domContentLoaded: 3000, loadComplete: 5000 };
      if (perf.domContentLoaded > perfThresh.domContentLoaded)
        warn('playwright', `Slow DOMContentLoaded: ${perf.domContentLoaded}ms (threshold: ${perfThresh.domContentLoaded}ms)`);
      if (flags.verbose) {
        console.log(`    [perf] DOMContentLoaded: ${perf.domContentLoaded}ms`);
        console.log(`    [perf] Load: ${perf.loadComplete}ms`);
        if (perf.firstContentfulPaint) console.log(`    [perf] FCP: ${perf.firstContentfulPaint}ms`);
      }

      // DOM integrity checks
      const domChecks = await page.evaluate(() => {
        const issues = [];
        const ids = [...document.querySelectorAll('[id]')].map(el => el.id);
        const dupes = ids.filter((id, i) => ids.indexOf(id) !== i);
        if (dupes.length > 0) issues.push({ level: 'fail', msg: `Duplicate IDs: ${[...new Set(dupes)].join(', ')}` });

        const imgNoAlt = [...document.querySelectorAll('img:not([alt])')].length;
        if (imgNoAlt > 0) issues.push({ level: 'fail', msg: `${imgNoAlt} img(s) missing alt` });

        const unlabeledBtns = [...document.querySelectorAll('button')]
          .filter(b => !b.textContent.trim() && !b.getAttribute('aria-label') && !b.getAttribute('aria-labelledby'));
        if (unlabeledBtns.length > 0) issues.push({ level: 'warn', msg: `${unlabeledBtns.length} button(s) with no accessible name` });

        const unlabeledInputs = [...document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button])')]
          .filter(inp => {
            const id = inp.id;
            return !inp.getAttribute('aria-label') && !inp.getAttribute('aria-labelledby') &&
              (!id || !document.querySelector(`label[for="${id}"]`));
          });
        if (unlabeledInputs.length > 0) issues.push({ level: 'warn', msg: `${unlabeledInputs.length} input(s) without label` });

        return issues;
      });
      for (const { level, msg } of domChecks) {
        if (level === 'fail') fail('dom', msg); else warn('dom', msg);
      }
      if (domChecks.length === 0) pass('dom', 'DOM integrity checks passed');

      // Broken same-page anchor links
      const brokenAnchors = await page.evaluate(() => {
        return [...document.querySelectorAll('a[href]')]
          .map(a => a.getAttribute('href'))
          .filter(href => href && href.startsWith('#') && href.length > 1)
          .filter(href => !document.getElementById(href.slice(1)))
          .map(href => `Broken anchor: ${href} — no element with id="${href.slice(1)}"`);
      });
      for (const issue of brokenAnchors) fail('playwright', issue);
      if (brokenAnchors.length === 0) pass('playwright', 'All same-page anchor links resolve');

      // Keyboard focus indicator check
      const focusIssues = await page.evaluate(() => {
        const issues = [];
        const sel = 'a[href], button:not([disabled]), input:not([disabled]):not([type=hidden]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
        for (const el of document.querySelectorAll(sel)) {
          el.focus();
          const s = window.getComputedStyle(el, ':focus');
          if (s.outlineStyle === 'none' && (s.outlineWidth === '0px' || s.outlineWidth === '') && s.boxShadow === 'none') {
            issues.push(`No visible focus indicator: ${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}`);
          }
        }
        return issues;
      });
      if (focusIssues.length > 0) {
        for (const issue of focusIssues.slice(0, 5)) warn('playwright', `[keyboard] ${issue}`);
        if (focusIssues.length > 5) warn('playwright', `[keyboard] ...and ${focusIssues.length - 5} more focus indicator issues`);
      } else {
        pass('playwright', 'All focusable elements have visible focus indicators');
      }

      // Multi-viewport overflow checks
      const viewportResults = {};
      for (const vp of flags.viewports) {
        const [width, height] = vp.split('x').map(Number);
        await page.setViewportSize({ width, height });
        await page.waitForTimeout(150);
        const vpIssues = await page.evaluate(() => {
          const issues = [];
          if (document.body.scrollWidth > window.innerWidth + 2)
            issues.push(`Horizontal scroll (body ${document.body.scrollWidth}px > viewport ${window.innerWidth}px)`);
          return issues;
        });
        viewportResults[vp] = vpIssues;
        for (const issue of vpIssues) warn('playwright', `[viewport ${vp}] ${issue}`);
        if (vpIssues.length === 0 && flags.verbose) pass('playwright', `Viewport ${vp}: no overflow`);
      }
      results.viewportResults = viewportResults;

      // Screenshot on failure
      if (results.failed.length > 0) {
        try {
          const ssDir = resolve('./test-reports/screenshots');
          mkdirSync(ssDir, { recursive: true });
          const ssPath = `${ssDir}/${fileName.replace('.html', '')}-${Date.now()}.png`;
          await page.screenshot({ path: ssPath, fullPage: true });
          results.screenshotPath = ssPath;
          if (flags.verbose) console.log(`    [screenshot] Saved: ${ssPath}`);
        } catch (e) {
          if (flags.verbose) console.log(`    [screenshot] Failed: ${e.message}`);
        }
      }

      // ─────────────────────────────────────────────
      // STEP 9: LAYER 4 — axe-core (improved coverage)
      // ─────────────────────────────────────────────
      console.log('\n[ Layer 4 ] axe-core accessibility audit');
      const l4Start = Date.now();

      let axeSource = null;
      try {
        axeSource = readFileSync('./node_modules/axe-core/axe.min.js', 'utf8');
      } catch (e) {
        warn('axe-core', `Could not read axe-core: ${e.message} — run: npm install axe-core`);
      }

      if (axeSource) {
        await page.addScriptTag({ content: axeSource });
        const rawAxe = await page.evaluate(async () => {
          const r = await window.axe.run(document, {
            runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'] },
          });
          return {
            violations: r.violations.map(v => ({
              id: v.id, impact: v.impact, description: v.description, helpUrl: v.helpUrl,
              nodeCount: v.nodes.length,
              nodes: v.nodes.map(n => ({ html: n.html, target: n.target, failureSummary: n.failureSummary })),
            })),
            incomplete:   r.incomplete.length,
            passes:       r.passes.length,
            inapplicable: r.inapplicable.length,
          };
        });

        axeResults = {
          version: runMeta.axeVersion,
          tags: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'],
          violationsByImpact: groupAxeByImpact(rawAxe.violations),
          violations:   rawAxe.violations,
          incomplete:   rawAxe.incomplete,
          passes:       rawAxe.passes,
          inapplicable: rawAxe.inapplicable,
        };

        if (axeResults.violations.length === 0) {
          pass('axe-core', `${axeResults.passes} rules passed, 0 violations`);
        } else {
          pass('axe-core', `${axeResults.passes} rules passed`);
          for (const v of axeResults.violations) {
            const level = v.impact === 'critical' || v.impact === 'serious' ? 'fail' : 'warn';
            const msg = `[${v.impact}] ${v.id}: ${v.description} (${v.nodeCount} node(s))`;
            if (level === 'fail') fail('axe-core', msg); else warn('axe-core', msg);
            if (flags.verbose) {
              for (const node of v.nodes) {
                console.log(`    HTML: ${node.html}`);
                if (node.target) console.log(`    Path: ${node.target.join(' > ')}`);
              }
            }
          }
        }
        if (axeResults.incomplete > 0) warn('axe-core', `${axeResults.incomplete} rules need manual review`);
      }

      results.timings.layer4Ms = Date.now() - l4Start;
      results.axe = axeResults;

      await browser.close();
    }).catch(e => warn('playwright', `Browser layer error: ${e.message}`));
  }

  results.timings.layer3Ms = Date.now() - l3Start;

  // ─────────────────────────────────────────────
  // STEP 10: Score + Summary
  // ─────────────────────────────────────────────
  const { score, grade } = computeScore(results);
  results.score = score;
  results.grade = grade;
  results.durationMs = Date.now() - fileStart;

  console.log('\n=== SUMMARY ===');
  console.log(`  ✅ Passed:   ${results.passed.length}`);
  console.log(`  ⚠️  Warnings: ${results.warnings.length}`);
  console.log(`  ❌ Failed:   ${results.failed.length}`);
  console.log(`  Score:      ${score}/100  Grade: ${grade}`);

  if (results.failed.length > 0) {
    console.log('\nFailed:');
    for (const { layer, msg } of results.failed) console.log(`  ❌ [${layer}] ${msg}`);
  }

  if (flags.verbose) {
    console.log('\nTimings:');
    for (const [k, v] of Object.entries(results.timings)) console.log(`  ${k}: ${v}ms`);
  }

  // STEP 11: Diff vs previous run
  const diff = diffVsPreviousRun(results, outDir, fileName.replace('.html', ''));
  if (diff) {
    results.diff = diff;
    const arrow = d => d > 0 ? `+${d}` : `${d}`;
    console.log(`\nDiff vs ${diff.previousReport}:`);
    console.log(`  Failures: ${arrow(diff.failedDelta)}  Warnings: ${arrow(diff.warningsDelta)}  Score: ${arrow(diff.scoreDelta)}`);
    if (diff.newFailures.length > 0) {
      console.log('  New failures:');
      for (const f of diff.newFailures) console.log(`    [${f.layer}] ${f.msg}`);
    }
    if (diff.resolvedFailures.length > 0) {
      console.log('  Resolved:');
      for (const f of diff.resolvedFailures) console.log(`    [${f.layer}] ${f.msg}`);
    }
  }

  // STEP 12: Write report
  const reportPath = writeReport(results, runMeta, flags, fileName);
  console.log(`\nReport saved: ${reportPath}`);

  return results;
}

// ─────────────────────────────────────────────
// STEP 14: Watch mode (polling)
// ─────────────────────────────────────────────

async function startWatch(resolvedFiles, flags) {
  console.log(`\n[watch] Watching ${resolvedFiles.length} file(s)... (polling every 1500ms, Ctrl+C to stop)\n`);
  const mtimes = new Map();
  for (const f of resolvedFiles) {
    try { mtimes.set(f, statSync(f).mtimeMs); } catch {}
  }
  const poll = async () => {
    for (const f of resolvedFiles) {
      try {
        const mtime = statSync(f).mtimeMs;
        if (mtimes.get(f) !== mtime) {
          mtimes.set(f, mtime);
          console.log(`\n[watch] ${basename(f)} changed — re-running...\n`);
          await testFile(f, flags).catch(e => console.error(`[watch] Error: ${e.message}`));
        }
      } catch {}
    }
    setTimeout(poll, 1500);
  };
  setTimeout(poll, 1500);
}

// ─────────────────────────────────────────────
// STEP 7 + 15: Main entry point
// ─────────────────────────────────────────────

async function main() {
  const resolvedFiles = await resolveFiles(rawFiles);

  if (resolvedFiles.length === 0) {
    console.error('No files found matching the given pattern(s).');
    process.exit(1);
  }

  const allResults = [];
  for (const file of resolvedFiles) {
    allResults.push(await testFile(file, flags));
  }

  // Multi-file aggregate summary
  if (resolvedFiles.length > 1) {
    const totF = allResults.reduce((s, r) => s + r.failed.length, 0);
    const totW = allResults.reduce((s, r) => s + r.warnings.length, 0);
    const totP = allResults.reduce((s, r) => s + r.passed.length, 0);
    console.log(`\n${'='.repeat(50)}`);
    console.log(`AGGREGATE (${resolvedFiles.length} files)`);
    console.log(`${'='.repeat(50)}`);
    console.log(`  Passed: ${totP}  Warnings: ${totW}  Failed: ${totF}`);
    for (const r of allResults) {
      const icon = r.failed.length > 0 ? '❌' : r.warnings.length > 0 ? '⚠️ ' : '✅';
      console.log(`  ${icon} ${r.grade} ${r.score}/100  ${r.file}`);
    }
    mkdirSync(outDir, { recursive: true });
    const combinedPath = resolve(outDir, `combined-${Date.now()}.json`);
    writeFileSync(combinedPath, JSON.stringify({ files: allResults, meta: runMeta }, null, 2));
    console.log(`\nCombined report: ${combinedPath}`);
  }

  // STEP 14: Watch mode keeps process alive
  if (flags.watch) {
    await startWatch(resolvedFiles, flags);
    return;
  }

  // STEP 15: Exit code — fail on failures or (optionally) on warnings
  console.log(`\nTotal run time: ${Date.now() - RUN_START}ms`);
  const totalFailed   = allResults.reduce((s, r) => s + r.failed.length, 0);
  const totalWarnings = allResults.reduce((s, r) => s + r.warnings.length, 0);
  process.exit(totalFailed > 0 || (flags.failOnWarnings && totalWarnings > 0) ? 1 : 0);
}

main().catch(e => {
  console.error(`Fatal error: ${e.message}`);
  process.exit(1);
});
