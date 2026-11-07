// Visor de trayectorias: mapa → provincia → líneas por ciclo. Datos en window.DATOS y window.GEO.
(function () {
  "use strict";

  const D = window.DATOS;
  const G = window.GEO;
  const NS = "http://www.w3.org/2000/svg";
  const DIMENSIONES = ["sector", "ambito", "sexo"];
  const ETIQUETA_VALOR = {
    Estatal: "Estatal", Privado: "Privado", Urbano: "Urbano", Rural: "Rural",
    mujeres: "Mujeres", varones: "Varones",
  };
  const NIVEL_TEXTO = { primaria: "Primaria", secundaria: "Secundaria", ambos: "Primaria y secundaria" };

  const estado = {
    prov: null,
    ind: "repitencia",
    medida: "cantidad",
    nivel: "secundaria",
    sexo: "total",
    ambito: "total",
    sector: "total",
  };

  const fmtEntero = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 });
  const fmtTasa = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  // ---------- Estado en la URL (enlaces compartibles) ----------
  function leerHash() {
    const p = new URLSearchParams(location.hash.slice(1));
    for (const clave of Object.keys(estado)) {
      if (p.has(clave)) estado[clave] = p.get(clave);
    }
    if (estado.prov && estado.prov !== D.total_pais && !D.provincias.includes(estado.prov)) estado.prov = null;
    if (!D.indicadores[estado.ind]) estado.ind = "repitencia";
    for (const dim of DIMENSIONES) {
      if (!["total", "desagregar"].includes(estado[dim])) estado[dim] = "total";
    }
    if (!["primaria", "secundaria", "ambos"].includes(estado.nivel)) estado.nivel = "secundaria";
    if (!["cantidad", "tasa"].includes(estado.medida)) estado.medida = "cantidad";
  }
  function escribirHash() {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries(estado)) if (v) p.set(k, v);
    history.replaceState(null, "", "#" + p.toString());
  }

  // ---------- Mapa ----------
  function trazar(svg, viewBox, provincias) {
    svg.setAttribute("viewBox", viewBox);
    for (const p of provincias) {
      const path = document.createElementNS(NS, "path");
      path.setAttribute("d", p.d);
      path.setAttribute("class", "prov");
      path.setAttribute("tabindex", "0");
      path.setAttribute("role", "button");
      path.setAttribute("aria-label", p.nombre);
      path.dataset.prov = p.nombre;
      const titulo = document.createElementNS(NS, "title");
      titulo.textContent = p.nombre;
      path.appendChild(titulo);
      path.addEventListener("click", () => elegir(p.nombre));
      path.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); elegir(p.nombre); }
      });
      path.addEventListener("mouseenter", () => { hover.textContent = p.nombre; });
      path.addEventListener("mouseleave", () => { hover.textContent = textoHoverBase(); });
      svg.appendChild(path);
    }
  }
  const hover = document.getElementById("nombre-hover");
  function textoHoverBase() {
    return estado.prov && estado.prov !== D.total_pais ? estado.prov : "Tocá una provincia";
  }

  function marcarSeleccion() {
    document.querySelectorAll(".prov").forEach((el) => {
      el.classList.toggle("seleccionada", el.dataset.prov === estado.prov);
    });
    document.getElementById("btn-pais").setAttribute("aria-pressed", String(estado.prov === D.total_pais));
    hover.textContent = textoHoverBase();
  }

  function elegir(prov) {
    estado.prov = prov;
    marcarSeleccion();
    escribirHash();
    render();
    if (window.matchMedia("(max-width: 820px)").matches) {
      document.getElementById("panel").scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  // ---------- Controles ----------
  function armarControles() {
    const cont = document.getElementById("opc-ind");
    for (const [clave, meta] of Object.entries(D.indicadores)) {
      const label = document.createElement("label");
      label.innerHTML = `<input type="radio" name="ind" value="${clave}"> ${meta.etiqueta}`;
      cont.appendChild(label);
    }
    const form = document.getElementById("controles");
    form.addEventListener("change", (e) => {
      estado[e.target.name] = e.target.value;
      escribirHash();
      render();
    });
  }

  function sincronizarControles() {
    const meta = D.indicadores[estado.ind];
    const sinTasa = !meta.formula;
    if (sinTasa && estado.medida === "tasa") estado.medida = "cantidad";
    const form = document.getElementById("controles");
    for (const nombre of ["ind", "medida", "nivel", "sexo", "ambito", "sector"]) {
      form.querySelectorAll(`input[name="${nombre}"]`).forEach((inp) => {
        inp.checked = inp.value === estado[nombre];
      });
    }
    form.querySelector('input[name="medida"][value="tasa"]').disabled = sinTasa;
    const aviso = document.getElementById("aviso-medida");
    aviso.hidden = !sinTasa;
    aviso.textContent = sinTasa ? `${meta.etiqueta} se muestra solo como cantidad.` : "";
    const fijo = Boolean(meta.fija_sector);
    form.querySelectorAll('input[name="sector"]').forEach((inp) => {
      inp.disabled = fijo;
      if (fijo) inp.checked = inp.value === "total";
    });
    const avisoSector = document.getElementById("aviso-sector");
    avisoSector.hidden = !fijo;
    avisoSector.textContent = fijo ? "Este indicador ya compara estatal y privado." : "";
  }

  function dimensionAbierta(dim) {
    if (dim === "sector" && D.indicadores[estado.ind].fija_sector) return false;
    return estado[dim] === "desagregar";
  }

  // ---------- Cálculo ----------
  function combinaciones() {
    const abiertas = DIMENSIONES.filter(dimensionAbierta);
    let combos = [{}];
    for (const dim of abiertas) {
      const nuevas = [];
      for (const c of combos) for (const v of D.valores[dim]) nuevas.push({ ...c, [dim]: v });
      combos = nuevas;
    }
    return combos;
  }

  function sumar(combo) {
    const niveles = estado.nivel === "ambos" ? ["primaria", "secundaria"] : [estado.nivel];
    const n = D.ciclos.length;
    const acum = {};
    for (const nivel of niveles) {
      const celdas = (D.celdas[estado.prov] || {})[nivel] || {};
      for (const [clave, conteos] of Object.entries(celdas)) {
        const [sector, ambito, sexo] = clave.split("|");
        const valores = { sector, ambito, sexo };
        if (Object.entries(combo).some(([dim, v]) => valores[dim] !== v)) continue;
        for (const [conteo, serie] of Object.entries(conteos)) {
          if (!acum[conteo]) acum[conteo] = new Array(n).fill(0);
          for (let i = 0; i < n; i++) acum[conteo][i] += serie[i];
        }
      }
    }
    return acum;
  }

  // Hay oferta si el grupo tuvo alumnos en el ciclo (o los esperaba por el pase de año).
  // Sin oferta el punto queda vacío: un 0 se leería como "ningún repitente" y no "no hay escuelas".
  const CONTEOS_OFERTA = ["inicial", "ultimo_con_resultado", "esperados", "egresados"];
  function conOferta(y, acum) {
    return y.map((v, i) => (CONTEOS_OFERTA.some((c) => ((acum[c] || [])[i] || 0) > 0) ? v : null));
  }

  // Serie del indicador elegido para una combinación de sector/ámbito/sexo.
  function serieDe(combo) {
    const meta = D.indicadores[estado.ind];
    const n = D.ciclos.length;
    const esTasa = estado.medida === "tasa" && meta.formula;
    const cero = new Array(n).fill(0);
    let y;
    if (meta.formula && meta.formula.especial === "participacion_privada") {
      const privado = sumar({ ...combo, sector: "Privado" });
      if (esTasa) {
        const acumTotal = sumar(combo);
        const total = acumTotal.inicial || cero;
        y = (privado.inicial || cero).map((v, i) => (total[i] > 0 ? (v / total[i]) * 100 : null));
        y = conOferta(y, acumTotal);
      } else {
        y = conOferta((privado.perdida || cero).map((v) => -v), privado);
      }
    } else {
      const acum = sumar(combo);
      if (esTasa) {
        const num = acum[meta.formula.numerador] || cero;
        y = D.ciclos.map((_, i) => {
          const den = meta.formula.denominadores.reduce((s, c) => s + ((acum[c] || [])[i] || 0), 0);
          return den > 0 ? (num[i] / den) * 100 : null;
        });
      } else {
        y = (acum[meta.cantidad] || cero).slice();
      }
      y = conOferta(y, acum);
    }
    const desde = (esTasa ? meta.primer_ciclo_tasa : meta.primer_ciclo_cantidad) ?? meta.primer_ciclo;
    return desde ? y.map((v, i) => (D.ciclos[i] < desde ? null : v)) : y;
  }


  // Color por sector × ámbito (orden fijo de la paleta); el sexo se distingue por trazo.
  function color(combo, css) {
    const s = combo.sector, a = combo.ambito;
    if (s && a) {
      return css({ "Estatal|Urbano": "--serie-1", "Privado|Urbano": "--serie-2",
        "Estatal|Rural": "--serie-3", "Privado|Rural": "--serie-4" }[`${s}|${a}`]);
    }
    if (s) return css(s === "Estatal" ? "--serie-1" : "--serie-2");
    if (a) return css(a === "Urbano" ? "--serie-7" : "--serie-6");
    return css("--serie-1");
  }

  function nombre(combo) {
    const partes = DIMENSIONES.filter((d) => combo[d]).map((d) => ETIQUETA_VALOR[combo[d]]);
    return partes.length ? partes.join(" · ") : "Total";
  }

  // Etiqueta al final de cada línea, separadas verticalmente para que no se pisen.
  function etiquetasDirectas(series, cssVar) {
    const ultimo = D.ciclos.length - 1;
    const maximo = Math.max(...series.flatMap((s) => s.y.filter((v) => v !== null)), 0) || 1;
    const separacion = maximo * 0.07;
    const puntos = series
      .map((s) => ({ texto: s.nombre, y: s.y[ultimo] ?? 0 }))
      .sort((a, b) => a.y - b.y);
    for (let i = 1; i < puntos.length; i++) {
      puntos[i].y = Math.max(puntos[i].y, puntos[i - 1].y + separacion);
    }
    return puntos.map((p) => ({
      x: D.ciclos[ultimo], y: p.y, text: p.texto, showarrow: false, xanchor: "left", xshift: 10,
      font: { color: cssVar("--tinta-2"), size: 12 },
    }));
  }

  // ---------- Render ----------
  function render() {
    const vacio = document.getElementById("panel-vacio");
    const contenido = document.getElementById("panel-contenido");
    if (!estado.prov) { vacio.hidden = false; contenido.hidden = true; return; }
    vacio.hidden = true;
    contenido.hidden = false;
    sincronizarControles();

    const meta = D.indicadores[estado.ind];
    const esTasa = estado.medida === "tasa";
    const abiertas = DIMENSIONES.filter(dimensionAbierta);
    const unidad = esTasa ? (meta.unidad_tasa || "%") : (meta.unidad_cantidad || meta.unidad);
    const sufijo = esTasa ? " %" : "";
    const cssVar = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

    document.getElementById("titulo-panel").textContent = estado.prov;
    const corte = abiertas.length
      ? " · por " + abiertas.map((d) => ({ sector: "sector", ambito: "ámbito", sexo: "sexo" })[d]).join(", ")
      : "";
    document.getElementById("subtitulo-panel").textContent =
      `${NIVEL_TEXTO[estado.nivel]} · ${meta.etiqueta} (${unidad})${corte}` +
      ` · ciclos ${D.ciclos[0]}–${D.ciclos[D.ciclos.length - 1]}`;

    const alertas = D.alertas[`${estado.prov}|${estado.nivel}|${estado.ind}`] || {};
    const combos = combinaciones();
    const todas = combos.map((c) => ({
      combo: c,
      nombre: nombre(c),
      y: serieDe(c),
    }));
    const series = todas.filter((s) => s.y.some((v) => v !== null));
    const omitidas = todas.filter((s) => !series.includes(s)).map((s) => s.nombre);
    const nota = document.getElementById("nota-series");
    nota.hidden = omitidas.length === 0;
    nota.textContent = omitidas.length
      ? `Sin alumnos en ${estado.prov} (${NIVEL_TEXTO[estado.nivel].toLowerCase()}): ${omitidas.join(", ")}. ` +
        "No hay escuelas de ese tipo, por eso no se dibuja la línea."
      : "";
    if (todas.length && !series.length) {
      Plotly.purge("grafico");
      document.getElementById("tabla").innerHTML = "";
      return;
    }

    const trazas = series.map((s) => {
      const conAlerta = D.ciclos.map((c) => Boolean(alertas[c]));
      const col = color(s.combo, cssVar);
      return {
        type: "scatter",
        mode: "lines+markers",
        name: s.nombre,
        x: D.ciclos,
        y: s.y,
        line: { color: col, width: 2, dash: s.combo.sexo === "varones" ? "dash" : "solid" },
        marker: {
          color: col,
          size: conAlerta.map((a) => (a ? 12 : 7)),
          symbol: conAlerta.map((a) => (a ? "x" : "circle")),
          line: { color: cssVar("--superficie"), width: conAlerta.map((a) => (a ? 0 : 1.5)) },
        },
        customdata: D.ciclos.map((c) => alertas[c] || ""),
        hovertemplate:
          `<b>${s.nombre}</b> · ciclo %{x}<br>${meta.etiqueta}: ` +
          (esTasa ? `%{y:.2f}${sufijo}` : "%{y:,.0f}") + "<br><i>%{customdata}</i><extra></extra>",
        connectgaps: false,
      };
    });

    const etiquetas = series.length <= 4 && series.length > 1 ? etiquetasDirectas(series, cssVar) : [];

    const ancho = document.getElementById("grafico").clientWidth;
    const layout = {
      paper_bgcolor: cssVar("--superficie"),
      plot_bgcolor: cssVar("--superficie"),
      font: { family: "system-ui, -apple-system, Segoe UI, sans-serif", color: cssVar("--tinta"), size: 13 },
      separators: ",.",
      margin: { l: 64, r: etiquetas.length ? Math.min(170, ancho * 0.28) : 16, t: 24, b: 40 },
      hovermode: "closest",
      showlegend: series.length > 1,
      legend: { orientation: "h", y: -0.14, x: 0 },
      xaxis: {
        dtick: 1, range: [D.ciclos[0] - 0.5, D.ciclos[D.ciclos.length - 1] + 0.5],
        showgrid: false, linecolor: cssVar("--eje"), tickfont: { color: cssVar("--tinta-tenue") },
        tickangle: ancho < 560 ? -45 : 0, fixedrange: true,
      },
      yaxis: {
        gridcolor: cssVar("--grilla"), linecolor: cssVar("--eje"),
        tickfont: { color: cssVar("--tinta-tenue") }, rangemode: "tozero",
        zeroline: true, zerolinecolor: cssVar("--eje"), zerolinewidth: 1.5,
        ticksuffix: sufijo, fixedrange: true,
      },
      shapes: [{
        type: "rect", xref: "x", yref: "paper", x0: 2019.5, x1: 2020.5, y0: 0, y1: 1,
        fillcolor: cssVar("--banda"), line: { width: 0 }, layer: "below",
      }],
      annotations: [
        { x: 2020, y: 1, xref: "x", yref: "paper", yanchor: "bottom", text: "Pandemia",
          showarrow: false, font: { size: 11, color: cssVar("--tinta-tenue") } },
        ...etiquetas,
      ],
    };
    Plotly.react("grafico", trazas, layout, { displaylogo: false, responsive: true,
      modeBarButtonsToRemove: ["lasso2d", "select2d", "zoom2d", "pan2d", "zoomIn2d", "zoomOut2d", "autoScale2d"] });

    let definicion = meta.descripcion;
    if (esTasa && meta.formula) {
      definicion += ` ${meta.formula_texto}`;
    }
    document.getElementById("definicion").textContent = definicion;

    const lista = document.getElementById("alertas-panel");
    lista.innerHTML = "";
    for (const [ciclo, texto] of Object.entries(alertas)) {
      const li = document.createElement("li");
      li.textContent = `Ciclo ${ciclo}: ${texto}`;
      lista.appendChild(li);
    }

    const tabla = document.getElementById("tabla");
    const fmt = (v) => (v === null ? "—" : esTasa ? fmtTasa.format(v) + sufijo : fmtEntero.format(v));
    let filas = `<thead><tr><th>Ciclo</th>${series.map((s) => `<th>${s.nombre}</th>`).join("")}</tr></thead><tbody>`;
    D.ciclos.forEach((c, i) => {
      filas += `<tr><td>${c}${alertas[c] ? " ✕" : ""}</td>${series.map((s) => `<td>${fmt(s.y[i])}</td>`).join("")}</tr>`;
    });
    tabla.innerHTML = filas + "</tbody>";
  }

  // ---------- Inicio ----------
  trazar(document.getElementById("svg-mapa"), G.viewBox, G.provincias);
  trazar(document.getElementById("svg-caba"), G.recuadro_caba.viewBox, [G.recuadro_caba]);
  document.getElementById("btn-pais").addEventListener("click", () => elegir(D.total_pais));
  armarControles();
  leerHash();
  marcarSeleccion();
  render();
  window.addEventListener("hashchange", () => { leerHash(); marcarSeleccion(); render(); });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
})();
