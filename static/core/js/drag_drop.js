document.addEventListener('DOMContentLoaded', function() {
    // Buscar la tabla de imágenes
    let tbody = document.querySelector('#imagenes-group tbody');
    if (!tbody) return;

    // A cada fila le damos la capacidad de ser arrastrada
    let rows = tbody.querySelectorAll('tr.form-row.has_original, tr.form-row.dynamic-imagenes');
    
    rows.forEach(row => {
        // Ignoremos la fila de "Añadir otro" vacía si no es arrastrable lógicamente
        if (row.classList.contains('empty-form')) return;

        row.setAttribute('draggable', 'true');
        row.style.cursor = 'move';
        row.title = "Arrastra hacia arriba o abajo para reordenar";
        
        row.addEventListener('dragstart', function(e) {
            row.classList.add('dragging');
            row.style.opacity = '0.5';
            e.dataTransfer.effectAllowed = 'move';
        });
        
        row.addEventListener('dragend', function(e) {
            row.classList.remove('dragging');
            row.style.opacity = '1';
            
            // Cuando soltamos la fila, recalculamos todos los campos 'orden'
            let updatedRows = tbody.querySelectorAll('tr.form-row:not(.empty-form)');
            updatedRows.forEach((r, idx) => {
                let input = r.querySelector('input[name$="-orden"]');
                if (input) {
                    input.value = idx + 1;
                    // Opcional: animar brevemente para mostrar que cambió
                    input.style.backgroundColor = '#d4edda';
                    setTimeout(() => input.style.backgroundColor = '', 500);
                }
            });
        });
    });

    tbody.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        const afterElement = getDragAfterElement(tbody, e.clientY);
        const draggable = document.querySelector('.dragging');
        
        if (draggable) {
            if (afterElement == null) {
                tbody.appendChild(draggable);
            } else {
                tbody.insertBefore(draggable, afterElement);
            }
        }
    });

    function getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('tr.form-row:not(.dragging):not(.empty-form)')];
        
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            // El medio de la fila
            const offset = y - box.top - box.height / 2;
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }
});
