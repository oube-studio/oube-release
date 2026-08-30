#!/usr/bin/env node
// @oube/release CLI. 앱 폴더(oube.config.json 이 있는 곳)를 찾아 도구 스크립트에 환경 변수로 넘긴다.
// 스크립트는 패키지 안에 있고 앱 파일은 앱 폴더 기준이라, 두 위치를 여기서 한 번만 계산한다.
import { spawnSync } from 'node:child_process';
import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const PACKAGE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TOOLS = path.join(PACKAGE_DIR, 'tools');
const TEMPLATES = path.join(PACKAGE_DIR, 'templates');

const HELP = `oube-release <command>

  init                              oube.config.json, fastlane/, 스토어 문구 폴더, 스크린샷 라우트를 생성합니다 (이미 있는 파일은 유지)
  screenshots build [--device d]    시뮬레이터용 Release 앱을 빌드하고 설치합니다
  screenshots capture [--device d] [--locale l|all]
  screenshots compose [--device d] [--locale l|all]
  screenshots run [--device d] [--locale l|all] [--skip-build]   build + capture + compose
  screenshots all                   모든 기기와 언어의 스크린샷을 생성합니다
  fonts                             설정에 지정된 폰트 중 없는 파일을 내려받습니다 (compose 전에 자동 실행)
  metadata lint                     스토어 문구와 인앱 상품 원고의 글자수 한도를 검사합니다
  metadata verify                   스토어에 게시된 문구와 fastlane/metadata 를 비교합니다
  doctor                            필요한 도구가 설치되어 있는지 확인합니다

--device 를 생략하면 설정의 첫 번째 기기, --locale 을 생략하면 모든 언어를 대상으로 합니다.
빌드 업로드와 심사 제출은 앱 폴더에서 fastlane beta, fastlane release 로 실행합니다.`;

const APP_STORE_FILES = [
  'name.txt',
  'subtitle.txt',
  'promotional_text.txt',
  'description.txt',
  'keywords.txt',
  'release_notes.txt',
  'marketing_url.txt',
  'privacy_url.txt',
  'support_url.txt',
];
const PLAY_FILES = [
  'title.txt',
  'short_description.txt',
  'full_description.txt',
  'changelogs/default.txt',
];
const GITIGNORE_LINES = [
  'fastlane/*.json.key',
  'fastlane/*.p8',
  'fastlane/report.xml',
  'fastlane/Preview.html',
  'fastlane/metadata/android/*/images/',
  'build/',
  '.screenshots-derived-data/',
];

function fail(message) {
  console.error(message);
  process.exit(1);
}

function findAppRoot(start) {
  let dir = start;
  for (;;) {
    if (existsSync(path.join(dir, 'oube.config.json'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function readJson(file) {
  try {
    return JSON.parse(readFileSync(file, 'utf8'));
  } catch (error) {
    return fail(`${file} 을 읽을 수 없습니다: ${error.message}`);
  }
}

function loadConfig(root) {
  const config = readJson(path.join(root, 'oube.config.json'));
  for (const key of ['scheme', 'ios', 'android', 'locales']) {
    if (!(key in config)) fail(`oube.config.json 에 ${key} 가 없습니다`);
  }
  return config;
}

function run(command, args, root) {
  const result = spawnSync(command, args, {
    stdio: 'inherit',
    cwd: root,
    env: {
      ...process.env,
      OUBE_APP_ROOT: root,
      OUBE_CONFIG: path.join(root, 'oube.config.json'),
      OUBE_TOOLS: TOOLS,
    },
  });
  if (result.error) fail(`${command} 실행 실패: ${result.error.message}`);
  if (result.status !== 0) process.exit(result.status ?? 1);
}

function parseArgs(argv) {
  const flags = {};
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (!arg.startsWith('--')) {
      positional.push(arg);
      continue;
    }
    const next = argv[i + 1];
    if (next !== undefined && !next.startsWith('--')) {
      flags[arg.slice(2)] = next;
      i++;
    } else {
      flags[arg.slice(2)] = true;
    }
  }
  return { flags, positional };
}

const SCREENSHOT_COMMANDS = ['build', 'capture', 'compose', 'run', 'all'];

function screenshots(sub, flags, root, config) {
  if (!SCREENSHOT_COMMANDS.includes(sub))
    fail(`알 수 없는 screenshots 명령어입니다: ${sub ?? ''}\n\n${HELP}`);
  const devices = Object.keys(config.screenshots?.devices ?? {});
  if (devices.length === 0) fail('oube.config.json 에 screenshots.devices 가 없습니다');
  const locales = Object.keys(config.locales);
  const device = flags.device ?? devices[0];
  if (!devices.includes(device)) fail(`설정에 없는 기기입니다: ${device}`);
  const wanted = !flags.locale || flags.locale === 'all' ? locales : [flags.locale];
  for (const locale of wanted) {
    if (!locales.includes(locale)) fail(`설정에 없는 언어입니다: ${locale}`);
  }

  const build = (d) => run('bash', [path.join(TOOLS, 'screenshots', 'build-ios.sh'), d], root);
  const capture = (d, l) =>
    run('bash', [path.join(TOOLS, 'screenshots', 'capture-ios.sh'), d, l], root);
  const compose = (d, l) =>
    run(
      'python3',
      [path.join(TOOLS, 'screenshots', 'batch.py'), '--device', d, '--locale', l],
      root
    );
  if (sub !== 'build' && sub !== 'capture') fonts(root); // 합성은 폰트가 있어야 한다

  switch (sub) {
    case 'build':
      build(device);
      break;
    case 'capture':
      for (const locale of wanted) capture(device, locale);
      break;
    case 'compose':
      for (const locale of wanted) compose(device, locale);
      break;
    case 'run':
      if (!flags['skip-build']) build(device);
      for (const locale of wanted) {
        capture(device, locale);
        compose(device, locale);
      }
      break;
    case 'all':
      for (const d of devices) {
        build(d);
        for (const locale of locales) {
          capture(d, locale);
          compose(d, locale);
        }
      }
      break;
  }
}

function fonts(root) {
  run('python3', [path.join(TOOLS, 'fonts', 'fetch.py')], root);
}

function metadata(sub, root) {
  if (sub !== 'lint' && sub !== 'verify')
    fail(`알 수 없는 metadata 명령어입니다: ${sub ?? ''}\n\n${HELP}`);
  run('python3', [path.join(TOOLS, 'metadata', `${sub}.py`)], root);
}

// 없는 줄만 .gitignore 끝에 추가한다. 키 파일과 빌드 결과물이 실수로 커밋되는 일을 init 단계에서 막는다
function appendGitignore(root) {
  const file = path.join(root, '.gitignore');
  const current = existsSync(file) ? readFileSync(file, 'utf8') : '';
  const present = new Set(current.split('\n').map((line) => line.trim()));
  const missing = GITIGNORE_LINES.filter((line) => !present.has(line));
  if (missing.length === 0) return;
  const prefix = current.length === 0 || current.endsWith('\n') ? '' : '\n';
  appendFileSync(file, `${prefix}\n# oube-release: 인증 키와 빌드 결과물\n${missing.join('\n')}\n`);
  console.log(`+ .gitignore (${missing.length}줄 추가)`);
}

// 없는 파일만 만든다. 이미 있는 파일은 앱에서 채운 것이라 건드리지 않는다
function writeIfMissing(file, content) {
  if (existsSync(file)) return false;
  mkdirSync(path.dirname(file), { recursive: true });
  writeFileSync(file, content);
  console.log(`+ ${file}`);
  return true;
}

function init(cwd) {
  const found = findAppRoot(cwd);
  if (!found) {
    let template = readFileSync(path.join(TEMPLATES, 'oube.config.json'), 'utf8');
    const appJson = path.join(cwd, 'app.json');
    if (existsSync(appJson)) {
      const expo = readJson(appJson).expo ?? {};
      template = template
        .replace('<scheme>', expo.scheme ?? '<scheme>')
        .replace('<ios bundle id>', expo.ios?.bundleIdentifier ?? '<ios bundle id>')
        .replace('<android package>', expo.android?.package ?? '<android package>');
    }
    writeIfMissing(path.join(cwd, 'oube.config.json'), template);
    console.log('\noube.config.json 을 작성한 뒤 oube-release init 을 다시 실행하세요.');
    return;
  }

  const config = loadConfig(found);
  for (const name of ['Fastfile', 'Deliverfile', 'README.md', 'metadata/README.md']) {
    writeIfMissing(
      path.join(found, 'fastlane', name),
      readFileSync(path.join(TEMPLATES, 'fastlane', name), 'utf8')
    );
  }
  if (config.iap) {
    writeIfMissing(
      path.join(found, 'fastlane', 'iap-products.json'),
      readFileSync(path.join(TEMPLATES, 'fastlane', 'iap-products.json'), 'utf8')
    );
  }
  const meta = path.join(found, 'fastlane', 'metadata');
  writeIfMissing(path.join(meta, 'copyright.txt'), '');
  for (const locale of Object.values(config.locales)) {
    for (const name of APP_STORE_FILES) writeIfMissing(path.join(meta, locale.appStore, name), '');
    for (const name of PLAY_FILES)
      writeIfMissing(path.join(meta, 'android', locale.play, name), '');
  }
  if (existsSync(path.join(found, 'app'))) {
    writeIfMissing(
      path.join(found, 'app', '__screenshots', '[scene].tsx'),
      readFileSync(path.join(TEMPLATES, 'app', '__screenshots', '[scene].tsx'), 'utf8')
    );
  }
  appendGitignore(found);
  console.log(
    '\n키 파일 두 개를 fastlane/ 에 넣어 주세요: asc-api-key.json.key (App Store Connect API 키), play-service-account.json.key (Play 서비스 계정)'
  );
}

function doctor() {
  const checks = [
    ['node', ['--version']],
    ['pnpm', ['--version']],
    ['jq', ['--version']],
    [
      'python3',
      ['-c', 'import PIL, numpy; print("Pillow", PIL.__version__, "numpy", numpy.__version__)'],
    ],
    ['fastlane', ['--version']],
    ['eas', ['--version']],
    ['xcrun', ['--version']],
  ];
  let missing = 0;
  for (const [command, args] of checks) {
    const result = spawnSync(command, args, { encoding: 'utf8' });
    const ok = !result.error && result.status === 0;
    if (!ok) missing++;
    const detail = ok
      ? (result.stdout || '').trim().split('\n').pop()
      : (result.error?.message ?? result.stderr.trim());
    console.log(`${ok ? 'OK     ' : 'MISSING'} ${command}  ${detail}`);
  }
  if (missing) process.exit(1);
}

function main() {
  const { flags, positional } = parseArgs(process.argv.slice(2));
  const [command, sub] = positional;
  if (!command || command === 'help' || flags.help) {
    console.log(HELP);
    return;
  }
  if (command === 'doctor') return doctor();
  if (command === 'init') return init(process.cwd());
  if (command === 'fonts') {
    const root = findAppRoot(process.cwd());
    if (!root)
      fail(
        'oube.config.json 을 찾을 수 없습니다. 앱 폴더에서 oube-release init 을 먼저 실행하세요.'
      );
    return fonts(root);
  }

  const root = findAppRoot(process.cwd());
  if (!root)
    fail('oube.config.json 을 찾을 수 없습니다. 앱 폴더에서 oube-release init 을 먼저 실행하세요.');
  const config = loadConfig(root);
  if (command === 'screenshots') return screenshots(sub, flags, root, config);
  if (command === 'metadata') return metadata(sub, root);
  fail(`알 수 없는 명령어입니다: ${command}\n\n${HELP}`);
}

main();
