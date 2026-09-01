from pathlib import Path
import json, re, sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
temp_workflows = {'archipam-one-time-refactor.yml','archipam-refactor-v2.yml','archipam-refactor-v3.yml'}
binary_ext = {'.png','.jpg','.jpeg','.gif','.webm','.ico','.zip','.woff','.woff2','.ttf','.otf','.pdf'}
special = [
    ('@licpmb/archipam-dsh','@licpmb/archipam-dsh'),
    ('https://github.com/licpmb/Archi.git','https://github.com/licpmb/Archi.git'),
    ('https://github.com/licpmb/Archi','https://github.com/licpmb/Archi'),
    ('https://licpmb.github.io/Archi','https://licpmb.github.io/Archi'),
    ('licpmb/Archi','licpmb/Archi'),
]
replacements = [('ARCHIPAM','ARCHIPAM'),('ArchiPam','ArchiPam'),('archipam','archipam')]

def is_text_candidate(p: Path):
    return p.is_file() and '.git' not in p.parts and p.suffix.lower() not in binary_ext and p.name not in temp_workflows

for p in list(root.rglob('*')):
    if not is_text_candidate(p):
        continue
    try:
        s = p.read_text('utf-8')
    except UnicodeDecodeError:
        continue
    old = s
    for a,b in special:
        s = s.replace(a,b)
    for a,b in replacements:
        s = s.replace(a,b)
    if s != old:
        p.write_text(s,'utf-8')

items = [p for p in root.rglob('*') if '.git' not in p.parts and 'archipam' in p.name.lower()]
for p in sorted(items, key=lambda x: len(x.parts), reverse=True):
    if not p.exists():
        continue
    newname = p.name.replace('ARCHIPAM','ARCHIPAM').replace('ArchiPam','ArchiPam').replace('archipam','archipam')
    if newname != p.name:
        p.rename(p.with_name(newname))

p = root/'archipam/package.json'
d = json.loads(p.read_text())
d['engines']['node'] = '^22.19.0 || >=24.0.0 <25'
d['overrides']['fast-uri'] = '3.1.6'
p.write_text(json.dumps(d,indent=2)+'\n')
p = root/'integrations/deepseek-harness/package.json'
d = json.loads(p.read_text())
d['engines']['node'] = '^22.19.0 || >=24.0.0 <25'
p.write_text(json.dumps(d,indent=2)+'\n')

pins = {
    'actions/checkout@v4':'actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4',
    'actions/setup-node@v4':'actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4',
    'browser-actions/setup-chrome@v2':'browser-actions/setup-chrome@48ad923757ca74d66703209fe939badbdf80f2f4 # v2.2.0',
    'actions/configure-pages@v5':'actions/configure-pages@983d7736d9b0ae728b81ab479565c72886d7745b # v5',
    'actions/upload-pages-artifact@v4':'actions/upload-pages-artifact@7b1f4a764d45c48632c6b24a0339c27f5614fb0b # v4',
    'actions/deploy-pages@v4':'actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e # v4',
    'softprops/action-gh-release@v2':'softprops/action-gh-release@3bb12739c298aeb8a4eeaf626c5b8d85266b0e65 # v2',
    'pnpm/action-setup@v4':'pnpm/action-setup@b906affcce14559ad1aafd4ab0e942779e9f58b1 # v4',
}
for p in (root/'.github/workflows').glob('*.yml'):
    if p.name in temp_workflows:
        continue
    s=p.read_text()
    for a,b in pins.items():
        s=s.replace(a,b)
    s=s.replace('node-version: [18, 20, 22, 24]','node-version: [22.19.0, 24]')
    s=re.sub(r'node-version:\s*22\s*$', 'node-version: 24', s, flags=re.M)
    if p.name=='ci.yml':
        s,n=re.subn(r'(  zip-freshness:\n.*?node-version:) 24', r'\1 22.19.0', s, count=1, flags=re.S)
        if n!=1:
            raise RuntimeError('zip-freshness node lane patch failed')
    if p.name=='release.yml':
        s,n=re.subn(r'node-version: 24','node-version: 22.19.0',s,count=1)
        if n!=1:
            raise RuntimeError('release node lane patch failed')
    out=[]
    for line in s.splitlines():
        if 'ARCHIPAM_CHROME_NO_SANDBOX:' in line:
            if out and out[-1].strip()=='env:':
                out.pop()
            continue
        out.append(line)
    s='\n'.join(out)+'\n'
    if p.name in {'ci.yml','dsh.yml'} and '\npermissions:' not in s.split('\njobs:',1)[0]:
        s=s.replace('\njobs:\n','\npermissions:\n  contents: read\n\njobs:\n',1)
    p.write_text(s)

p=root/'.github/workflows/ci.yml'
s=p.read_text()
needle='      - name: Golden-file + schema tests\n        run: npm test\n        working-directory: archipam\n'
if 'Dependency vulnerability gate' not in s:
    if needle not in s:
        raise RuntimeError('CI insertion point missing')
    s=s.replace(needle,'      - name: Dependency vulnerability gate\n        run: npm audit --audit-level=high\n        working-directory: archipam\n'+needle,1)
p.write_text(s)

for p in root.rglob('*'):
    if not is_text_candidate(p):
        continue
    try:
        s=p.read_text('utf-8')
    except UnicodeDecodeError:
        continue
    old=s
    s=re.sub(r'\s*<noscript>\s*<link href="https://fonts\.googleapis\.com[^>]*>\s*</noscript>\s*','\n',s,flags=re.S)
    s=re.sub(r'\s*<link rel="preconnect" href="https://fonts\.gstatic\.com" crossorigin>\s*','\n',s)
    s=re.sub(r'\s*<link rel="preconnect" href="https://fonts\.googleapis\.com">\s*','\n',s)
    s=re.sub(r'\s*<link href="https://fonts\.googleapis\.com[^>]*>\s*','\n',s,flags=re.S)
    s=s.replace('about:blank#remote-font-removed','about:blank#remote-font-removed').replace('about:blank#remote-font-removed','about:blank#remote-font-removed')
    s=s.replace('  <!-- Async font load: a blackholed network must not block first paint.\n       The body font stack falls back to system monospace until it lands. -->\n','  <!-- Offline-safe font policy: use the local/system monospace stack only. -->\n')
    if s!=old:
        p.write_text(s,'utf-8')

p=root/'archipam/bin/archipam.mjs'
s=p.read_text()
old = "function commandRender(args) {\n  const qualityArgs = extractQualityArgs(args);\n  const repoArgs = extractRepoRootArgs(qualityArgs.rest);\n  const [type, input, output] = repoArgs.rest;\n  if (!type || !input) fail(usage());\n  assertEvidenceType(type, repoArgs.repoRoot);\n  const result = runNode([rendererPath(type), input, ...(output ? [output] : [])], {\n    env: rendererEnv(qualityArgs.quality, repoArgs.repoRoot),\n  });\n  if (result.status !== 0) exitFrom(result);\n}"
new = "function commandRender(args) {\n  const qualityArgs = extractQualityArgs(args);\n  const repoArgs = extractRepoRootArgs(qualityArgs.rest);\n  const [type, input, output] = repoArgs.rest;\n  if (!type || !input) fail(usage());\n  assertEvidenceType(type, repoArgs.repoRoot);\n  const result = runNode([rendererPath(type), input, ...(output ? [output] : [])], {\n    stdio: 'pipe',\n    env: rendererEnv(qualityArgs.quality, repoArgs.repoRoot, true),\n  });\n  if (result.status !== 0) {\n    const failure = rendererFailure(result);\n    reportArtifactFailure({\n      command: 'render',\n      json: false,\n      stage: failure.diagnostics.some((entry) => entry.code.startsWith('input/')) ? 'input' : 'render',\n      type,\n      input: path.resolve(input),\n      ...(output ? { output: path.resolve(output) } : {}),\n      error: failure.error,\n      diagnostics: failure.diagnostics,\n      status: result.status ?? 1,\n    });\n    return;\n  }\n  if (result.stdout) process.stdout.write(result.stdout);\n}"
if old not in s:
    raise RuntimeError('commandRender old block not found')
s=s.replace(old,new,1)
old="  const nodeMajor = Number.parseInt(process.versions.node.split('.')[0], 10);\n  checks.push({\n    label: `Node.js v${process.versions.node} (requires >=18)`,\n    ok: nodeMajor >= 18,"
new="  const [nodeMajor, nodeMinor] = process.versions.node.split('.').map(Number);\n  const nodeSupported = (nodeMajor === 22 && nodeMinor >= 19) || nodeMajor === 24;\n  checks.push({\n    label: `Node.js v${process.versions.node} (requires Node 22.19+ or 24.x)`,\n    ok: nodeSupported,"
if old not in s:
    raise RuntimeError('doctor old block not found')
s=s.replace(old,new,1).replace('Node.js 18 or newer is required','Node.js 22.19+ or Node.js 24.x is required')
p.write_text(s)

p=root/'archipam/test/release-package-gates.test.mjs'
s=p.read_text()
s=s.replace("assert.equal(packageJson.engines?.node, '>=18');", "assert.equal(packageJson.engines?.node, '^22.19.0 || >=24.0.0 <25');")
s=s.replace('.map((version) => Number(version.trim()));','.map((version) => version.trim());')
old="  for (const version of [18, 20, 22, 24]) {\n    assert.ok(versions.includes(version), `test matrix must cover Node ${version}`);\n  }"
new="  for (const version of ['22.19.0', '24']) {\n    assert.ok(versions.includes(version), `test matrix must cover maintained Node ${version}`);\n  }\n  for (const eolVersion of ['18', '20']) {\n    assert.equal(versions.includes(eolVersion), false, `test matrix must not advertise EOL Node ${eolVersion}`);\n  }"
if old not in s:
    raise RuntimeError('matrix old block not found')
s=s.replace(old,new,1)
s=s.replace('assert.match(packageSmokeJob, /node-version:\\s*22/);','assert.match(packageSmokeJob, /node-version:\\s*24/);')
for a,b in {
    'actions\\/configure-pages@v5':'actions\\/configure-pages@983d7736d9b0ae728b81ab479565c72886d7745b',
    'actions\\/upload-pages-artifact@v4':'actions\\/upload-pages-artifact@7b1f4a764d45c48632c6b24a0339c27f5614fb0b',
    'actions\\/deploy-pages@v4':'actions\\/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e',
}.items():
    s=s.replace(a,b)
p.write_text(s)

legacy_paths=[str(p.relative_to(root)) for p in root.rglob('*') if '.git' not in p.parts and p.name not in temp_workflows and 'archipam' in p.name.lower()]
legacy_text=[]
for p in root.rglob('*'):
    if not is_text_candidate(p):
        continue
    try:
        text=p.read_text('utf-8')
    except UnicodeDecodeError:
        continue
    if 'archipam' in text.lower():
        legacy_text.append(str(p.relative_to(root)))
if legacy_paths or legacy_text:
    raise RuntimeError(f'legacy paths={legacy_paths[:20]} text={legacy_text[:20]}')
print('refactor text/path phase OK')
