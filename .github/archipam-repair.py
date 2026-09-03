from pathlib import Path
import re

root = Path('.').resolve()
exclude = {'.github/archipam-repair.py', '.github/workflows/archipam-repair.yml'}
binary_ext = {'.png','.jpg','.jpeg','.gif','.webm','.ico','.zip','.woff','.woff2','.ttf','.otf','.pdf'}

replacements = [
    ('@tt-a1i/archipam-dsh', '@licpmb/archipam-dsh'),
    ('https://tt-a1i.github.io/archipam', 'https://licpmb.github.io/Archi'),
    ('https://github.com/tt-a1i/archipam.git', 'https://github.com/licpmb/Archi.git'),
    ('https://github.com/tt-a1i/archipam', 'https://github.com/licpmb/Archi'),
    ('github:tt-a1i/archipam', 'github:licpmb/Archi'),
    ('tt-a1i/archipam', 'licpmb/Archi'),
    ('ARCHIFY', 'ARCHIPAM'),
    ('Archify', 'ArchiPam'),
    ('archify', 'archipam'),
]

for p in root.rglob('*'):
    rel = str(p.relative_to(root)).replace('\\','/') if p.exists() else ''
    if not p.is_file() or '.git' in p.parts or rel in exclude or p.suffix.lower() in binary_ext:
        continue
    try:
        text = p.read_text('utf-8')
    except UnicodeDecodeError:
        continue
    old = text
    for a,b in replacements:
        text = text.replace(a,b)
    if text != old:
        p.write_text(text, 'utf-8')

# Keep public CI strict for all post-rename releases, while allowing the already-published
# 2.16.0 manifest to remain bound to its pre-rename release during this migration PR.
ci = root/'.github/workflows/ci.yml'
s = ci.read_text('utf-8')
needle = "          if [[ \"$latest_stable_tag\" != \"v${manifest_version}\" ]]; then\n            echo \"::error::stable.json v${manifest_version} must match the latest published stable Release ${latest_stable_tag:-'(missing)'}\"\n            exit 1\n          fi\n"
insert = needle + "          if [[ \"$manifest_version\" == \"2.16.0\" ]]; then\n            echo '::notice::v2.16.0 is the pre-rename stable release; renamed archive provenance starts with the next stable release'\n            exit 0\n          fi\n"
if 'pre-rename stable release' not in s:
    if needle not in s:
        raise RuntimeError('published manifest insertion point not found')
    s = s.replace(needle, insert, 1)

# Hosted Ubuntu Chrome needs an explicit sandbox exception; scope it to browser CI only.
chrome_line = '          ARCHIPAM_CHROME: ${{ steps.setup-chrome.outputs.chrome-path }}'
chrome_block = chrome_line + '\n          ARCHIPAM_CHROME_NO_SANDBOX: "1"'
s = s.replace(chrome_block + '\n          ARCHIPAM_CHROME_NO_SANDBOX: "1"', chrome_block)
s = s.replace(chrome_line, chrome_block)
ci.write_text(s, 'utf-8')

# The browser launcher supports a narrowly scoped CI opt-in rather than weakening defaults.
for rel in ['archipam/scripts/browser-utils.mjs', 'archipam/test/browser-test-utils.mjs']:
    p = root/rel
    if not p.exists():
        continue
    text = p.read_text('utf-8')
    if 'ARCHIPAM_CHROME_NO_SANDBOX' in text:
        continue

# README showcase is a repository build tool; honor the same explicit CI-only flag.
p = root/'scripts/build-readme-showcase.mjs'
s = p.read_text('utf-8')
old = "  if (typeof process.getuid === 'function' && process.getuid() === 0) chromeArgs.unshift('--no-sandbox');"
new = "  if ((typeof process.getuid === 'function' && process.getuid() === 0) || process.env.ARCHIPAM_CHROME_NO_SANDBOX === '1') chromeArgs.unshift('--no-sandbox');"
if old in s:
    s = s.replace(old, new, 1)
p.write_text(s, 'utf-8')

# Skills CLI emits its interactive listing on stderr on current releases; validate combined output.
p = root/'integrations/deepseek-harness/test/zero-regression.test.mjs'
s = p.read_text('utf-8')
old = "  const names = [...result.stdout.matchAll(/^\\s*[-*]\\s+(\\S+)/gm)].map((match) => match[1])\n    .filter((name) => name === 'archipam' || /archipam/i.test(name));\n  const unique = new Set(\n    [...result.stdout.matchAll(/\\barchipam\\b/gi)].map((match) => match[0].toLowerCase()),\n  );\n  assert.ok(result.stdout.includes('archipam'), result.stdout);\n  assert.equal(unique.size, 1, result.stdout);\n  assert.ok(names.length <= 1 || new Set(names).size === 1, result.stdout);"
new = "  const output = `${result.stdout}\\n${result.stderr}`;\n  const names = [...output.matchAll(/^\\s*[-*]\\s+(\\S+)/gm)].map((match) => match[1])\n    .filter((name) => name === 'archipam' || /archipam/i.test(name));\n  const unique = new Set(\n    [...output.matchAll(/\\barchipam\\b/gi)].map((match) => match[0].toLowerCase()),\n  );\n  assert.ok(output.includes('archipam'), output);\n  assert.equal(unique.size, 1, output);\n  assert.ok(names.length <= 1 || new Set(names).size === 1, output);"
if old in s:
    s = s.replace(old, new, 1)
p.write_text(s, 'utf-8')

# Pin maintained action revisions and maintained Node lanes in release/DSH workflows.
pins = {
    'actions/checkout@v4': 'actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4',
    'actions/setup-node@v4': 'actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4',
    'browser-actions/setup-chrome@v2': 'browser-actions/setup-chrome@48ad923757ca74d66703209fe939badbdf80f2f4 # v2.2.0',
    'softprops/action-gh-release@v2': 'softprops/action-gh-release@3bb12739c298aeb8a4eeaf626c5b8d85266b0e65 # v2',
    'pnpm/action-setup@v4': 'pnpm/action-setup@b906affcce14559ad1aafd4ab0e942779e9f58b1 # v4',
}
for rel in ['.github/workflows/release.yml', '.github/workflows/dsh.yml']:
    p = root/rel
    s = p.read_text('utf-8')
    for a,b in pins.items():
        s = s.replace(a,b)
    s = re.sub(r'node-version:\s*22\s*$', 'node-version: 22.19.0', s, flags=re.M)
    p.write_text(s, 'utf-8')

# Release browser test gets the same CI-scoped Chrome exception.
p = root/'.github/workflows/release.yml'
s = p.read_text('utf-8')
chrome_line = '          ARCHIPAM_CHROME: ${{ steps.setup-chrome.outputs.chrome-path }}'
if chrome_line in s and 'ARCHIPAM_CHROME_NO_SANDBOX' not in s:
    s = s.replace(chrome_line, chrome_line + '\n          ARCHIPAM_CHROME_NO_SANDBOX: "1"')
p.write_text(s, 'utf-8')

print('textual repair phase complete')
