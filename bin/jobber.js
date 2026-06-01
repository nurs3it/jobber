#!/usr/bin/env node
/**
 * Jobber CLI — управление установкой, версиями, расписанием и логином.
 *
 * Распределение ответственности:
 *   - Этот Node-CLI ставит/обновляет/удаляет Jobber и регистрирует его в Claude Code.
 *   - Повседневная работа (поиск вакансий, дайджест) идёт через Claude Code (slash-команды + MCP),
 *     где LLM-шаги делает сам Claude. Python-движок живёт в venv внутри ~/.jobber.
 *
 * Данные пользователя: ~/.jobber (config.yaml, .env, *.session, vault, storage, venv).
 * Код пакета: каталог npm-пакета (этот файл лежит в <pkg>/bin/).
 *
 * Без внешних npm-зависимостей — только встроенные модули Node.
 */

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const cp = require('child_process');
const readline = require('readline');

// --- Константы путей ---
const PKG_ROOT = path.resolve(__dirname, '..');
const PKG = require(path.join(PKG_ROOT, 'package.json'));
const REPO_SLUG = 'nurs3it/jobber';

const HOME = process.env.JOBBER_HOME
  ? path.resolve(expandHome(process.env.JOBBER_HOME))
  : path.join(os.homedir(), '.jobber');
const VENV = path.join(HOME, 'venv');
const VENV_BIN = path.join(VENV, process.platform === 'win32' ? 'Scripts' : 'bin');
const VENV_PY = path.join(VENV_BIN, process.platform === 'win32' ? 'python.exe' : 'python');
const STATE_FILE = path.join(HOME, 'state.json');
const MCP_WRAPPER = path.join(HOME, 'mcp-server.sh');
const CLAUDE_HOME = path.join(os.homedir(), '.claude');

// --- Утилиты вывода ---
const c = {
  reset: '\x1b[0m', bold: '\x1b[1m', dim: '\x1b[2m',
  green: '\x1b[32m', yellow: '\x1b[33m', red: '\x1b[31m', cyan: '\x1b[36m',
};
const supportsColor = process.stdout.isTTY;
function paint(color, s) { return supportsColor ? color + s + c.reset : s; }
function log(s = '') { console.log(s); }
function ok(s) { log(paint(c.green, '✓ ') + s); }
function info(s) { log(paint(c.cyan, '→ ') + s); }
function warn(s) { log(paint(c.yellow, '⚠ ') + s); }
function fail(s) { console.error(paint(c.red, '✗ ') + s); }

function expandHome(p) {
  return p.startsWith('~') ? path.join(os.homedir(), p.slice(1)) : p;
}

// --- Запуск процессов ---
function run(cmd, args, opts = {}) {
  const res = cp.spawnSync(cmd, args, { stdio: 'inherit', ...opts });
  return res.status === 0;
}
function capture(cmd, args, opts = {}) {
  try {
    return cp.execFileSync(cmd, args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], ...opts }).trim();
  } catch (_) {
    return null;
  }
}
function which(cmd) {
  const probe = process.platform === 'win32' ? 'where' : 'which';
  return capture(probe, [cmd]) !== null;
}

function ensureDir(p) { fs.mkdirSync(p, { recursive: true }); }

function readState() {
  try { return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')); } catch (_) { return {}; }
}
function writeState(patch) {
  const state = Object.assign(readState(), patch);
  ensureDir(HOME);
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2) + '\n');
  return state;
}

function ask(question) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => rl.question(question, (a) => { rl.close(); resolve(a.trim()); }));
}

// --- Python ---
function findPython() {
  for (const cand of ['python3.11', 'python3.12', 'python3', 'python']) {
    if (which(cand)) {
      const v = capture(cand, ['-c', 'import sys;print("%d.%d"%sys.version_info[:2])']);
      if (v) {
        const [maj, min] = v.split('.').map(Number);
        if (maj === 3 && min >= 11) return cand;
      }
    }
  }
  return null;
}

// --- Канал версий (github | npm) ---
function channel() {
  return readState().channel || 'github';
}
function pkgManager() {
  const ua = process.env.npm_config_user_agent || '';
  if (ua.startsWith('yarn')) return 'yarn';
  if (which('npm')) return 'npm';
  if (which('yarn')) return 'yarn';
  return 'npm';
}
// Спецификатор для установки конкретной версии через выбранный канал.
function installSpec(version) {
  if (channel() === 'npm') {
    return PKG.name + '@' + (version || 'latest');
  }
  // github
  return 'github:' + REPO_SLUG + (version ? '#' + version : '');
}
function selfInstall(version) {
  const spec = installSpec(version);
  const pm = pkgManager();
  info(`Установка ${spec} через ${pm}...`);
  const args = pm === 'yarn' ? ['global', 'add', spec] : ['install', '-g', spec];
  return run(pm, args);
}

// --- Список доступных версий ---
function listVersions() {
  if (channel() === 'npm') {
    const out = capture('npm', ['view', PKG.name, 'versions', '--json']);
    if (!out) return [];
    try { return JSON.parse(out); } catch (_) { return []; }
  }
  // github: теги
  const out = capture('git', ['ls-remote', '--tags', `https://github.com/${REPO_SLUG}.git`]);
  if (!out) return [];
  const tags = out.split('\n')
    .map((l) => (l.split('\t')[1] || '').replace('refs/tags/', '').replace('^{}', ''))
    .filter((t) => /^v?\d+\.\d+\.\d+/.test(t));
  return [...new Set(tags)].sort(semverCmp);
}
function semverCmp(a, b) {
  const pa = a.replace(/^v/, '').split('.').map(Number);
  const pb = b.replace(/^v/, '').split('.').map(Number);
  for (let i = 0; i < 3; i++) {
    if ((pa[i] || 0) !== (pb[i] || 0)) return (pa[i] || 0) - (pb[i] || 0);
  }
  return 0;
}

// ============================================================
// Команды
// ============================================================

async function cmdSetup(flags = {}) {
  info(`Установка Jobber в ${paint(c.bold, HOME)}`);
  ensureDir(HOME);

  // 1. Python + venv
  const py = findPython();
  if (!py) {
    fail('Не найден Python 3.11+. Установите его (macOS: brew install python@3.11) и повторите.');
    process.exit(1);
  }
  if (!fs.existsSync(VENV_PY)) {
    info('Создаю виртуальное окружение...');
    if (!run(py, ['-m', 'venv', VENV])) { fail('Не удалось создать venv'); process.exit(1); }
  }

  // 2. Зависимости (editable-установка кода пакета)
  info('Устанавливаю Python-зависимости (это может занять минуту)...');
  run(VENV_PY, ['-m', 'pip', 'install', '--quiet', '--upgrade', 'pip']);
  const extra = flags.ocr ? '[ocr]' : '';
  if (!run(VENV_PY, ['-m', 'pip', 'install', '--quiet', '-e', PKG_ROOT + extra])) {
    fail('Не удалось установить Python-зависимости');
    process.exit(1);
  }

  // 3. config.yaml + .env + рабочие папки
  copyIfAbsent(path.join(PKG_ROOT, 'config.yaml'), path.join(HOME, 'config.yaml'));
  const envPath = path.join(HOME, '.env');
  if (!fs.existsSync(envPath)) {
    fs.copyFileSync(path.join(PKG_ROOT, '.env.example'), envPath);
    try { fs.chmodSync(envPath, 0o600); } catch (_) {}
    ok('Создан ~/.jobber/.env (заполните ключи в /onboard)');
  }
  ['storage', 'logs', 'profile', path.join('vault', 'Jobber')].forEach((d) => ensureDir(path.join(HOME, d)));

  // 4. Claude Code: команды, агенты, MCP
  installClaudeAssets();
  installMcp();

  // 5. Состояние
  writeState({
    channel: channel(),
    version: PKG.version,
    name: PKG.name,
    repo: REPO_SLUG,
    home: HOME,
  });

  log('');
  ok(paint(c.bold, `Jobber ${PKG.version} установлен.`));
  log('');
  log('Дальше:');
  log(`  1. ${paint(c.cyan, 'jobber login')}      — или в Claude Code: ${paint(c.cyan, '/onboard')} (резюме + ключи + вход в Telegram)`);
  log(`  2. В Claude Code: ${paint(c.cyan, '/scan')} и ${paint(c.cyan, '/digest')}`);
  log(`  3. Расписание дайджеста: ${paint(c.cyan, 'jobber schedule on')}`);
  log('');
  log(paint(c.dim, `Данные: ${HOME}  ·  Документация: https://github.com/${REPO_SLUG}`));
}

function copyIfAbsent(src, dest) {
  if (!fs.existsSync(dest)) {
    ensureDir(path.dirname(dest));
    fs.copyFileSync(src, dest);
    ok(`Создан ${dest.replace(os.homedir(), '~')}`);
  }
}

function installClaudeAssets() {
  const srcCmd = path.join(PKG_ROOT, '.claude', 'commands');
  const dstCmd = path.join(CLAUDE_HOME, 'commands');
  const srcAg = path.join(PKG_ROOT, '.claude', 'agents');
  const dstAg = path.join(CLAUDE_HOME, 'agents');
  let n = 0;
  if (fs.existsSync(srcCmd)) {
    ensureDir(dstCmd);
    for (const f of fs.readdirSync(srcCmd)) {
      if (f.endsWith('.md')) { fs.copyFileSync(path.join(srcCmd, f), path.join(dstCmd, f)); n++; }
    }
  }
  if (fs.existsSync(srcAg)) {
    ensureDir(dstAg);
    for (const f of fs.readdirSync(srcAg)) {
      if (f.endsWith('.md')) fs.copyFileSync(path.join(srcAg, f), path.join(dstAg, f));
    }
  }
  ok(`Установлены slash-команды Claude Code (${n}) в ~/.claude/commands`);
}

function installMcp() {
  // Обёртка экспортирует JOBBER_HOME и запускает MCP-сервер из venv.
  const wrapper = [
    '#!/usr/bin/env bash',
    'set -euo pipefail',
    `export JOBBER_HOME="${HOME}"`,
    `exec "${VENV_PY}" -m mcp_server`,
    '',
  ].join('\n');
  fs.writeFileSync(MCP_WRAPPER, wrapper);
  try { fs.chmodSync(MCP_WRAPPER, 0o755); } catch (_) {}

  if (which('claude')) {
    // Зарегистрировать на уровне пользователя (доступно во всех проектах).
    capture('claude', ['mcp', 'remove', 'jobber', '-s', 'user']); // снять старую, если была
    const okAdd = run('claude', ['mcp', 'add', 'jobber', '-s', 'user', '--', 'bash', MCP_WRAPPER]);
    if (okAdd) { ok('MCP-сервер jobber зарегистрирован в Claude Code (user scope)'); return; }
  }
  warn('Claude Code CLI не найден или регистрация не удалась.');
  log(`  Зарегистрируйте вручную: ${paint(c.cyan, `claude mcp add jobber -s user -- bash ${MCP_WRAPPER}`)}`);
}

async function cmdInstall(version) {
  if (version) {
    if (!selfInstall(version)) { fail('Установка версии не удалась'); process.exit(1); }
    // После замены глобального бинаря запускаем setup уже новой версией.
    if (!run('jobber', ['setup'])) warn('Запустите `jobber setup` вручную, чтобы дообновить окружение.');
    return;
  }
  await cmdSetup();
}

async function cmdUpdate() {
  let target = '';
  if (channel() === 'github') {
    const versions = listVersions();
    target = versions.length ? versions[versions.length - 1] : ''; // последний тег или main
    info(target ? `Последняя версия: ${target}` : 'Тегов не найдено — обновляюсь до main');
  }
  if (!selfInstall(target)) { fail('Обновление не удалось'); process.exit(1); }
  run('jobber', ['setup']);
}

async function cmdDowndate() {
  const versions = listVersions();
  if (versions.length < 1) { fail('Не удалось получить список версий'); process.exit(1); }
  const cur = (readState().version || PKG.version).replace(/^v/, '');
  const idx = versions.findIndex((v) => v.replace(/^v/, '') === cur);
  let prev;
  if (idx > 0) prev = versions[idx - 1];
  else if (idx === -1 && versions.length) prev = versions[versions.length - 1];
  else { fail('Нет предыдущей версии для отката'); process.exit(1); }
  info(`Откат к версии ${prev}`);
  if (!selfInstall(prev)) { fail('Откат не удался'); process.exit(1); }
  run('jobber', ['setup']);
}

async function cmdUse(version) {
  if (!version) { fail('Укажите версию: jobber install-version <версия>'); process.exit(1); }
  if (!selfInstall(version)) { fail('Установка версии не удалась'); process.exit(1); }
  run('jobber', ['setup']);
}

function cmdVersions() {
  const versions = listVersions();
  if (!versions.length) { warn('Версии не найдены (нет тегов/публикаций или нет сети).'); return; }
  const cur = (readState().version || PKG.version).replace(/^v/, '');
  log(`Доступные версии (канал: ${channel()}):`);
  for (const v of versions) {
    const mark = v.replace(/^v/, '') === cur ? paint(c.green, '  ← установлена') : '';
    log(`  ${v}${mark}`);
  }
}

async function cmdRemove(flags) {
  const purge = flags.purge;
  log(purge
    ? paint(c.yellow, 'Полное удаление: venv + конфиг + .env + сессия + vault + storage.')
    : 'Удаление окружения (venv) и регистрации в Claude Code. Данные (config/.env/сессия/vault) сохранятся.');
  const a = await ask('Продолжить? [y/N] ');
  if (!/^y(es)?$/i.test(a)) { info('Отменено.'); return; }

  // MCP + команды Claude
  if (which('claude')) capture('claude', ['mcp', 'remove', 'jobber', '-s', 'user']);
  removeClaudeAssets();

  // venv
  rmrf(VENV);
  rmrf(MCP_WRAPPER);
  ok('Окружение удалено.');

  if (purge) {
    rmrf(HOME);
    ok('Каталог данных ~/.jobber удалён.');
  } else {
    info(`Данные сохранены в ${HOME} (удалить полностью: jobber remove --purge).`);
  }

  // глобальный пакет
  const pm = pkgManager();
  const a2 = await ask(`Удалить и сам пакет (${pm} ${pm === 'yarn' ? 'global remove' : 'rm -g'} ${PKG.name})? [y/N] `);
  if (/^y(es)?$/i.test(a2)) {
    run(pm, pm === 'yarn' ? ['global', 'remove', PKG.name] : ['rm', '-g', PKG.name]);
  }
}

function removeClaudeAssets() {
  const cmdDir = path.join(CLAUDE_HOME, 'commands');
  const agDir = path.join(CLAUDE_HOME, 'agents');
  const ours = ['onboard', 'scan', 'digest', 'cover', 'profile-edit', 'sources', 'seen-reset'];
  for (const name of ours) rmrf(path.join(cmdDir, name + '.md'));
  rmrf(path.join(agDir, 'matcher.md'));
}

function rmrf(p) {
  try { fs.rmSync(p, { recursive: true, force: true }); } catch (_) {}
}

function cmdVersion() {
  const st = readState();
  log(`${paint(c.bold, 'jobber')} ${PKG.version}`);
  log(`  установленная версия: ${st.version || '—'}`);
  log(`  канал:                ${st.channel || channel()}`);
  log(`  данные (JOBBER_HOME): ${HOME}`);
  log(`  venv:                 ${fs.existsSync(VENV_PY) ? paint(c.green, 'есть') : paint(c.yellow, 'нет (jobber setup)')}`);
}

function cmdStatus() {
  log(paint(c.bold, 'Jobber — статус'));
  check('Python 3.11+', !!findPython());
  check('venv', fs.existsSync(VENV_PY));
  const depsOk = fs.existsSync(VENV_PY) &&
    run(VENV_PY, ['-c', 'import telethon, mcp, pydantic'], { stdio: 'ignore' });
  check('Python-зависимости (telethon, mcp, pydantic)', depsOk);
  check('config.yaml', fs.existsSync(path.join(HOME, 'config.yaml')));
  check('.env', fs.existsSync(path.join(HOME, '.env')));
  const sessName = readEnvValue('TG_SESSION_NAME') || 'jobber';
  check(`сессия Telegram (${sessName}.session)`, fs.existsSync(path.join(HOME, sessName + '.session')));
  check('Claude Code CLI', which('claude'));
  const mcpReg = which('claude') && (capture('claude', ['mcp', 'list']) || '').includes('jobber');
  check('MCP-сервер зарегистрирован', !!mcpReg);
  log('');
  log(paint(c.dim, `JOBBER_HOME=${HOME}`));
}

function check(label, good) {
  log(`  ${good ? paint(c.green, '✓') : paint(c.red, '✗')} ${label}`);
}

function readEnvValue(key) {
  try {
    const txt = fs.readFileSync(path.join(HOME, '.env'), 'utf8');
    const m = txt.match(new RegExp('^' + key + '=(.*)$', 'm'));
    return m ? m[1].trim() : null;
  } catch (_) { return null; }
}

function requireVenv() {
  if (!fs.existsSync(VENV_PY)) {
    fail('Окружение не установлено. Запустите: jobber setup');
    process.exit(1);
  }
}
function venvEnv() {
  return Object.assign({}, process.env, { JOBBER_HOME: HOME });
}

function cmdLogin() {
  requireVenv();
  process.exit(run(VENV_PY, ['-m', 'sources.telegram', 'login'], { env: venvEnv() }) ? 0 : 1);
}

function cmdExtract(file) {
  requireVenv();
  if (!file) { fail('Укажите файл: jobber extract <резюме.pdf|docx|png>'); process.exit(1); }
  process.exit(run(VENV_PY, ['-m', 'ingest', 'extract', file], { env: venvEnv() }) ? 0 : 1);
}

function cmdMcp() {
  requireVenv();
  // Запуск stdio MCP-сервера (для ручной проверки/отладки).
  run(VENV_PY, ['-m', 'mcp_server'], { env: venvEnv() });
}

function cmdSchedule(action) {
  const plistLabel = 'com.jobber.digest';
  const time = readScheduleTime();
  const claudeCmd = which('claude') ? 'claude' : 'claude';
  if (action === 'off') {
    if (process.platform === 'darwin') {
      const plist = path.join(os.homedir(), 'Library', 'LaunchAgents', plistLabel + '.plist');
      capture('launchctl', ['unload', plist]);
      rmrf(plist);
      ok('Расписание снято (launchd).');
    } else {
      const cur = capture('crontab', ['-l']) || '';
      const filtered = cur.split('\n').filter((l) => !l.includes('jobber') && l.trim()).join('\n');
      cp.spawnSync('crontab', ['-'], { input: filtered + '\n' });
      ok('Расписание снято (cron).');
    }
    return;
  }
  // on
  const runLine = `cd "${HOME}" && ${claudeCmd} -p "/digest" >> "${path.join(HOME, 'logs', 'schedule.log')}" 2>&1`;
  if (process.platform === 'darwin') {
    const dir = path.join(os.homedir(), 'Library', 'LaunchAgents');
    ensureDir(dir);
    const plist = path.join(dir, plistLabel + '.plist');
    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>${plistLabel}</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string><string>-lc</string><string>${runLine}</string>
  </array>
  <key>StartCalendarInterval</key><dict>
    <key>Hour</key><integer>${time.h}</integer><key>Minute</key><integer>${time.m}</integer>
  </dict>
  <key>WorkingDirectory</key><string>${HOME}</string>
</dict></plist>\n`;
    fs.writeFileSync(plist, xml);
    capture('launchctl', ['unload', plist]);
    run('launchctl', ['load', plist]);
    ok(`Дайджест по расписанию в ${pad(time.h)}:${pad(time.m)} (launchd).`);
  } else {
    const cron = `${time.m} ${time.h} * * * /bin/bash -lc '${runLine}'`;
    const cur = (capture('crontab', ['-l']) || '').split('\n').filter((l) => l.trim() && !l.includes('jobber'));
    cur.push(cron);
    cp.spawnSync('crontab', ['-'], { input: cur.join('\n') + '\n' });
    ok(`Дайджест по расписанию в ${pad(time.h)}:${pad(time.m)} (cron).`);
  }
  if (!which('claude')) warn('claude CLI не найден — расписание установлено, но запуск /digest требует Claude Code.');
}

function readScheduleTime() {
  try {
    const txt = fs.readFileSync(path.join(HOME, 'config.yaml'), 'utf8');
    const m = txt.match(/schedule_time:\s*"?(\d{1,2}):(\d{2})"?/);
    if (m) return { h: parseInt(m[1], 10), m: parseInt(m[2], 10) };
  } catch (_) {}
  return { h: 9, m: 0 };
}
function pad(n) { return String(n).padStart(2, '0'); }

function cmdHelp() {
  log(`${paint(c.bold, 'jobber')} — ассистент поиска работы по Telegram (CLI управления)

${paint(c.bold, 'Установка/версии:')}
  jobber install [версия]       Установить/настроить (опц. конкретную версию) и зарегистрировать в Claude Code
  jobber setup                  Пересобрать окружение (venv, зависимости, MCP, команды)
  jobber update                 Обновить до последней версии
  jobber downdate               Откатить на предыдущую версию
  jobber install-version <v>    Установить конкретную версию (алиас: use)
  jobber versions               Показать доступные версии
  jobber remove [--purge]       Удалить (с --purge — вместе с данными ~/.jobber)

${paint(c.bold, 'Работа:')}
  jobber login                  Войти в Telegram (код + 2FA), создать сессию
  jobber extract <файл>         Извлечь текст из резюме (pdf/docx/img)
  jobber schedule <on|off>      Включить/выключить ежедневный дайджест по расписанию
  jobber mcp                    Запустить MCP-сервер (отладка)

${paint(c.bold, 'Инфо:')}
  jobber status                 Проверить окружение (doctor)
  jobber version                Версия и пути
  jobber help                   Эта справка

${paint(c.dim, 'Повседневно: в Claude Code — /onboard, /scan, /digest, /cover, /sources, /profile-edit, /seen-reset')}
${paint(c.dim, `Данные: ${HOME}  ·  Канал версий: ${channel()}  ·  https://github.com/${REPO_SLUG}`)}`);
}

// --- Разбор аргументов ---
function parseFlags(args) {
  const flags = {};
  const rest = [];
  for (const a of args) {
    if (a === '--purge') flags.purge = true;
    else if (a === '--ocr') flags.ocr = true;
    else if (a === '--npm') flags.npm = true;
    else if (a === '--github') flags.github = true;
    else rest.push(a);
  }
  return { flags, rest };
}

async function main() {
  const [, , cmd, ...rawArgs] = process.argv;
  const { flags, rest } = parseFlags(rawArgs);

  // Переопределение канала на лету.
  if (flags.npm) writeState({ channel: 'npm' });
  if (flags.github) writeState({ channel: 'github' });

  switch (cmd) {
    case undefined:
    case 'help':
    case '-h':
    case '--help':
      return cmdHelp();
    case 'version':
    case '-v':
    case '--version':
      return cmdVersion();
    case 'setup':
      return cmdSetup(flags);
    case 'install':
      return cmdInstall(rest[0]);
    case 'update':
    case 'upgrade':
      return cmdUpdate();
    case 'downdate':
    case 'downgrade':
      return cmdDowndate();
    case 'install-version':
    case 'use':
      return cmdUse(rest[0]);
    case 'versions':
      return cmdVersions();
    case 'remove':
    case 'uninstall':
      return cmdRemove(flags);
    case 'status':
    case 'doctor':
      return cmdStatus();
    case 'login':
      return cmdLogin();
    case 'extract':
      return cmdExtract(rest[0]);
    case 'schedule':
      return cmdSchedule(rest[0] || 'on');
    case 'mcp':
      return cmdMcp();
    case '_postinstall':
      // Тихий хук npm postinstall: не делаем тяжёлую работу автоматически.
      if (!process.env.JOBBER_SILENT) {
        log('');
        ok(`Jobber ${PKG.version} установлен как CLI.`);
        info('Завершите настройку: ' + paint(c.cyan, 'jobber setup'));
        log('');
      }
      return;
    default:
      fail(`Неизвестная команда: ${cmd}`);
      cmdHelp();
      process.exit(1);
  }
}

main().catch((e) => { fail(e && e.message ? e.message : String(e)); process.exit(1); });
