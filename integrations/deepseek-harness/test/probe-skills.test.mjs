import assert from 'node:assert/strict';
import test from 'node:test';
import { waitForArchiPam } from './probe-skills.mjs';

test('skill probe waits for a provider that registers during DSH boot', async () => {
  let calls = 0;
  const archipam = { name: 'archipam', provider: 'archipam-plugin' };
  const skills = {
    async list() {
      calls += 1;
      return calls < 3 ? [] : [archipam];
    },
  };
  const result = await waitForArchiPam(skills, '/workspace', {
    timeoutMs: 1_000,
    sleep: async () => {},
  });
  assert.equal(calls, 3);
  assert.equal(result.archipam, archipam);
  assert.deepEqual(result.list, [archipam]);
});
