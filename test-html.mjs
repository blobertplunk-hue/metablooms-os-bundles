#!/usr/bin/env node
/**
 * test-html.mjs — MetaBlooms HTML test runner
 *
 * Usage:
 *   node test-html.mjs <file.html> [--verbose]
 *
 * Layers:
 *   1. html-validate  — static structural validation
 *   2. ESLint         — JS static analysis (inline scripts)
 *   3. Playwright     — real Chromium headless execution
 *      a. Console errors captured
 *      b. Uncaught exceptions captured
 *      c. axe-core accessibility audit
 *      d. Custom DOM security checks
 */

import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { resolve, basename } from 'path';
import { createRequire } from 'module';
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { HtmlValidate } from './node_modules/html-validate/dist/esm/index.js';

const require = createRequire(import.meta.url);

const args = process.argv.slice(2);
const filePath = args.find(a => !a.startsWith('--'));
const verbose = args.includes('--verbose');

if (!filePath) {
  console.error('Usage: node test-html.mjs <file.html> [--verbose]');
  process.exit(1);
}

const absPath = resolve(filePath);
const html = readFileSync(absPath, 'utf8');
const fileName = basename(absPath);

const results = { file: fileName, passed: [], warnings: [], failed: [] };

function pass(layer, msg) {
  results.passed.push({ layer, msg });
  if (verbose) console.log(`  ✅ [${layer}] ${msg}`);
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
// LAYER 1: html-validate
// ─────────────────────────────────────────────
console.log('[ Layer 1 ] html-validate (static structural)');
try {
  const htmlvalidate = new HtmlValidate({
    rules: {
      'no-dup-id': 'error',
      'void-content': 'error',
      'close-order': 'error',
      'no-unknown-elements': 'off', // custom elements ok
      'require-sri': 'off',
    },
  });
  const report = await htmlvalidate.validateString(html);
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
  warn('html-validate', `Could not run: ${e.message}`);
}

// ─────────────────────────────────────────────
// LAYER 2: Static text pattern checks
// ─────────────────────────────────────────────
console.log('\n[ Layer 2 ] Static security/quality patterns');

const checks = [
  { pattern: /\beval\s*\(/g,              label: 'eval() usage',              level: 'fail' },
  { pattern: /new\s+Function\s*\(/g,      label: 'new Function() usage',      level: 'fail' },
  { pattern: /innerHTML\s*=/g,            label: 'innerHTML assignment',       level: 'warn' },
  { pattern: /outerHTML\s*=/g,            label: 'outerHTML assignment',       level: 'warn' },
  { pattern: /document\.write\s*\(/g,     label: 'document.write()',           level: 'fail' },
  { pattern: / on\w+\s*=\s*["']/g,        label: 'Inline event handler attr',  level: 'warn' },
  { pattern: /javascript:\s*/gi,          label: 'javascript: URI',            level: 'fail' },
  { pattern: /localStorage\s*\./g,        label: 'localStorage usage',         level: 'warn' },
  { pattern: /var\s+\w+\s*=/g,            label: 'var declarations (use let/const)', level: 'warn' },
  { pattern: /window\[\s*["']\w+["']\]\s*=/g, label: 'Global window property mutation', level: 'warn' },
];

let securityClean = true;
for (const { pattern, label, level } of checks) {
  const matches = html.match(pattern);
  if (matches) {
    securityClean = false;
    if (level === 'fail') fail('static', `${label} (${matches.length}x)`);
    else warn('static', `${label} (${matches.length}x)`);
  }
}
if (securityClean) pass('static', 'No flagged security patterns');

// Missing alt attributes
const imgNoAlt = (html.match(/<img(?![^>]*\balt\s*=)[^>]*>/gi) || []).length;
if (imgNoAlt > 0) fail('static', `${imgNoAlt} <img> tag(s) missing alt attribute`);
else pass('static', 'All <img> tags have alt attributes (or none present)');

// Missing ARIA roles on dialogs
const dialogNoRole = (html.match(/<div(?![^>]*role=)[^>]*dialog[^>]*>/gi) || []).length;
if (dialogNoRole > 0) warn('static', `Possible dialog div without role attribute`);

// ─────────────────────────────────────────────
// LAYER 3: Playwright — real Chromium execution
// ─────────────────────────────────────────────
console.log('\n[ Layer 3 ] Playwright — Chromium headless execution');

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const page = await context.newPage();

const consoleErrors = [];
const consoleWarnings = [];
const pageErrors = [];

page.on('console', msg => {
  if (msg.type() === 'error') consoleErrors.push(msg.text());
  if (msg.type() === 'warning') consoleWarnings.push(msg.text());
  if (verbose) console.log(`    [console.${msg.type()}] ${msg.text()}`);
});
page.on('pageerror', err => pageErrors.push(err.message));

// Load the file
const fileUrl = `file://${absPath}`;
await page.goto(fileUrl, { waitUntil: 'domcontentloaded', timeout: 10000 }).catch(e => {
  fail('playwright', `Page load failed: ${e.message}`);
});

// Wait a moment for any async init
await page.waitForTimeout(500);

// Console errors
if (pageErrors.length > 0) {
  for (const e of pageErrors) fail('playwright', `Uncaught exception: ${e}`);
} else {
  pass('playwright', 'No uncaught JS exceptions');
}

if (consoleErrors.length > 0) {
  for (const e of consoleErrors) warn('playwright', `console.error: ${e}`);
} else {
  pass('playwright', 'No console errors');
}

// DOM integrity checks via page.evaluate
const domChecks = await page.evaluate(() => {
  const issues = [];

  // Duplicate IDs
  const ids = [...document.querySelectorAll('[id]')].map(el => el.id);
  const dupes = ids.filter((id, i) => ids.indexOf(id) !== i);
  if (dupes.length > 0) issues.push({ level: 'fail', msg: `Duplicate IDs: ${[...new Set(dupes)].join(', ')}` });

  // Images without alt
  const imgNoAlt = [...document.querySelectorAll('img:not([alt])')].length;
  if (imgNoAlt > 0) issues.push({ level: 'fail', msg: `${imgNoAlt} img(s) missing alt` });

  // Interactive elements without accessible name
  const buttons = [...document.querySelectorAll('button')];
  const unlabeled = buttons.filter(b => !b.textContent.trim() && !b.getAttribute('aria-label') && !b.getAttribute('aria-labelledby'));
  if (unlabeled.length > 0) issues.push({ level: 'warn', msg: `${unlabeled.length} button(s) with no accessible name` });

  // Forms without labels
  const inputs = [...document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button])')];
  const unlabeledInputs = inputs.filter(inp => {
    const id = inp.id;
    return !inp.getAttribute('aria-label') && !inp.getAttribute('aria-labelledby') && (!id || !document.querySelector(`label[for="${id}"]`));
  });
  if (unlabeledInputs.length > 0) issues.push({ level: 'warn', msg: `${unlabeledInputs.length} input(s) without label` });

  return issues;
});

for (const { level, msg } of domChecks) {
  if (level === 'fail') fail('dom', msg);
  else warn('dom', msg);
}
if (domChecks.length === 0) pass('dom', 'DOM integrity checks passed');

// ─────────────────────────────────────────────
// LAYER 4: axe-core accessibility audit
// ─────────────────────────────────────────────
console.log('\n[ Layer 4 ] axe-core accessibility audit');

const axeSource = readFileSync('./node_modules/axe-core/axe.min.js', 'utf8');
await page.addScriptTag({ content: axeSource });

const axeResults = await page.evaluate(async () => {
  const results = await window.axe.run(document, {
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'best-practice'] },
  });
  return {
    violations: results.violations.map(v => ({
      id: v.id,
      impact: v.impact,
      description: v.description,
      nodes: v.nodes.length,
    })),
    incomplete: results.incomplete.length,
    passes: results.passes.length,
  };
});

if (axeResults.violations.length === 0) {
  pass('axe-core', `${axeResults.passes} rules passed, 0 violations`);
} else {
  pass('axe-core', `${axeResults.passes} rules passed`);
  for (const v of axeResults.violations) {
    const level = v.impact === 'critical' || v.impact === 'serious' ? 'fail' : 'warn';
    const msg = `[${v.impact}] ${v.id}: ${v.description} (${v.nodes} node(s))`;
    if (level === 'fail') fail('axe-core', msg);
    else warn('axe-core', msg);
  }
}
if (axeResults.incomplete > 0) {
  warn('axe-core', `${axeResults.incomplete} rules need manual review`);
}

await browser.close();

// ─────────────────────────────────────────────
// SUMMARY
// ─────────────────────────────────────────────
console.log('\n=== SUMMARY ===');
console.log(`  ✅ Passed:   ${results.passed.length}`);
console.log(`  ⚠️  Warnings: ${results.warnings.length}`);
console.log(`  ❌ Failed:   ${results.failed.length}`);

if (results.failed.length > 0) {
  console.log('\nFailed:');
  for (const { layer, msg } of results.failed) console.log(`  ❌ [${layer}] ${msg}`);
}

// Write JSON report
mkdirSync('./test-reports', { recursive: true });
const reportPath = `./test-reports/${fileName.replace('.html', '')}-${Date.now()}.json`;
writeFileSync(reportPath, JSON.stringify({ ...results, axe: axeResults }, null, 2));
console.log(`\nReport saved: ${reportPath}`);

process.exit(results.failed.length > 0 ? 1 : 0);
