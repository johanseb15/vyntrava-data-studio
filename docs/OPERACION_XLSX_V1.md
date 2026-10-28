# Importación XLSX: precisión numérica

En recetas `1.1.0`, una entrada `.xlsx` indica una hoja visible mediante `hoja`. El importador convierte cada celda a la tabla textual usada por el flujo de validación, análisis y entrega. El valor numérico almacenado determina la importación; el formato visual de Excel no modifica ese valor.

Las celdas numéricas admiten **como máximo 15 dígitos significativos** en el valor que recibe el importador. El signo, el punto decimal, el exponente de la notación científica y los ceros de escala no cuentan como dígitos significativos. Por ejemplo, `0.10`, `12.345` y `1234567890123.45` son admisibles como valores numéricos. `1E+20` también lo es: su exponente no añade dígitos significativos. Si el valor numérico supera el límite, se rechaza la importación con `XlsxError`: `code="numeric_precision"`, `sheet`, `row` y `column`. El mensaje no contiene el valor de la celda.

Para conservar más de 15 dígitos significativos, guardar el dato como **texto** en el libro antes de importarlo. El importador conserva ese texto sin redondear ni reconstruir cifras. No aplica redondeos correctivos a las celdas numéricas rechazadas.

Esta comprobación opera sobre el valor disponible al leer el archivo. **No puede detectar toda pérdida de precisión ocurrida en Excel antes de la importación**: si Excel ya cambió un número y el valor resultante tiene 15 dígitos significativos o menos, el importador no puede recuperar ni identificar con certeza los dígitos originales. Para identificadores e importes de alta precisión, usar texto desde la captura del dato.

Un rechazo ocurre antes de publicar salidas o manifiesto del encargo. El archivo original permanece sin modificar. La corrección requiere preparar un nuevo original y volver a ejecutar la receta con las aprobaciones HMAC correspondientes a sus hashes.
