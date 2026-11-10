/* Uso offline (RF19): registra sem internet e sincroniza depois.
   Também registra o service worker (PWA) e limpa o cache ao sair. */

(function () {

    const CHAVE = "rc_fila";
    const uid = (document.querySelector('meta[name="user-id"]') || {}).content || "";
    const csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";

    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/sw.js").catch(function () {});
    }

    // Ao sair, apaga páginas guardadas no aparelho
    document.querySelectorAll('form[action$="/sair"]').forEach(function (f) {
        f.addEventListener("submit", function () {
            if (navigator.serviceWorker && navigator.serviceWorker.controller) {
                navigator.serviceWorker.controller.postMessage("limpar");
            }
        });
    });

    function lerFila() {
        try { return JSON.parse(localStorage.getItem(CHAVE) || "[]"); } catch (e) { return []; }
    }

    function gravarFila(fila) {
        try { localStorage.setItem(CHAVE, JSON.stringify(fila)); } catch (e) {}
    }

    function aviso(texto, erro) {
        const main = document.querySelector("main");
        if (!main) return;
        const el = document.createElement("div");
        el.className = "alert " + (erro ? "alert-bad" : "alert-ok");
        el.setAttribute("role", "alert");
        el.textContent = texto;
        main.prepend(el);
        setTimeout(function () { el.remove(); }, 8000);
    }

    function atualizarPendentes() {
        const n = lerFila().filter(function (i) { return i.uid === uid; }).length;
        const el = document.getElementById("fila-aviso");
        if (!el) return;
        el.hidden = n === 0;
        el.textContent = n + (n === 1 ? " registro aguardando" : " registros aguardando") + " conexão para sincronizar.";
    }

    // Formulário de produção: sem internet, guarda no aparelho
    const form = document.getElementById("form-producao");
    if (form) {
        form.addEventListener("submit", function (ev) {
            if (navigator.onLine) return;
            ev.preventDefault();
            if (!form.reportValidity()) return;

            const dados = {};
            new FormData(form).forEach(function (v, k) { if (k !== "csrf_token") dados[k] = v; });

            const fila = lerFila();
            fila.push({ id: Date.now() + "-" + Math.random().toString(36).slice(2), uid: uid, dados: dados });
            gravarFila(fila);

            form.reset();
            aviso("Sem internet: o registro foi salvo no aparelho e será enviado quando a conexão voltar.", false);
            atualizarPendentes();
        });
    }

    // Quando a internet volta, envia o que ficou guardado
    let enviando = false;   // evita envio duplicado (evento 'online' + carregamento da página)

    function sincronizar() {
        if (enviando) return;
        const fila = lerFila();
        const meus = fila.filter(function (i) { return i.uid === uid; });
        if (!meus.length || !navigator.onLine || !uid) return;
        enviando = true;
        const enviados_ids = meus.map(function (i) { return i.id; });

        fetch("/producao/sincronizar", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
            body: JSON.stringify({ itens: meus.map(function (i) { return i.dados; }) })
        })
            .then(function (r) {
                if (!r.ok || !(r.headers.get("content-type") || "").includes("json")) throw new Error();
                return r.json();
            })
            .then(function (resp) {
                const erros = [];
                resp.resultados.forEach(function (r) { if (!r.ok) erros.push(r.erro); });
                // remove da fila só o que foi enviado (relê, pois pode ter entrado algo novo)
                gravarFila(lerFila().filter(function (i) { return enviados_ids.indexOf(i.id) === -1; }));
                enviando = false;
                atualizarPendentes();

                const enviados = resp.resultados.length - erros.length;
                if (enviados) aviso(enviados + " registro(s) sincronizado(s).", false);
                if (erros.length) aviso("Não foi possível enviar " + erros.length + " registro(s): " + erros[0], true);
                if (enviados) setTimeout(function () { location.reload(); }, 1500);
            })
            .catch(function () { enviando = false; /* tenta de novo na próxima vez */ });
    }

    window.addEventListener("online", sincronizar);
    atualizarPendentes();
    sincronizar();

})();
