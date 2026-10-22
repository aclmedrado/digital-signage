/* Testes de lógica com DOM/relógio simulados. NÃO são testes de browser/codecs. */
const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const vm = require("node:vm");
const source = readFileSync("app/static/player.js", "utf8");

function schedule(revision = "one", state = "playing") {
  return {revision, state, items: state === "playing" ? [
    {id: 1, kind: "image", duration_seconds: 6, url: "/player/s/tv/media/1"},
    {id: 2, kind: "video", duration_seconds: null, url: "/player/s/tv/media/2"},
    {id: 3, kind: "image", duration_seconds: 8, url: "/player/s/tv/media/1"}
  ] : []};
}

function harness() {
  let now = 0, serial = 0, activeRequests = 0;
  const timers = new Map(), events = {}, elements = [];
  const nodes = {stage: {append(element) { elements.push(element); }}, status: {hidden: false}, connection: {hidden: true}};
  const h = {reply: schedule(), statusCode: 200, rejectPlay: false, calls: 0, maxRequests: 0};
  const document = {hidden: false, body: {dataset: {manifest: "/player/s/tv/manifest"}},
    getElementById: id => nodes[id],
    createElement(tag) {
      return {tagName: tag.toUpperCase(), currentTime: 0,
        removeAttribute(name) { delete this[name]; }, remove() { this.removed = true; },
        load() {}, pause() { this.paused = true; },
        play() { return h.rejectPlay ? Promise.reject(new Error("autoplay")) : Promise.resolve(); }};
    }};
  function timer(fn, delay, interval = 0) {
    const id = ++serial;
    timers.set(id, {fn, at: now + delay, interval});
    return id;
  }
  vm.runInNewContext(source, {document, window: {addEventListener: (name, fn) => { events[name] = fn; }},
    performance: {now: () => now}, AbortController,
    Math: {random: () => 0, min: Math.min},
    setTimeout: (fn, delay) => timer(fn, delay), clearTimeout: id => timers.delete(id),
    setInterval: (fn, delay) => timer(fn, delay, delay), clearInterval: id => timers.delete(id),
    fetch: async (_url, options) => {
      h.calls += 1;
      activeRequests += 1;
      h.maxRequests = Math.max(h.maxRequests, activeRequests);
      assert.equal(options.credentials, "same-origin");
      assert.equal(options.cache, "no-store");
      try {
        if (h.networkError) throw new Error("offline");
        if (h.hold) await new Promise(resolve => { h.release = resolve; });
        return {status: h.statusCode, ok: h.statusCode === 200, json: async () => h.reply};
      } finally { activeRequests -= 1; }
    }});
  h.flush = async () => { for (let i = 0; i < 10; i += 1) await Promise.resolve(); };
  h.tick = async milliseconds => {
    const end = now + milliseconds;
    let iterations = 0;
    for (;;) {
      const next = [...timers.entries()].filter(([, value]) => value.at <= end).sort((a, b) => a[1].at - b[1].at)[0];
      if (!next) break;
      assert.ok(++iterations < 1000, "sem loop apertado");
      const [id, value] = next;
      now = value.at;
      if (value.interval) value.at += value.interval;
      else timers.delete(id);
      value.fn();
      await h.flush();
    }
    now = end;
    await h.flush();
  };
  h.last = () => elements.at(-1);
  h.elements = elements;
  h.nodes = nodes;
  h.events = events;
  h.timerCount = () => timers.size;
  h.document = document;
  return h;
}

async function startVideo(h) {
  await h.flush();
  h.last().onload();
  await h.tick(6000);
  assert.equal(h.last().tagName, "VIDEO");
  return h.last();
}

test("imagem conta duração após load e vídeo inicia mudo", async () => {
  const h = harness();
  await h.flush();
  const image = h.last();
  await h.tick(3000);
  assert.equal(h.last(), image);
  image.onload();
  await h.tick(5999);
  assert.equal(h.last(), image);
  await h.tick(1);
  const video = h.last();
  assert.equal(video.tagName, "VIDEO");
  assert.ok(video.muted && video.autoplay && video.playsInline);
  assert.equal(video.controls, false);
  assert.equal(image.src, undefined);
  assert.equal(image.onload, null);
});

test("vídeo só avança por ended; repetição tem duração por item e loop", async () => {
  const h = harness();
  const video = await startVideo(h);
  for (let progress = 1; progress <= 8; progress += 1) {
    video.currentTime = progress * 5;
    await h.tick(5000);
    assert.equal(h.last(), video);
  }
  video.onended();
  await h.tick(0);
  const repeated = h.last();
  assert.equal(repeated.tagName, "IMG");
  repeated.onload();
  await h.tick(7999);
  assert.equal(h.last(), repeated);
  await h.tick(1);
  assert.notEqual(h.last(), repeated);
  assert.equal(h.last().src, "/player/s/tv/media/1");
  assert.ok(video.paused && video.removed);
});

test("atualização aguarda transição do vídeo", async () => {
  const h = harness();
  const video = await startVideo(h);
  h.reply = schedule("two");
  h.reply.items = [{id: 4, kind: "image", duration_seconds: 10, url: "/player/s/tv/media/9"}];
  video.currentTime = 1;
  await h.tick(14000);
  assert.equal(h.last(), video);
  assert.equal(h.calls, 2);
  video.onended();
  await h.tick(0);
  assert.equal(h.last().src, "/player/s/tv/media/9");
});

for (const code of [401, 403, 404]) {
  test(`HTTP ${code} interrompe e limpa mídia na próxima verificação`, async () => {
    const h = harness();
    const video = await startVideo(h);
    h.statusCode = code;
    video.currentTime = 1;
    await h.tick(14000);
    assert.ok(video.removed && video.paused);
    assert.equal(video.src, undefined);
    assert.match(h.nodes.status.textContent, /Ative novamente/);
  });
}

test("desativação interrompe vídeo e reativação recupera programação", async () => {
  const h = harness();
  const video = await startVideo(h);
  h.reply = schedule("off", "screen_inactive");
  video.currentTime = 1;
  await h.tick(14000);
  assert.ok(video.removed);
  h.reply = schedule("back");
  await h.tick(20000);
  assert.equal(h.last().tagName, "IMG");
  assert.notEqual(h.last(), video);
});

test("sequência inteiramente defeituosa espera pelo menos 20 segundos", async () => {
  const h = harness();
  await h.flush();
  h.last().onerror();
  await h.tick(2000);
  h.last().onerror();
  await h.tick(2000);
  h.last().onerror();
  const count = h.elements.length;
  await h.tick(19999);
  assert.equal(h.elements.length, count);
  await h.tick(1);
  assert.equal(h.elements.length, count + 1);
});

test("play rejeitado e listeners antigos não duplicam avanço", async () => {
  const h = harness();
  await h.flush();
  const oldError = h.last().onerror;
  h.rejectPlay = true;
  h.last().onload();
  await h.tick(6000);
  const video = h.last();
  assert.ok(video.removed);
  oldError();
  await h.tick(1999);
  assert.equal(h.last(), video);
  await h.tick(1);
  assert.equal(h.last().tagName, "IMG");
  assert.equal(h.elements.length, 3);
});

test("falha de rede limpa conteúdo e recupera com manifesto fresco", async () => {
  const h = harness();
  const video = await startVideo(h);
  h.networkError = true;
  video.currentTime = 1;
  await h.tick(14000);
  assert.ok(video.removed);
  assert.equal(h.nodes.connection.hidden, false);
  h.networkError = false;
  h.reply = schedule("fresh");
  await h.tick(39999);
  assert.equal(h.calls, 2);
  await h.tick(1);
  assert.equal(h.calls, 3);
  assert.equal(h.last().tagName, "IMG");
  assert.equal(h.nodes.connection.hidden, true);
});

test("polling não sobrepõe requisições e pagehide limpa timers", async () => {
  const h = harness();
  await h.flush();
  h.hold = true;
  await h.tick(20000);
  assert.equal(h.calls, 2);
  await h.tick(5000);
  assert.equal(h.calls, 2);
  h.release();
  await h.flush();
  assert.equal(h.maxRequests, 1);
  h.events.pagehide();
  assert.equal(h.timerCount(), 0);
  await h.tick(120000);
  assert.equal(h.calls, 2);
});

test("watchdog avança vídeo sem progresso sem usar duração de imagem", async () => {
  const h = harness();
  const video = await startVideo(h);
  video.currentTime = 1;
  await h.tick(5000);
  await h.tick(45000);
  assert.ok(video.removed);
  await h.tick(2000);
  assert.equal(h.last().tagName, "IMG");
});

test("manifesto com URL externa é recusado", async () => {
  const h = harness();
  h.reply = schedule("invalid");
  h.reply.items[0].url = "https://example.invalid/media";
  await h.flush();
  assert.equal(h.elements.length, 0);
  assert.equal(h.nodes.connection.hidden, false);
});
