#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, '..');
const outputPath = path.join(repoRoot, 'docs', 'assets', 'archipam-showcase.gif');
const receiptPath = path.join(repoRoot, 'docs', 'assets', 'archipam-showcase.receipt.json');
const width = 1280;
const height = 720;
const fps = 8;
const framesPerScene = 7;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

const scenes = [
  {
    id: 'architecture',
    artifact: 'examples/web-app-rendered.html',
    view: 'model',
    eyebrow: 'Architecture · model',
    title: 'Trace a request across the system',
    receipt: 'A checked dependency view, ready to inspect',
  },
  {
    id: 'workflow',
    artifact: 'examples/workflow-agent-tool-call-rendered.html',
    view: 'model',
    eyebrow: 'Workflow · model',
    title: 'See ownership and handoffs at a glance',
    receipt: 'A compact path through agents, tools, and outcomes',
  },
  {
    id: 'sequence',
    artifact: 'examples/sequence-cache-miss-request.html',
    view: 'model',
    eyebrow: 'Sequence · model',
    title: 'Follow timing without reading source first',
    receipt: 'Calls, waits, and responses stay in one evidence-backed view',
  },
  {
    id: 'dataflow',
    artifact: 'examples/dataflow-product-analytics.html',
    view: 'model',
    eyebrow: 'Dataflow · model',
    title: 'Make data movement reviewable',
    receipt: 'Sources, transformations, stores, and consumers remain explicit',
  },
  {
    id: 'lifecycle',
    artifact: 'examples/lifecycle-agent-run.html',
    view: 'model',
    eyebrow: 'Lifecycle · model',
    title: 'Turn state transitions into an inspection surface',
    receipt: 'Transitions, guards, and terminal states are visible before rollout',
  },
];

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function commandExists(command) {
  return spawnSync(process.platform === 'win32' ? 'where' : 'which', [command], { stdio: 'ignore' }).status === 0;
}

function requireCommand(command, hint) {
  if (!commandExists(command)) throw new Error(`${command} is required. ${hint}`);
  return command;
}

function findChrome() {
  const explicit = process.env.ARCHIPAM_CHROME;
  if (explicit && fs.existsSync(explicit)) return explicit;
  const candidates = process.platform === 'darwin'
    ? ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Chromium.app/Contents/MacOS/Chromium']
    : process.platform === 'win32'
      ? [
          path.join(process.env.PROGRAMFILES || '', 'Google', 'Chrome', 'Application', 'chrome.exe'),
          path.join(process.env['PROGRAMFILES(X86)'] || '', 'Google', 'Chrome', 'Application', 'chrome.exe'),
          path.join(process.env.LOCALAPPDATA || '', 'Google', 'Chrome', 'Application', 'chrome.exe'),
        ]
      : ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser'];
  for (const candidate of candidates) if (candidate && fs.existsSync(candidate)) return candidate;
  for (const command of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
    if (commandExists(command)) return command;
  }
  return null;
}

function esc(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function wrapperHtml(scene, sceneIndex) {
  const artifactUrl = pathToFileURL(path.join(repoRoot, scene.artifact)).href;
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root{--fade:0}
  *{box-sizing:border-box}
  html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#071019;color:#edf5ff;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace}
  body{position:relative;background:radial-gradient(circle at 82% 12%,rgba(79,149,255,.16),transparent 28%),linear-gradient(180deg,#09131f,#050b11)}
  .shell{position:absolute;inset:22px;border:1px solid rgba(146,186,230,.24);border-radius:20px;overflow:hidden;background:#0a141f;box-shadow:0 20px 70px rgba(0,0,0,.34)}
  iframe{display:block;width:100%;height:100%;border:0;background:white}
  .hud{position:absolute;left:42px;right:42px;top:38px;display:flex;justify-content:space-between;gap:32px;align-items:flex-start;pointer-events:none;text-shadow:0 2px 14px rgba(0,0,0,.9)}
  .eyebrow{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:#9bc2ec;margin-bottom:8px}
  .title{font-size:25px;font-weight:800;max-width:690px;line-height:1.12;color:#fff}
  .receipt{font-size:12px;line-height:1.45;text-align:right;color:#b8cee4;max-width:330px;background:rgba(5,11,17,.78);border:1px solid rgba(146,186,230,.2);border-radius:12px;padding:10px 12px;backdrop-filter:blur(5px)}
  .receipt strong{display:block;color:#70d7aa;font-size:10px;letter-spacing:.12em;margin-bottom:4px}
  .fade{position:absolute;inset:0;background:#071019;opacity:var(--fade);pointer-events:none;transition:opacity .12s linear}
</style>
</head>
<body>
  <div class="shell"><iframe src="${artifactUrl}#view=${encodeURIComponent(scene.view)}" title="${esc(scene.title)}"></iframe></div>
  <div class="hud">
    <div><div class="eyebrow">${esc(scene.eyebrow)}</div><div class="title">${esc(scene.title)}</div></div>
    <div class="receipt"><strong>GENERATED · CHECKED · INTERACTIVE</strong>${esc(scene.receipt)}</div>
  </div>
  <div class="fade"></div>
  <script>
    window.__archipamShowcaseReady=false;
    const frame=document.querySelector('iframe');
    frame.addEventListener('load',()=>setTimeout(()=>{window.__archipamShowcaseReady=true},260),{once:true});
  </script>
</body>
</html>`;
}

class PipeCdp {
  constructor(child) {
    this.child = child;
    this.nextId = 1;
    this.buffer = '';
    this.pending = new Map();
    this.waiters = [];
    child.stdio[4].setEncoding('utf8');
    child.stdio[4].on('data', chunk => this.consume(chunk));
    child.once('exit', code => this.failAll(new Error(`Chrome exited before capture completed (${code})`)));
  }

  consume(chunk) {
    this.buffer += chunk;
    let boundary;
    while ((boundary = this.buffer.indexOf('\0')) >= 0) {
      const raw = this.buffer.slice(0, boundary);
      this.buffer = this.buffer.slice(boundary + 1);
      if (!raw) continue;
      const message = JSON.parse(raw);
      if (message.id) {
        const pending = this.pending.get(message.id);
        if (!pending) continue;
        clearTimeout(pending.timer);
        this.pending.delete(message.id);
        if (message.error) pending.reject(new Error(`${pending.method}: ${message.error.message}`));
        else pending.resolve(message.result || {});
        continue;
      }
      for (const waiter of [...this.waiters]) {
        if (waiter.method !== message.method) continue;
        if (waiter.sessionId && waiter.sessionId !== message.sessionId) continue;
        clearTimeout(waiter.timer);
        this.waiters.splice(this.waiters.indexOf(waiter), 1);
        waiter.resolve(message.params || {});
      }
    }
  }

  send(method, params = {}, sessionId = undefined, timeoutMs = 15000) {
    const id = this.nextId++;
    const message = { id, method, params };
    if (sessionId) message.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`${method}: timed out after ${timeoutMs}ms`));
      }, timeoutMs);
      this.pending.set(id, { method, resolve, reject, timer });
      this.child.stdio[3].write(`${JSON.stringify(message)}\0`);
    });
  }

  waitFor(method, sessionId, timeoutMs = 15000) {
    return new Promise((resolve, reject) => {
      const waiter = { method, sessionId, resolve, reject, timer: null };
      waiter.timer = setTimeout(() => {
        this.waiters.splice(this.waiters.indexOf(waiter), 1);
        reject(new Error(`${method}: event timed out after ${timeoutMs}ms`));
      }, timeoutMs);
      this.waiters.push(waiter);
    });
  }

  failAll(error) {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    for (const waiter of this.waiters) {
      clearTimeout(waiter.timer);
      waiter.reject(error);
    }
    this.pending.clear();
    this.waiters = [];
  }
}

async function evaluate(cdp, sessionId, expression, awaitPromise = false) {
  const result = await cdp.send('Runtime.evaluate', {
    expression,
    awaitPromise,
    returnByValue: true,
  }, sessionId);
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text || 'Runtime.evaluate failed');
  }
  return result.result?.value;
}

async function captureFrames(chromePath, tempRoot) {
  const profileRoot = path.join(tempRoot, 'profile');
  const framesRoot = path.join(tempRoot, 'frames');
  fs.mkdirSync(profileRoot, { recursive: true });
  fs.mkdirSync(framesRoot, { recursive: true });

  const chromeArgs = [
    '--headless=new', '--remote-debugging-pipe', '--disable-gpu', '--hide-scrollbars',
    '--disable-background-networking', '--disable-component-update', '--disable-default-apps',
    '--disable-sync', '--metrics-recording-only', '--no-first-run', '--no-default-browser-check',
    '--disable-background-timer-throttling', '--disable-backgrounding-occluded-windows',
    '--disable-renderer-backgrounding', '--force-device-scale-factor=1',
    `--window-size=${width},${height}`, `--user-data-dir=${profileRoot}`, 'about:blank',
  ];
  if ((typeof process.getuid === 'function' && process.getuid() === 0) || process.env.ARCHIPAM_CHROME_NO_SANDBOX === '1') chromeArgs.unshift('--no-sandbox');

  const chrome = spawn(chromePath, chromeArgs, { stdio: ['ignore', 'ignore', 'pipe', 'pipe', 'pipe'] });
  let chromeErrors = '';
  chrome.stderr.setEncoding('utf8');
  chrome.stderr.on('data', chunk => { chromeErrors = `${chromeErrors}${chunk}`.slice(-8000); });
  const cdp = new PipeCdp(chrome);

  try {
    const targets = await cdp.send('Target.getTargets');
    let target = targets.targetInfos?.find(item => item.type === 'page');
    if (!target) {
      // Chrome 152+ rejects width/height on Target.createTarget unless newWindow=true.
      // The viewport is set explicitly below through Emulation.setDeviceMetricsOverride,
      // so target creation should remain geometry-free and browser-version agnostic.
      const created = await cdp.send('Target.createTarget', { url: 'about:blank' });
      target = { targetId: created.targetId };
    }
    const attached = await cdp.send('Target.attachToTarget', { targetId: target.targetId, flatten: true });
    const sessionId = attached.sessionId;
    await cdp.send('Page.enable', {}, sessionId);
    await cdp.send('Runtime.enable', {}, sessionId);
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width, height, deviceScaleFactor: 1, mobile: false,
    }, sessionId);

    let frameIndex = 0;
    for (const [sceneIndex, scene] of scenes.entries()) {
      const wrapperPath = path.join(tempRoot, `showcase-${scene.id}.html`);
      fs.writeFileSync(wrapperPath, wrapperHtml(scene, sceneIndex));
      const loaded = cdp.waitFor('Page.loadEventFired', sessionId);
      const navigation = await cdp.send('Page.navigate', { url: pathToFileURL(wrapperPath).href }, sessionId);
      if (navigation.errorText) throw new Error(`${scene.id}: ${navigation.errorText}`);
      await loaded;
      await evaluate(cdp, sessionId, `new Promise((resolve,reject)=>{const end=Date.now()+12000;const poll=()=>window.__archipamShowcaseReady?resolve(true):Date.now()>end?reject(new Error('artifact load timeout')):setTimeout(poll,40);poll()})`, true);

      for (let i = 0; i < framesPerScene; i += 1) {
        const fade = i === 0 ? 0.82 : i === 1 ? 0.38 : i === framesPerScene - 1 ? 0.42 : 0;
        await evaluate(cdp, sessionId, `document.documentElement.style.setProperty('--fade','${fade}')`);
        if (i > 0) await sleep(88);
        const screenshot = await cdp.send('Page.captureScreenshot', {
          format: 'png', fromSurface: true, captureBeyondViewport: false,
        }, sessionId, 20000);
        const filename = `frame-${String(frameIndex).padStart(4, '0')}.png`;
        fs.writeFileSync(path.join(framesRoot, filename), Buffer.from(screenshot.data, 'base64'));
        frameIndex += 1;
      }
    }
    return { framesRoot, frameCount: frameIndex };
  } catch (error) {
    if (chromeErrors.trim()) error.message += `\nChrome diagnostics:\n${chromeErrors.trim()}`;
    throw error;
  } finally {
    cdp.failAll(new Error('capture finished'));
    if (chrome.exitCode === null) {
      let exited = new Promise(resolve => chrome.once('exit', resolve));
      chrome.kill('SIGTERM');
      await Promise.race([exited, sleep(2000)]);
      if (chrome.exitCode === null) {
        exited = new Promise(resolve => chrome.once('exit', resolve));
        chrome.kill('SIGKILL');
        await Promise.race([exited, sleep(5000)]);
      }
    }
  }
}

function buildGif(ffmpeg, framesRoot) {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  const filter = [
    `fps=${fps},scale=${width}:${height}:flags=lanczos,split[s0][s1]`,
    '[s0]palettegen=max_colors=112:stats_mode=diff[p]',
    '[s1][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle',
  ].join(';');
  const result = spawnSync(ffmpeg, [
    '-y', '-loglevel', 'error', '-framerate', String(fps),
    '-i', path.join(framesRoot, 'frame-%04d.png'),
    '-filter_complex', filter, '-loop', '0', outputPath,
  ], { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(`ffmpeg failed:\n${result.stderr || result.stdout}`);
}

async function main() {
  for (const scene of scenes) {
    const artifact = path.join(repoRoot, scene.artifact);
    if (!fs.existsSync(artifact)) throw new Error(`${scene.id}: missing ${scene.artifact}; run node scripts/build-gallery.mjs`);
  }
  const chromePath = findChrome();
  if (!chromePath) throw new Error('Chrome or Chromium is required. Set ARCHIPAM_CHROME to its executable path.');
  const ffmpeg = requireCommand('ffmpeg', 'Install it with your system package manager.');
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'archipam-readme-showcase-'));
  try {
    const { framesRoot, frameCount } = await captureFrames(chromePath, tempRoot);
    buildGif(ffmpeg, framesRoot);
    const receipt = {
      schemaVersion: 1,
      generator: 'scripts/build-readme-showcase.mjs',
      output: path.relative(repoRoot, outputPath),
      width,
      height,
      fps,
      frameCount,
      durationSeconds: frameCount / fps,
      bytes: fs.statSync(outputPath).size,
      sha256: sha256(outputPath),
      scenes: scenes.map(scene => ({
        id: scene.id,
        artifact: scene.artifact,
        artifactSha256: sha256(path.join(repoRoot, scene.artifact)),
        view: scene.view,
        eyebrow: scene.eyebrow,
        title: scene.title,
        receipt: scene.receipt,
      })),
    };
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`);
    console.log(`README showcase ${frameCount} frames / ${receipt.durationSeconds.toFixed(1)}s / ${receipt.bytes} bytes`);
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 8, retryDelay: 125 });
  }
}

main().catch(error => {
  console.error(error?.stack || error);
  process.exitCode = 1;
});
