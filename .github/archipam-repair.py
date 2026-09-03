from pathlib import Path

# Repair revision 3: rerun after Chrome 152 CDP compatibility fix.
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
    rel = str(p.relative_to(root)).replace('\\', '/')
    if (
        not p.is_file()
        or '.git' in p.parts
        or rel in exclude
        or rel.startswith('.github/workflows/')
        or p.suffix.lower() in binary_ext
    ):
        continue
    try:
        text = p.read_text('utf-8')
    except UnicodeDecodeError:
        continue
    old = text
    for source, target in replacements:
        text = text.replace(source, target)
    if text != old:
        p.write_text(text, 'utf-8')

p = root/'scripts/build-readme-showcase.mjs'
s = p.read_text('utf-8')
s = s.replace(
    "  if (typeof process.getuid === 'function' && process.getuid() === 0) chromeArgs.unshift('--no-sandbox');",
    "  if ((typeof process.getuid === 'function' && process.getuid() === 0) || process.env.ARCHIPAM_CHROME_NO_SANDBOX === '1') chromeArgs.unshift('--no-sandbox');",
)
old = "      const exited = new Promise(resolve => chrome.once('exit', resolve));\n      chrome.kill('SIGTERM');\n      await Promise.race([exited, sleep(2000)]);\n      if (chrome.exitCode === null) chrome.kill('SIGKILL');"
new = "      let exited = new Promise(resolve => chrome.once('exit', resolve));\n      chrome.kill('SIGTERM');\n      await Promise.race([exited, sleep(2000)]);\n      if (chrome.exitCode === null) {\n        exited = new Promise(resolve => chrome.once('exit', resolve));\n        chrome.kill('SIGKILL');\n        await Promise.race([exited, sleep(5000)]);\n      }"
if old in s:
    s = s.replace(old, new, 1)
s = s.replace(
    "    fs.rmSync(tempRoot, { recursive: true, force: true });",
    "    fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 8, retryDelay: 125 });",
)
p.write_text(s, 'utf-8')

p = root/'integrations/deepseek-harness/test/zero-regression.test.mjs'
s = p.read_text('utf-8')
old = "  const names = [...result.stdout.matchAll(/^\\s*[-*]\\s+(\\S+)/gm)].map((match) => match[1])\n    .filter((name) => name === 'archipam' || /archipam/i.test(name));\n  const unique = new Set(\n    [...result.stdout.matchAll(/\\barchipam\\b/gi)].map((match) => match[0].toLowerCase()),\n  );\n  assert.ok(result.stdout.includes('archipam'), result.stdout);\n  assert.equal(unique.size, 1, result.stdout);\n  assert.ok(names.length <= 1 || new Set(names).size === 1, result.stdout);"
new = "  const output = `${result.stdout}\\n${result.stderr}`;\n  const names = [...output.matchAll(/^\\s*[-*]\\s+(\\S+)/gm)].map((match) => match[1])\n    .filter((name) => name === 'archipam' || /archipam/i.test(name));\n  const unique = new Set(\n    [...output.matchAll(/\\barchipam\\b/gi)].map((match) => match[0].toLowerCase()),\n  );\n  assert.ok(output.includes('archipam'), output);\n  assert.equal(unique.size, 1, output);\n  assert.ok(names.length <= 1 || new Set(names).size === 1, output);"
if old in s:
    s = s.replace(old, new, 1)
p.write_text(s, 'utf-8')

print('non-workflow repair phase complete')
