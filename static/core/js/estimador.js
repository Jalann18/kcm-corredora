/**
 * estimador.js — Lógica para el Wizard del Tasador Virtual de Propiedades
 */
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("estimadorForm");
    if (!form) return;

    let currentStep = 1;
    const totalSteps = 4;

    // Elementos UI
    const panes = document.querySelectorAll(".wizard-pane");
    const stepItems = document.querySelectorAll(".step-item");
    const nextButtons = document.querySelectorAll(".btn-next");
    const prevButtons = document.querySelectorAll(".btn-prev");
    
    // Toggle terreno basado en tipo de propiedad
    const propRadios = document.querySelectorAll('input[name="tipo_propiedad"]');
    const terrenoWrapper = document.getElementById("terreno-wrapper");
    
    propRadios.forEach(radio => {
        radio.addEventListener("change", (e) => {
            if (e.target.value === 'casa') {
                terrenoWrapper.style.display = 'block';
            } else {
                terrenoWrapper.style.display = 'none';
                document.querySelector('input[name="sup_terreno"]').value = '';
            }
        });
    });

    // Contadores (+ / -)
    const btnMinus = document.querySelectorAll(".btn-minus");
    const btnPlus = document.querySelectorAll(".btn-plus");
    
    btnMinus.forEach(btn => {
        btn.addEventListener("click", () => {
            const input = btn.nextElementSibling;
            let val = parseInt(input.value) || 0;
            if (val > 0) input.value = val - 1;
        });
    });
    
    btnPlus.forEach(btn => {
        btn.addEventListener("click", () => {
            const input = btn.previousElementSibling;
            let val = parseInt(input.value) || 0;
            if (val < 10) input.value = val + 1;
        });
    });

    // Navegación de pasos
    function showStep(stepNumber) {
        // Validar antes de avanzar (solo si avanza)
        if (stepNumber > currentStep) {
            if (!validateStep(currentStep)) return;
        }

        panes.forEach(pane => pane.classList.remove("active"));
        document.getElementById(`step-${stepNumber}`).classList.add("active");
        
        stepItems.forEach((item, index) => {
            const num = index + 1;
            item.classList.remove("active");
            if (num === stepNumber) {
                item.classList.add("active");
            } else if (num < stepNumber) {
                item.classList.add("completed");
            } else {
                item.classList.remove("completed");
            }
        });
        
        currentStep = stepNumber;
    }

    function validateStep(step) {
        let valid = true;
        const currentPane = document.getElementById(`step-${step}`);
        const requiredInputs = currentPane.querySelectorAll("[required]");
        
        requiredInputs.forEach(input => {
            if (!input.value.trim()) {
                input.classList.add("is-invalid");
                valid = false;
            } else {
                input.classList.remove("is-invalid");
            }
        });
        
        return valid;
    }

    // Remover estado invalido al escribir
    document.querySelectorAll(".form-control, .form-select").forEach(input => {
        input.addEventListener("input", () => {
            input.classList.remove("is-invalid");
        });
    });

    nextButtons.forEach(btn => {
        btn.addEventListener("click", () => showStep(currentStep + 1));
    });

    prevButtons.forEach(btn => {
        btn.addEventListener("click", () => showStep(currentStep - 1));
    });

    // Envio del formulario final para calcular
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        if (!validateStep(3)) return;

        // Avanzar al paso 4 (Loading)
        showStep(4);
        
        document.getElementById("loading-tasacion").style.display = "block";
        document.getElementById("resultado-tasacion").style.display = "none";

        // Preparar JSON
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // Llama a la API de Django
        try {
            const token = document.querySelector('[name=csrfmiddlewaretoken]').value;
            const res = await fetch("/api/tasacion/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": token
                },
                body: JSON.stringify(data)
            });

            if (!res.ok) throw new Error("Error en la tasación");

            const result = await res.json();
            
            // Mostrar resultados
            setTimeout(() => {
                mostrarResultados(result.precio_min_uf, result.precio_max_uf);
            }, 1500); // Pequeño delay para UX de "analizando..."

        } catch (error) {
            console.error(error);
            alert("Ocurrió un error al calcular la tasación. Por favor intenta de nuevo.");
            showStep(3); // Volver
        }
    });

    function formatNumber(n) {
        return new Intl.NumberFormat("es-CL").format(Math.round(n));
    }

    function mostrarResultados(minUF, maxUF) {
        document.getElementById("loading-tasacion").style.display = "none";
        document.getElementById("resultado-tasacion").style.display = "block";
        
        // Animacion contador para UF
        animateValue("res-min-uf", 0, minUF, 1000);
        animateValue("res-max-uf", 0, maxUF, 1500);
        
        // Si la UF de hoy esta disponible (viene de base.html)
        if (window.__UF_HOY_CLP && window.__UF_HOY_CLP > 0) {
            const minCLP = minUF * window.__UF_HOY_CLP;
            const maxCLP = maxUF * window.__UF_HOY_CLP;
            document.getElementById("res-min-clp").innerText = '$' + formatNumber(minCLP);
            document.getElementById("res-max-clp").innerText = '$' + formatNumber(maxCLP);
        } else {
            document.getElementById("res-min-clp").parentElement.style.display = "none";
        }
    }

    // Efecto visual de números corriendo
    function animateValue(id, start, end, duration) {
        const obj = document.getElementById(id);
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = formatNumber(Math.floor(progress * (end - start) + start));
            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                obj.innerHTML = formatNumber(end); // Asegurar el numero final
            }
        };
        window.requestAnimationFrame(step);
    }
});
