// Serves the repo and asks headless Chrome for deterministic film frames.
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const FONTS = {
  "/system-font/DejaVuSans.ttf": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
  "/system-font/DejaVuSans-Bold.ttf": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
};

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json",
  ".css": "text/css; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".wav": "audio/wav",
  ".mp3": "audio/mpeg",
  ".ttf": "font/ttf",
};

export function safePath(root, urlPath) {
  const raw = urlPath.split("?")[0];
  let decoded;
  try {
    decoded = decodeURIComponent(raw);
  } catch {
    return null;
  }
  const rel = decoded.replace(/^\/+/, "");
  if (!rel) return null;
  const full = path.resolve(root, rel);
  const base = path.resolve(root);
  if (full !== base && !full.startsWith(base + path.sep)) return null;
  return full;
}

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) {
      args._.push(token);
      continue;
    }
    const key = token.slice(2);
    const next = argv[i + 1];
    if (next === undefined || next.startsWith("--")) args[key] = true;
    else {
      args[key] = next;
      i += 1;
    }
  }
  return args;
}

function findChrome() {
  if (process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH)) return process.env.CHROME_PATH;
  for (const name of ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]) {
    const found = which(name);
    if (found) return found;
  }
  throw new Error("Chrome not found. Set CHROME_PATH.");
}

function which(name) {
  const paths = (process.env.PATH || "").split(path.delimiter);
  for (const dir of paths) {
    const candidate = path.join(dir, name);
    if (existsSync(candidate)) return candidate;
  }
  return "";
}

function startServer(root) {
  const server = createServer(async (req, res) => {
    try {
      const pathname = new URL(req.url || "/", "http://127.0.0.1").pathname;
      if (FONTS[pathname]) {
        const font = FONTS[pathname];
        if (!existsSync(font)) {
          res.writeHead(404);
          res.end("font missing");
          return;
        }
        const body = await readFile(font);
        res.writeHead(200, { "Content-Type": "font/ttf", "Cache-Control": "no-cache" });
        res.end(body);
        return;
      }
      const file = safePath(root, pathname);
      if (!file || !existsSync(file)) {
        res.writeHead(404);
        res.end("not found");
        return;
      }
      const body = await readFile(file);
      const type = TYPES[path.extname(file).toLowerCase()] || "application/octet-stream";
      res.writeHead(200, { "Content-Type": type, "Cache-Control": "no-cache" });
      res.end(body);
    } catch {
      res.writeHead(500);
      res.end("error");
    }
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      resolve({ server, port: address.port });
    });
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function debuggingPort(profile) {
  const file = path.join(profile, "DevToolsActivePort");
  for (let i = 0; i < 80; i += 1) {
    if (existsSync(file)) {
      const port = Number(readFileSync(file, "utf8").split("\n")[0].trim());
      if (port) return port;
    }
    await sleep(100);
  }
  throw new Error("Chrome did not open a debugging port");
}

async function pageSocket(port) {
  for (let i = 0; i < 80; i += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/list`);
      const list = await response.json();
      const page = list.find((target) => target.type === "page" && target.webSocketDebuggerUrl);
      if (page) return page.webSocketDebuggerUrl;
    } catch {
      // Chrome is still starting.
    }
    await sleep(100);
  }
  throw new Error("Chrome did not publish a page target");
}

function connect(ws) {
  let id = 0;
  const pending = new Map();
  const listeners = new Map();
  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const waiter = pending.get(message.id);
      if (!waiter) return;
      pending.delete(message.id);
      if (message.error) waiter.reject(new Error(message.error.message || "cdp error"));
      else waiter.resolve(message.result);
      return;
    }
    const set = listeners.get(message.method);
    if (set) for (const fn of set) fn(message.params || {});
  });
  return {
    send(method, params = {}, timeoutMs = 30000) {
      const msgId = ++id;
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
          pending.delete(msgId);
          reject(new Error(`timeout calling ${method}`));
        }, timeoutMs);
        pending.set(msgId, {
          resolve: (value) => {
            clearTimeout(timer);
            resolve(value);
          },
          reject: (error) => {
            clearTimeout(timer);
            reject(error);
          },
        });
        ws.send(JSON.stringify({ id: msgId, method, params }));
      });
    },
    once(method, timeoutMs = 30000) {
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error(`timeout waiting for ${method}`)), timeoutMs);
        const fn = (params) => {
          clearTimeout(timer);
          listeners.get(method)?.delete(fn);
          resolve(params);
        };
        if (!listeners.has(method)) listeners.set(method, new Set());
        listeners.get(method).add(fn);
      });
    },
  };
}

async function evaluate(send, expression, timeoutMs) {
  const result = await send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  }, timeoutMs);
  if (result.exceptionDetails) {
    const detail = result.exceptionDetails.exception?.description || result.exceptionDetails.text || "page error";
    throw new Error(detail);
  }
  return result.result?.value;
}

function jpegBytes(dataUrl) {
  if (typeof dataUrl !== "string" || !dataUrl.includes(",")) {
    throw new Error("captureFrame must return a JPEG data URL");
  }
  return Buffer.from(dataUrl.slice(dataUrl.indexOf(",") + 1), "base64");
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log("node studio/capture.mjs --url films/name/film.html --video out.mp4 [--params w=640&h=360] [--crf 18]");
    console.log("node studio/capture.mjs --url films/name/film.html --stills 1,4 --out dir");
    console.log("node studio/capture.mjs --serve");
    return;
  }
  const { server, port } = await startServer(ROOT);
  if (args.serve) {
    console.log(`http://127.0.0.1:${port}/films/paper-boat/film.html`);
    await new Promise(() => {});
    return;
  }
  if (!args.url) throw new Error("missing --url");
  const profile = await mkdtemp(path.join(tmpdir(), "studio-chrome-"));
  const chromeLog = [];
  const chrome = spawn(findChrome(), [
    "--headless=new",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--hide-scrollbars",
    "--remote-debugging-port=0",
    "--remote-allow-origins=*",
    `--user-data-dir=${profile}`,
    "--window-size=1280,720",
    "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });
  chrome.stderr.on("data", (chunk) => {
    chromeLog.push(String(chunk));
    if (chromeLog.length > 40) chromeLog.shift();
  });

  let ffmpeg;
  try {
    const debugPort = await debuggingPort(profile);
    const ws = new WebSocket(await pageSocket(debugPort));
    await new Promise((resolve, reject) => {
      ws.addEventListener("open", resolve);
      ws.addEventListener("error", () => reject(new Error("devtools websocket failed")));
    });
    const cdp = connect(ws);
    const query = new URLSearchParams(typeof args.params === "string" ? args.params : "");
    query.set("capture", "1");
    const rel = String(args.url).replace(/^\/+/, "");
    const pageUrl = `http://127.0.0.1:${port}/${rel}?${query.toString()}`;
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    const loaded = cdp.once("Page.loadEventFired");
    await cdp.send("Page.navigate", { url: pageUrl });
    await loaded;
    const meta = await evaluate(cdp.send, "window.STUDIO_READY");
    if (!meta || !Number.isFinite(meta.frames) || meta.frames < 1 || !Number.isFinite(meta.fps) || meta.fps <= 0) {
      throw new Error("STUDIO_READY did not describe a film");
    }

    if (args.probe) {
      console.log(JSON.stringify(meta, null, 2));
      ws.close();
      return;
    }

    if (args.stills) {
      if (!args.out) throw new Error("--stills needs --out");
      mkdirSync(args.out, { recursive: true });
      const times = String(args.stills).split(",").map((part) => Number(part.trim()));
      for (const time of times) {
        if (!Number.isFinite(time) || time < 0) throw new Error(`bad still time: ${time}`);
        const frame = Math.min(meta.frames - 1, Math.round(time * meta.fps));
        const bytes = jpegBytes(await evaluate(cdp.send, `window.captureFrame(${frame})`));
        const name = `t-${time.toFixed(3)}.jpg`;
        writeFileSync(path.join(args.out, name), bytes);
        console.error(`still ${name}`);
      }
      ws.close();
      return;
    }

    if (!args.video) throw new Error("pass --video, --stills, --probe, or --serve");
    const crf = String(args.crf || "18");
    ffmpeg = spawn("ffmpeg", [
      "-y",
      "-f", "image2pipe",
      "-framerate", String(meta.fps),
      "-vcodec", "mjpeg",
      "-i", "pipe:0",
      "-an",
      "-c:v", "libx264",
      "-pix_fmt", "yuv420p",
      "-crf", crf,
      "-preset", "veryfast",
      "-movflags", "+faststart",
      args.video,
    ], { stdio: ["pipe", "ignore", "pipe"] });
    let ffErr = "";
    ffmpeg.stderr.on("data", (chunk) => {
      ffErr += chunk;
      if (ffErr.length > 4000) ffErr = ffErr.slice(-4000);
    });
    const ffDone = new Promise((resolve, reject) => {
      ffmpeg.on("error", reject);
      ffmpeg.on("close", (code) => {
        if (code === 0) resolve();
        else reject(new Error(`ffmpeg exited ${code}\n${ffErr}`));
      });
    });
    for (let frame = 0; frame < meta.frames; frame += 1) {
      const bytes = jpegBytes(await evaluate(cdp.send, `window.captureFrame(${frame})`, 60000));
      if (!ffmpeg.stdin.write(bytes)) await new Promise((resolve) => ffmpeg.stdin.once("drain", resolve));
      if (frame % meta.fps === 0) console.error(`frame ${frame}/${meta.frames}`);
    }
    ffmpeg.stdin.end();
    await ffDone;
    writeFileSync(`${args.video}.json`, JSON.stringify(meta, null, 2));
    console.error(`picture ${meta.width}x${meta.height} ${meta.frames} frames`);
    ws.close();
  } catch (error) {
    if (ffmpeg && !ffmpeg.killed) ffmpeg.kill("SIGKILL");
    const tail = chromeLog.join("").trim().split("\n").slice(-8).join("\n");
    if (tail) console.error(tail);
    throw error;
  } finally {
    try { chrome.kill("SIGKILL"); } catch { /* already gone */ }
    await sleep(150);
    server.close();
    await rm(profile, { recursive: true, force: true }).catch(() => {});
  }
}

const isMain = process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;
if (isMain) {
  main().catch((error) => {
    console.error(error.message || error);
    process.exit(1);
  });
}
