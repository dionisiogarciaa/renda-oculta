/* Service worker do Renda Oculta: instalação (PWA) e uso offline. */

const VERSAO = "rc-v1";
const BASICO = [
    "/offline",
    "/static/style.css",
    "/static/charts.js",
    "/static/offline.js",
    "/static/vendor/bootstrap.min.css",
    "/static/vendor/bootstrap.bundle.min.js",
    "/static/vendor/chart.umd.js",
    "/static/vendor/fonts/figtree-latin-400-normal.woff2",
    "/static/vendor/fonts/figtree-latin-600-normal.woff2",
    "/static/vendor/fonts/figtree-latin-700-normal.woff2",
    "/static/vendor/fonts/figtree-latin-800-normal.woff2",
    "/static/icons/icon-192.png",
];

self.addEventListener("install", (e) => {
    e.waitUntil(caches.open(VERSAO).then((c) => c.addAll(BASICO)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
    e.waitUntil(
        caches.keys()
            .then((nomes) => Promise.all(nomes.filter((n) => n !== VERSAO).map((n) => caches.delete(n))))
            .then(() => self.clients.claim())
    );
});

// Ao sair da conta, apaga as páginas guardadas (aparelho compartilhado)
self.addEventListener("message", (e) => {
    if (e.data === "limpar") e.waitUntil(caches.delete(VERSAO));
});

self.addEventListener("fetch", (e) => {
    const req = e.request;
    const url = new URL(req.url);
    if (req.method !== "GET" || url.origin !== location.origin) return;

    // Páginas: tenta a rede; sem internet, usa a última versão vista
    if (req.mode === "navigate") {
        e.respondWith(
            fetch(req)
                .then((res) => {
                    if (res.ok && !res.redirected) {
                        const copia = res.clone();
                        caches.open(VERSAO).then((c) => c.put(req, copia));
                    }
                    return res;
                })
                .catch(() => caches.match(req).then((r) => r || caches.match("/offline")))
        );
        return;
    }

    // Arquivos estáticos: do cache primeiro
    if (url.pathname.startsWith("/static/")) {
        e.respondWith(
            caches.match(req).then((r) => r || fetch(req).then((res) => {
                const copia = res.clone();
                caches.open(VERSAO).then((c) => c.put(req, copia));
                return res;
            }))
        );
    }
});
