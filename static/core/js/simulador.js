/**
 * simulador.js — Simulador de Crédito Hipotecario KCM
 *
 * Calcula cuota mensual por sistema francés (amortización constante).
 * Lee window.__UF_HOY_CLP del script global de base.html para
 * mostrar el equivalente en CLP en tiempo real.
 *
 * Dependencias: ninguna (vanilla JS).
 */

(function () {
  "use strict";

  /* =====================================================
     CONSTANTES / DEFAULTS
  ===================================================== */
  const DEFAULTS = {
    pie_pct: 20,      // % pie inicial
    plazo_anos: 20,   // años del crédito
    tasa_anual: 4.5,  // tasa anual referencial del mercado (%)
  };

  /* =====================================================
     UTILIDADES
  ===================================================== */

  /** Formatea número como CLP. */
  function fmtCLP(n) {
    if (!Number.isFinite(n)) return "—";
    return new Intl.NumberFormat("es-CL", {
      style: "currency",
      currency: "CLP",
      maximumFractionDigits: 0,
    }).format(Math.round(n));
  }

  /** Formatea número como UF con 2 decimales. */
  function fmtUF(n) {
    if (!Number.isFinite(n)) return "—";
    return new Intl.NumberFormat("es-CL", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(n) + " UF";
  }

  /**
   * Cuota mensual sistema francés.
   * @param {number} capital     — monto del crédito (en la misma unidad que quieras la cuota)
   * @param {number} tasaMensual — tasa mensual en decimal (e.g. 0.00375)
   * @param {number} nCuotas    — número total de cuotas
   * @returns {number} cuota mensual
   */
  function cuotaFrancesa(capital, tasaMensual, nCuotas) {
    if (tasaMensual === 0) return capital / nCuotas;
    const factor = Math.pow(1 + tasaMensual, nCuotas);
    return (capital * tasaMensual * factor) / (factor - 1);
  }

  /* =====================================================
     FUNCIÓN PRINCIPAL — CALCULAR Y PINTAR RESULTADOS
  ===================================================== */
  function calcular(sim) {
    const precioUF   = parseFloat(sim.dataset.precioUf) || 0;
    const piePct     = parseFloat(sim.querySelector("[data-sim-pie]").value) || 0;
    const plazoAnos  = parseInt(sim.querySelector("[data-sim-plazo]").value, 10) || 0;
    const tasaAnual  = parseFloat(sim.querySelector("[data-sim-tasa]").value) || 0;

    // Porcentaje del pie → monto pie y monto a financiar (UF)
    const pieUF      = (precioUF * piePct) / 100;
    const creditoUF  = precioUF - pieUF;

    // Tasa mensual decimal
    const tasaMensual = tasaAnual / 100 / 12;
    const nCuotas     = plazoAnos * 12;

    // Cuota mensual en UF
    const cuotaUF = cuotaFrancesa(creditoUF, tasaMensual, nCuotas);

    // Equivalentes CLP usando el tipo de cambio del día (si ya se cargó)
    const ufHoy        = window.__UF_HOY_CLP;
    const cuotaCLP     = Number.isFinite(ufHoy) ? cuotaUF * ufHoy : NaN;
    const creditoCLP   = Number.isFinite(ufHoy) ? creditoUF * ufHoy : NaN;
    const pieCLP       = Number.isFinite(ufHoy) ? pieUF * ufHoy : NaN;
    const totalPagoCLP = Number.isFinite(ufHoy) ? cuotaUF * nCuotas * ufHoy : NaN;

    // --- Pintar valores en el DOM ---
    setText(sim, "[data-res-pie-uf]",     fmtUF(pieUF));
    setText(sim, "[data-res-pie-clp]",    Number.isFinite(pieCLP) ? fmtCLP(pieCLP) : "");
    setText(sim, "[data-res-credito-uf]", fmtUF(creditoUF));
    setText(sim, "[data-res-credito-clp]",Number.isFinite(creditoCLP) ? fmtCLP(creditoCLP) : "");
    setText(sim, "[data-res-cuota-uf]",   fmtUF(cuotaUF));
    setText(sim, "[data-res-cuota-clp]",  Number.isFinite(cuotaCLP)   ? fmtCLP(cuotaCLP)   : "");
    setText(sim, "[data-res-total-clp]",  Number.isFinite(totalPagoCLP) ? fmtCLP(totalPagoCLP) : "");
    setText(sim, "[data-res-ncuotas]",    nCuotas > 0 ? `${nCuotas} cuotas` : "—");

    // Actualizar display de los rangos
    const pieDisplay   = sim.querySelector("[data-display-pie]");
    const plazoDisplay = sim.querySelector("[data-display-plazo]");
    const tasaDisplay  = sim.querySelector("[data-display-tasa]");
    if (pieDisplay)   pieDisplay.textContent   = piePct + "%";
    if (plazoDisplay) plazoDisplay.textContent = plazoAnos + " años";
    if (tasaDisplay)  tasaDisplay.textContent  = tasaAnual.toFixed(2) + "% anual";

    // Mostrar badge de advertencia si tasa o plazo son poco habituales
    const badge = sim.querySelector("[data-sim-disclaimer]");
    if (badge) badge.classList.toggle("d-none", tasaAnual >= 2 && tasaAnual <= 8);
  }

  function setText(root, selector, value) {
    const el = root.querySelector(selector);
    if (el) el.textContent = value;
  }

  /* =====================================================
     INICIALIZACIÓN DE CADA WIDGET .kcm-simulador
  ===================================================== */
  function initSimulador(sim) {
    let precioUF = parseFloat(sim.dataset.precioUf);
    const precioCLP = parseFloat(sim.dataset.precioClp);

    // Si no hay precio en UF pero sí hay precio en CLP, calculamos UF dinámicamente
    if (!Number.isFinite(precioUF) && Number.isFinite(precioCLP) && precioCLP > 0) {
      if (Number.isFinite(window.__UF_HOY_CLP) && window.__UF_HOY_CLP > 0) {
        precioUF = precioCLP / window.__UF_HOY_CLP;
        sim.dataset.precioUf = precioUF.toString();
      } else {
        // Esperar a que se cargue el tipo de cambio del script global
        const checkUF = setInterval(() => {
          if (Number.isFinite(window.__UF_HOY_CLP) && window.__UF_HOY_CLP > 0) {
            clearInterval(checkUF);
            sim.dataset.precioUf = (precioCLP / window.__UF_HOY_CLP).toString();
            // Re-ejecutar inicialización con el precioUF disponible
            initSimulador(sim);
          }
        }, 100);
        setTimeout(() => clearInterval(checkUF), 10000);
        return;
      }
    }

    // Si no tenemos ningún precio válido, ocultamos el simulador
    if (!Number.isFinite(precioUF) || precioUF <= 0) {
      sim.querySelector("[data-sim-sin-precio]")?.classList.remove("d-none");
      sim.querySelector("[data-sim-body]")?.classList.add("d-none");
      return;
    }

    // Asegurarse de mostrar el simulador si estaba oculto
    sim.querySelector("[data-sim-sin-precio]")?.classList.add("d-none");
    sim.querySelector("[data-sim-body]")?.classList.remove("d-none");

    // Mostrar precio en la cabecera del widget
    setText(sim, "[data-res-precio-uf]", fmtUF(precioUF));

    // Actualizar dinámicamente el enlace a la página completa del simulador si existe
    const fullSimLink = sim.querySelector(".sim-cta-link");
    if (fullSimLink) {
      const baseUrl = fullSimLink.getAttribute("href").split("?")[0];
      fullSimLink.setAttribute("href", `${baseUrl}?precio_uf=${Math.round(precioUF)}`);
    }

    // Aplicar defaults
    const pieInput   = sim.querySelector("[data-sim-pie]");
    const plazoInput = sim.querySelector("[data-sim-plazo]");
    const tasaInput  = sim.querySelector("[data-sim-tasa]");

    if (pieInput)   pieInput.value   = DEFAULTS.pie_pct;
    if (plazoInput) plazoInput.value = DEFAULTS.plazo_anos;
    if (tasaInput)  tasaInput.value  = DEFAULTS.tasa_anual;

    // Primera renderización
    calcular(sim);

    // Escuchar cambios
    [pieInput, plazoInput, tasaInput].forEach((input) => {
      if (!input) return;
      input.addEventListener("input", () => calcular(sim));
    });

    // Si la UF aún no se cargó, re-calcular cuando llegue
    const observer = setInterval(() => {
      if (Number.isFinite(window.__UF_HOY_CLP)) {
        calcular(sim);
        clearInterval(observer);
      }
    }, 400);
    setTimeout(() => clearInterval(observer), 10000);
  }

  /* =====================================================
     BOOTSTRAP — esperar DOM
  ===================================================== */
  function boot() {
    document.querySelectorAll(".kcm-simulador").forEach(initSimulador);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
