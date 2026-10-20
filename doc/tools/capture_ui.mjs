// 시연 화면 캡처 — 실제 브라우저(Chrome)를 띄워 채팅을 보내고 화면을 저장한다.
//
// 왜 이렇게 하나
//   "이런 화면이 나온다"는 말을 붙이려면 실제로 화면을 캡처해야 한다.
//   만들어 낸 이미지를 붙이면 근거가 아니게 된다.
//   여기서는 8100 백엔드 + 8600 프론트엔드를 실제로 띄운 상태에서
//   Chrome DevTools Protocol로 입력·전송·스크린샷까지 수행한다.
//
// 사용:
//   node doc/tools/capture_ui.mjs --message "..." --out artifacts/captures/<id>/01.png
//
// 외부 의존성 없음 (Node 22 내장 WebSocket + fetch 사용).
import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PAGE_URL = process.env.CAPTURE_URL || "http://localhost:8600";
const PORT = Number(process.env.CAPTURE_CDP_PORT || 9222);

function arg(name, fallback = null) {
  const index = process.argv.indexOf(`--${name}`);
  return index === -1 ? fallback : process.argv[index + 1];
}

const message = arg("message", "auth-service 로그인 응답이 p95 2.4초로 느려졌어요, 원인 진단해주세요");
const out = arg("out", "artifacts/captures/capture.png");
const waitMs = Number(arg("wait", "9000"));
const viewport = (arg("viewport", "1440,900")).split(",").map(Number);
// --clip x,y,w,h — 문서 일부만 잘라 담을 때(예: 슬라이드 7번째)
const clipArg = arg("clip", null);
const clip = clipArg
  ? (([x, y, width, height]) => ({ x, y, width, height }))(clipArg.split(",").map(Number))
  : null;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function cdpTargets() {
  for (let i = 0; i < 40; i += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const list = await res.json();
      if (list.length) return list;
    } catch {
      /* 아직 안 뜬 것 */
    }
    await sleep(250);
  }
  throw new Error("Chrome 디버깅 포트에 연결하지 못했습니다");
}

class Session {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    ws.addEventListener("message", (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      }
    });
  }

  send(method, params = {}) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
  }
}

async function main() {
  await mkdir(path.dirname(out), { recursive: true });

  const chrome = spawn(CHROME, [
    "--headless=new",
    `--remote-debugging-port=${PORT}`,
    `--window-size=${viewport[0]},${viewport[1]}`,
    "--hide-scrollbars",
    "--disable-gpu",
    "--no-first-run",
    "--user-data-dir=/tmp/archify-capture-profile",
    "about:blank",
  ], { stdio: "ignore" });

  try {
    const targets = await cdpTargets();
    const page = targets.find((t) => t.type === "page");
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((resolve) => ws.addEventListener("open", resolve));
    const session = new Session(ws);

    await session.send("Page.enable");
    await session.send("Runtime.enable");
    await session.send("Emulation.setDeviceMetricsOverride", {
      width: viewport[0], height: viewport[1], deviceScaleFactor: 2, mobile: false,
    });
    await session.send("Page.navigate", { url: PAGE_URL });
    await sleep(2500);

    const expression = `(() => {
      const input = document.querySelector('#app input');
      if (!input) return 'no-input';
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(input, ${JSON.stringify(message)});
      input.dispatchEvent(new Event('input', { bubbles: true }));
      const button = document.querySelector('#app button[type=submit]');
      if (button) button.click();
      return 'sent';
    })()`;
    const result = await session.send("Runtime.evaluate", { expression, awaitPromise: true });
    const sent = result.result?.value;
    if (sent !== "sent" && sent !== "no-input") {
      throw new Error(`입력 전송 실패: ${sent}`);
    }
    if (sent === "no-input") {
      console.log("입력란이 없어 전송 없이 화면만 담았습니다.");
    }

    await sleep(waitMs);

    const shot = await session.send("Page.captureScreenshot", {
      format: "png",
      ...(clip ? { clip: { ...clip, scale: 1 }, captureBeyondViewport: true } : {}),
    });
    const { writeFile } = await import("node:fs/promises");
    await writeFile(out, Buffer.from(shot.data, "base64"));
    console.log(`saved: ${out}  (${sent}, ${message})`);
    ws.close();
  } finally {
    chrome.kill("SIGKILL");
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
