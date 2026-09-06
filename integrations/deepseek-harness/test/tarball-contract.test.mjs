import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const integrationRoot = path.resolve(here, '..');
const repoRoot = path.resolve(integrationRoot, '..', '..');
const packScript = path.join(integrationRoot, 'scripts', 'pack.mjs');
const DSH_RELEASE_REF = process.env.ARCHIPAM_DSH_SOURCE_REF || 'HEAD';

const FORBIDDEN = [
  '/test/',
  'package-lock.json',
  '/node_modules/',
  '.hive',
  '.workbuddy',
  'probe-skills',
  'generate-brand-marks.mjs',
  'generate-validators.mjs',
  'distribution-acceptance',
];

function packTarball() {
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'archipam-dsh-tarball-'));
  const out = path.join(scratch, 'licpmb-archipam-dsh-0.1.0.tgz');
  const result = spawnSync(process.execPath, [packScript, '--out', out, '--json'], {
    cwd: repoRoot,
    encoding: 'utf8',
  });
  return { scratch, out, result };
}

test('pack command emits a real npm tarball with the expected identity and file list', () => {
  const { scratch, out, result } = packTarball();
  try {
    assert.equal(result.status, 0, result.stderr || result.stdout);
    const receipt = JSON.parse(result.stdout);
    assert.equal(receipt.name, '@licpmb/archipam-dsh');
    assert.equal(receipt.version, '0.1.0');
    assert.equal(fs.existsSync(out), true);
    const files = receipt.files.map((file) => file.path.replace(/^package\//, ''));
    for (const required of [
      'package.json',
      'cordis.patch.yml',
      'lib/index.js',
      'README.md',
      'LICENSE',
      'skills/archipam/SKILL.md',
      'skills/archipam/bin/archipam.mjs',
    ]) {
      assert.ok(files.includes(required), `tarball missing ${required}`);
    }
    const skillEntries = files.filter((file) => file === 'skills/archipam/SKILL.md' || file.endsWith('/SKILL.md'));
    assert.deepEqual(skillEntries, ['skills/archipam/SKILL.md']);
    for (const notifierFile of [
      'skills/archipam/skill-release.json',
      'skills/archipam/scripts/check-update.mjs',
      'skills/archipam/scripts/update-contract.mjs',
    ]) {
      assert.equal(files.includes(notifierFile), false, `DSH 0.1.0 must not contain ${notifierFile}`);
    }
    for (const file of files) {
      for (const forbidden of FORBIDDEN) {
        assert.equal(file.includes(forbidden), false, `tarball contains forbidden ${file}`);
      }
    }
    assert.equal(files.some((file) => file.startsWith('test/')), false);
  } finally {
    fs.rmSync(scratch, { recursive: true, force: true });
  }
});

test('packed Skill payload remains byte-identical to the selected immutable source ref', () => {
  const { scratch, out, result } = packTarball();
  try {
    assert.equal(result.status, 0, result.stderr || result.stdout);
    const receipt = JSON.parse(result.stdout);
    const packedRoot = path.join(scratch, 'packed');
    fs.mkdirSync(packedRoot);
    const tar = spawnSync('tar', ['-xzf', path.basename(out), '-C', packedRoot], {
      cwd: path.dirname(out),
      encoding: 'utf8',
    });
    assert.equal(tar.status, 0, tar.stderr);
    const skillRoot = path.join(packedRoot, 'package', 'skills', 'archipam');
    const skillFiles = receipt.files
      .map((file) => file.path.replace(/^package\//, ''))
      .filter((file) => file.startsWith('skills/archipam/'))
      .filter((file) => !['skills/archipam/package.json', 'skills/archipam/SKILL.md'].includes(file));
    for (const packagedPath of skillFiles) {
      const relative = packagedPath.slice('skills/archipam/'.length);
      const tagged = spawnSync('git', [
        'show',
        `${DSH_RELEASE_REF}:archipam/${relative}`,
      ], {
        cwd: repoRoot,
        encoding: null,
      });
      assert.equal(tagged.status, 0, tagged.stderr?.toString('utf8'));
      assert.deepEqual(
        fs.readFileSync(path.join(skillRoot, ...relative.split('/'))),
        tagged.stdout,
        `${packagedPath} differs from ${DSH_RELEASE_REF}`,
      );
    }
    const skillPackage = JSON.parse(fs.readFileSync(path.join(skillRoot, 'package.json'), 'utf8'));
    const sourcePackage = JSON.parse(fs.readFileSync(path.join(repoRoot, 'archipam', 'package.json'), 'utf8'));
    assert.equal(skillPackage.version, sourcePackage.version);
    assert.doesNotMatch(fs.readFileSync(path.join(skillRoot, 'SKILL.md'), 'utf8'), /## Update awareness/);
  } finally {
    fs.rmSync(scratch, { recursive: true, force: true });
  }
});
