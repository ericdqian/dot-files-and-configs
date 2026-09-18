const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { test } = require('node:test');

test('registers and refreshes a private mapping, including an unavailable inbox', t => {
  const registry = fs.mkdtempSync(path.join(os.tmpdir(), 'claude-registry-test-'));
  t.after(() => fs.rmSync(registry, { recursive: true }));
  const sessionId = '12345678-1234-1234-1234-123456789abc';
  const run = (id, socket) => spawnSync('bash', [path.join(__dirname, 'register_claude_session.sh')], {
    input: JSON.stringify({ session_id: id }), encoding: 'utf8',
    env: { ...process.env, CLAUDE_SESSION_REGISTRY_DIR: registry, CLAUDE_CODE_MESSAGING_SOCKET: socket,
      CLAUDE_CODE_MESSAGING_TOKEN: 'must-not-be-stored' },
  });
  for (const socket of ['/tmp/first.sock', '/tmp/resumed.sock', '']) {
    assert.equal(run(sessionId, socket).status, 0);
    const filename = path.join(registry, `${sessionId}.json`);
    assert.deepEqual(JSON.parse(fs.readFileSync(filename, 'utf8')), { sessionId, messagingSocket: socket });
    assert.equal(fs.statSync(filename).mode & 0o777, 0o600);
  }
  assert.notEqual(run('../escape', '/tmp/socket').status, 0);
  assert.deepEqual(fs.readdirSync(registry), [`${sessionId}.json`]);
});
