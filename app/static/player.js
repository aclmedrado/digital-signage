/* Uma mídia e um polling por vez. Nenhuma credencial acessível pelo script. */
(() => {
  "use strict";
  const stage = document.getElementById("stage");
  const status = document.getElementById("status");
  const connection = document.getElementById("connection");
  const endpoint = document.body.dataset.manifest;
  let current = null, pending = null, index = -1, failures = 0;
  let media = null, mediaTimer = null, watchdog = null, pollTimer = null;
  let generation = 0, inFlight = false, stopped = false, blocked = false;
  let retryDelay = 20000, requestController = null, sleeping = false;

  function clearMedia() {
    generation += 1;
    clearTimeout(mediaTimer);
    clearInterval(watchdog);
    mediaTimer = watchdog = null;
    if (media) {
      media.onload = media.onerror = media.onended = null;
      if (media.tagName === "VIDEO") media.pause();
      media.removeAttribute("src");
      if (media.tagName === "VIDEO") media.load();
      media.remove();
      media = null;
    }
  }

  function neutral(message) {
    clearMedia();
    status.textContent = message;
    status.hidden = false;
  }

  function waitForRetry() {
    neutral("Conteúdo temporariamente indisponível. Aguardando nova tentativa…");
    sleeping = true;
    mediaTimer = setTimeout(() => {
      sleeping = false;
      failures = 0;
      if (!stopped && !blocked) advance();
    }, 20000);
  }

  function advance() {
    if (stopped || blocked || sleeping) return;
    clearMedia();
    if (pending) {
      current = pending;
      pending = null;
      index = -1;
      failures = 0;
    }
    if (!current || current.state !== "playing" || current.items.length === 0) {
      neutral("Sem conteúdo disponível.");
      return;
    }
    index = (index + 1) % current.items.length;
    const item = current.items[index];
    const ticket = generation;
    let finished = false;
    function finish(failed) {
      if (finished || ticket !== generation || stopped) return;
      finished = true;
      if (failed) failures += 1;
      else failures = 0;
      clearMedia();
      if (failures >= current.items.length) return waitForRetry();
      // Uma falha nunca dispara uma cadeia síncrona nem reintentos por segundo.
      mediaTimer = setTimeout(advance, failed ? 2000 : 0);
    }
    status.textContent = "Carregando conteúdo…";
    status.hidden = false;
    media = document.createElement(item.kind === "video" ? "video" : "img");
    const element = media;
    element.onerror = () => finish(true);
    mediaTimer = setTimeout(() => finish(true), 30000); // Limite de carregamento.
    if (item.kind === "image") {
      element.alt = "";
      element.onload = () => {
        if (ticket !== generation || finished) return;
        clearTimeout(mediaTimer);
        status.hidden = true;
        mediaTimer = setTimeout(() => finish(false), item.duration_seconds * 1000);
      };
    } else {
      element.muted = true;
      element.autoplay = true;
      element.playsInline = true;
      element.preload = "auto";
      element.controls = false;
      element.onended = () => finish(false);
      let previousTime = 0, lastProgress = performance.now();
      // Watchdog de progresso, independente da duração do vídeo; só ended
      // termina uma reprodução saudável. Aba oculta não é tratada como travamento.
      watchdog = setInterval(() => {
        if (document.hidden) { lastProgress = performance.now(); return; }
        if (element.currentTime > previousTime) {
          previousTime = element.currentTime;
          lastProgress = performance.now();
          status.hidden = true;
          clearTimeout(mediaTimer);
        } else if (performance.now() - lastProgress >= 45000) finish(true);
      }, 5000);
    }
    stage.append(element);
    element.src = item.url;
    if (item.kind === "video") {
      try {
        const promise = element.play();
        if (promise && typeof promise.catch === "function") promise.catch(() => finish(true));
      } catch (_error) { finish(true); }
    }
  }

  function validManifest(value) {
    if (!value || typeof value.revision !== "string" || !Array.isArray(value.items) || value.items.length > 100) return false;
    if (!["playing", "screen_inactive", "no_playlist", "playlist_unavailable"].includes(value.state)) return false;
    const mediaPrefix = endpoint.slice(0, -"manifest".length) + "media/";
    return value.items.every(item => {
      if (!item || !["image", "video"].includes(item.kind) || typeof item.url !== "string") return false;
      if (!item.url.startsWith(mediaPrefix) || !/^[0-9]+$/.test(item.url.slice(mediaPrefix.length))) return false;
      return item.kind === "video" ? item.duration_seconds === null :
        Number.isInteger(item.duration_seconds) && item.duration_seconds >= 5 && item.duration_seconds <= 600;
    });
  }

  async function poll() {
    if (inFlight || stopped) return;
    clearTimeout(pollTimer);
    inFlight = true;
    requestController = new AbortController();
    const timeout = setTimeout(() => requestController.abort(), 10000);
    try {
      const response = await fetch(endpoint, {credentials: "same-origin", cache: "no-store",
        redirect: "error", signal: requestController.signal});
      if ([401, 403, 404].includes(response.status)) {
        blocked = true;
        sleeping = false;
        current = pending = null;
        index = -1;
        neutral("Acesso indisponível. Ative novamente o dispositivo.");
        connection.hidden = true;
        retryDelay = 20000;
        return;
      }
      if (!response.ok) throw new Error("indisponível");
      const next = await response.json();
      if (!validManifest(next)) throw new Error("manifesto inválido");
      connection.hidden = true;
      retryDelay = 20000;
      blocked = false;
      if (next.state !== "playing" || next.items.length === 0) {
        sleeping = false;
        current = next;
        pending = null;
        index = -1;
        neutral("Sem conteúdo disponível.");
      } else {
        if (!current || current.revision !== next.revision) pending = next;
        else pending = null; // Desfaz também uma alteração pendente revertida.
        if (!media && !sleeping) advance();
      }
    } catch (_error) {
      if (!stopped) {
        connection.hidden = false;
        retryDelay = Math.min(retryDelay * 2, 120000);
        // Sem garantia offline: limpa a mídia e exige manifesto fresco ao voltar.
        sleeping = false;
        current = pending = null;
        index = -1;
        neutral("Conexão indisponível. Aguardando programação…");
      }
    } finally {
      clearTimeout(timeout);
      requestController = null;
      inFlight = false;
      // Jitter de 0–2 s; uma única requisição, próxima só depois desta terminar.
      if (!stopped) pollTimer = setTimeout(poll, retryDelay + Math.random() * 2000);
    }
  }

  window.addEventListener("pagehide", () => {
    stopped = true;
    clearTimeout(pollTimer);
    if (requestController) requestController.abort();
    clearMedia();
  });
  window.addEventListener("pageshow", event => {
    if (event.persisted) {
      stopped = false;
      current = pending = null;
      index = -1;
      sleeping = false;
      poll();
    }
  });
  poll();
})();
