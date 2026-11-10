/* Gráficos do Renda Oculta (Chart.js, arquivo local em static/vendor).
   Os dados chegam do Flask via tojson; aqui só desenhamos. */

(function () {

    const css = getComputedStyle(document.documentElement);
    const cor = (nome) => css.getPropertyValue(nome).trim();

    // Mesmas cores de destino usadas em toda a aplicação (style.css)
    const COR_DESTINO = {
        "Autoconsumo": cor("--cor-autoconsumo"),
        "Trocas": cor("--cor-trocas"),
        "Doações": cor("--cor-doacoes"),
        "Venda": cor("--cor-venda"),
    };

    const VERDES = ["#1f7a4d", "#3a9a68", "#63b585", "#8fcaa6", "#b7ddc5", "#d5e9dc"];

    const reais = (n) => "R$ " + Number(n).toLocaleString("pt-BR", {
        minimumFractionDigits: 2, maximumFractionDigits: 2
    });

    const reaisCurto = (n) => "R$ " + Number(n).toLocaleString("pt-BR", {
        maximumFractionDigits: 0
    });

    Chart.defaults.font.family = 'Figtree, "Segoe UI", Arial, sans-serif';
    Chart.defaults.font.size = 12;
    Chart.defaults.color = cor("--muda");
    Chart.defaults.plugins.legend.display = false;
    Chart.defaults.plugins.tooltip.backgroundColor = cor("--floresta");
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 10;
    Chart.defaults.plugins.tooltip.displayColors = false;

    const grade = { color: cor("--linha"), drawTicks: false };

    const criar = (id, config) => {
        const el = document.getElementById(id);
        return el ? new Chart(el, config) : null;
    };

    window.RC = {

        // 1) Rosca: distribuição da produção por destino
        rosca(id, destinos) {
            const total = destinos.reduce((s, d) => s + d[1], 0);
            return criar(id, {
                type: "doughnut",
                data: {
                    labels: destinos.map(d => d[0]),
                    datasets: [{
                        data: destinos.map(d => d[1]),
                        backgroundColor: destinos.map(d => COR_DESTINO[d[0]]),
                        borderColor: "#fff", borderWidth: 3, hoverOffset: 4,
                    }]
                },
                options: {
                    maintainAspectRatio: false, cutout: "68%",
                    plugins: { tooltip: { callbacks: {
                        label: (c) => c.label + ": " + reais(c.parsed) +
                            " (" + Math.round(c.parsed / total * 100) + "%)"
                    } } }
                }
            });
        },

        // 2) Barras: valor econômico por destino
        barras(id, destinos) {
            return criar(id, {
                type: "bar",
                data: {
                    labels: destinos.map(d => d[0]),
                    datasets: [{
                        data: destinos.map(d => d[1]),
                        backgroundColor: destinos.map(d => COR_DESTINO[d[0]]),
                        borderRadius: 8, maxBarThickness: 56,
                    }]
                },
                options: {
                    maintainAspectRatio: false,
                    scales: {
                        x: { grid: { display: false }, border: { display: false },
                             ticks: { maxRotation: 0, autoSkip: false, font: { size: 11 } } },
                        y: { beginAtZero: true, grid: grade, border: { display: false },
                             ticks: { callback: reaisCurto, maxTicksLimit: 5 } }
                    },
                    plugins: { tooltip: { callbacks: { label: (c) => reais(c.parsed.y) } } }
                }
            });
        },

        // 3) Linha: valor acumulado ao longo do tempo
        linha(id, pontos) {
            const el = document.getElementById(id);
            if (!el) return null;
            const ctx = el.getContext("2d");
            const fundo = ctx.createLinearGradient(0, 0, 0, el.parentElement.clientHeight || 250);
            fundo.addColorStop(0, "rgba(31,122,77,.28)");
            fundo.addColorStop(1, "rgba(31,122,77,0)");
            return new Chart(el, {
                type: "line",
                data: {
                    labels: pontos.map(p => p[0]),
                    datasets: [{
                        data: pontos.map(p => p[1]),
                        borderColor: cor("--folha"), backgroundColor: fundo, fill: true,
                        borderWidth: 3, tension: .35,
                        pointRadius: 5, pointBackgroundColor: "#fff",
                        pointBorderColor: cor("--folha"), pointBorderWidth: 3,
                    }]
                },
                options: {
                    maintainAspectRatio: false,
                    scales: {
                        x: { grid: { display: false }, border: { display: false } },
                        y: { beginAtZero: true, grid: grade, border: { display: false },
                             ticks: { callback: reaisCurto, maxTicksLimit: 5 } }
                    },
                    plugins: { tooltip: { callbacks: { label: (c) => reais(c.parsed.y) } } }
                }
            });
        },

        // 4) Barras horizontais: distribuição por produto
        produtos(id, itens) {
            return criar(id, {
                type: "bar",
                data: {
                    labels: itens.map(i => i[0]),
                    datasets: [{
                        data: itens.map(i => i[1]),
                        backgroundColor: itens.map((_, i) => VERDES[i % VERDES.length]),
                        borderRadius: 6, barThickness: 18,
                    }]
                },
                options: {
                    indexAxis: "y", maintainAspectRatio: false,
                    scales: {
                        x: { beginAtZero: true, grid: grade, border: { display: false },
                             ticks: { callback: reaisCurto, maxTicksLimit: 4 } },
                        y: { grid: { display: false }, border: { display: false },
                             ticks: { callback: function (v) {
                                 const t = this.getLabelForValue(v);
                                 return t.length > 16 ? t.slice(0, 15) + "…" : t;
                             } } }
                    },
                    plugins: { tooltip: { callbacks: {
                        title: (c) => c[0].label,
                        label: (c) => reais(c.parsed.x)
                    } } }
                }
            });
        },

        // 5) Comparação entre meses: valor econômico x renda monetária
        comparar(id, meses) {
            return criar(id, {
                type: "bar",
                data: {
                    labels: meses.map(m => m[0]),
                    datasets: [
                        { label: "Valor econômico (estimado)", data: meses.map(m => m[1]),
                          backgroundColor: cor("--cor-doacoes"), borderRadius: 6 },
                        { label: "Renda monetária", data: meses.map(m => m[2]),
                          backgroundColor: cor("--cor-venda"), borderRadius: 6 },
                    ]
                },
                options: {
                    maintainAspectRatio: false,
                    scales: {
                        x: { grid: { display: false }, border: { display: false } },
                        y: { beginAtZero: true, grid: grade, border: { display: false },
                             ticks: { callback: reaisCurto, maxTicksLimit: 5 } }
                    },
                    plugins: {
                        legend: { display: true, position: "bottom" },
                        tooltip: { displayColors: true, callbacks: { label: (c) => c.dataset.label + ": " + reais(c.parsed.y) } }
                    }
                }
            });
        },
    };

})();
