# CONCILIAR_PYTHON

Este proyecto incluye un script `conciliador.py` para conciliar movimientos bancarios con registros contables.

## Requisitos
- Python 3.10 o superior
- pdfplumber >= 0.10
- pandas >= 2.0
- openpyxl >= 3.1

Instala las dependencias con:

```bash
pip install pdfplumber pandas openpyxl
```

## Uso

Ejecuta el script proporcionando las rutas del PDF y del Excel. Por ejemplo:

```bash
python conciliador.py "~/Descargas/CORRIENTE 05-2025 CTA 9670.pdf" "~/Descargas/CTA CTE SOL DEL NORTE MAYO.xlsx"
```

El script generará los archivos `conciliacion_detalle.xlsx` y `conciliacion_resumen.csv` en el directorio actual e imprimirá un resumen en consola.
