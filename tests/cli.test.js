import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const CLI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../bin/oube-release.js');

function cli(cwd, ...args) {
  return spawnSync('node', [CLI, ...args], { cwd, encoding: 'utf8' });
}

function makeApp() {
  const dir = mkdtempSync(path.join(tmpdir(), 'oube-release-'));
  writeFileSync(
    path.join(dir, 'app.json'),
    JSON.stringify({
      expo: {
        version: '1.0.0',
        scheme: 'demo',
        ios: { bundleIdentifier: 'com.example.demo' },
        android: { package: 'com.example.demo' },
      },
    })
  );
  return dir;
}

test('help prints the command list', () => {
  const result = cli(process.cwd(), '--help');
  assert.equal(result.status, 0);
  assert.match(result.stdout, /screenshots run/);
  assert.match(result.stdout, /metadata lint/);
});

test('commands that need a config fail clearly outside an app', () => {
  const result = cli(mkdtempSync(path.join(tmpdir(), 'oube-empty-')), 'metadata', 'lint');
  assert.equal(result.status, 1);
  assert.match(result.stderr, /oube-release init/);
});

test('init writes a config prefilled from app.json, then scaffolds fastlane and metadata', () => {
  const app = makeApp();
  const first = cli(app, 'init');
  assert.equal(first.status, 0, first.stderr);
  const config = JSON.parse(readFileSync(path.join(app, 'oube.config.json'), 'utf8'));
  assert.equal(config.scheme, 'demo');
  assert.equal(config.ios.bundleId, 'com.example.demo');
  assert.equal(config.android.package, 'com.example.demo');

  const second = cli(app, 'init');
  assert.equal(second.status, 0, second.stderr);
  assert.ok(existsSync(path.join(app, 'fastlane', 'Fastfile')));
  assert.ok(existsSync(path.join(app, 'fastlane', 'Deliverfile')));
  assert.ok(existsSync(path.join(app, 'fastlane', 'metadata', 'ko', 'release_notes.txt')));
  assert.ok(
    existsSync(
      path.join(app, 'fastlane', 'metadata', 'android', 'en-US', 'changelogs', 'default.txt')
    )
  );
  assert.match(second.stdout, /\.gitignore/);
  assert.match(readFileSync(path.join(app, '.gitignore'), 'utf8'), /store-assets\/fonts\//);

  // 두 번째 init 은 있는 파일을 덮어쓰지 않는다
  writeFileSync(path.join(app, 'fastlane', 'metadata', 'ko', 'name.txt'), '허들');
  cli(app, 'init');
  assert.equal(
    readFileSync(path.join(app, 'fastlane', 'metadata', 'ko', 'name.txt'), 'utf8'),
    '허들'
  );
});

test('metadata lint runs against the scaffolded tree and reports limits', () => {
  const app = makeApp();
  cli(app, 'init');
  cli(app, 'init');
  const clean = cli(app, 'metadata', 'lint');
  assert.equal(clean.status, 0, clean.stderr);
  assert.match(clean.stdout, /한도 초과 0건/);

  writeFileSync(path.join(app, 'fastlane', 'metadata', 'ko', 'name.txt'), 'x'.repeat(31));
  const over = cli(app, 'metadata', 'lint');
  assert.equal(over.status, 1);
  assert.match(over.stdout, /ko App Store name.txt: 31\/30/);
  assert.match(over.stdout, /이름이 App Store 와 Play 에서 다릅니다/);
});

test('screenshots rejects unknown devices and locales before running anything', () => {
  const app = makeApp();
  cli(app, 'init');
  const device = cli(app, 'screenshots', 'capture', '--device', 'watch');
  assert.equal(device.status, 1);
  assert.match(device.stderr, /설정에 없는 기기/);
  const locale = cli(app, 'screenshots', 'compose', '--locale', 'fr');
  assert.equal(locale.status, 1);
  assert.match(locale.stderr, /설정에 없는 언어/);
});
