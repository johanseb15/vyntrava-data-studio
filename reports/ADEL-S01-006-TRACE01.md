# ADEL-S01-006-TRACE01 — corrección mínima de trazabilidad

**Fecha:** 2026-10-27. **Alcance:** enlace entre el registro histórico [STAB01](ADEL-S01-006-STAB01.md) y la corrección posterior [DELIM01-FIX01](ADEL-S01-006-DELIM01-FIX01.md). No se modifica código ni se atribuyen ejecuciones nuevas.

El test de dos interpretaciones rectangulares citado en STAB01 como `test_rejects_two_rectangular_multicolumn_interpretations` figura ahora en `tests/test_importer.py` como `test_ambiguous_delimiter_requires_explicit_confirmation`. La política CSV que STAB01 dejó pendiente se contrastó con SPEC.md §5 y se corrigió en DELIM01-FIX01: el importador devuelve `delimiter_ambiguous` cuando ambas lecturas de varias columnas son plausibles y exige confirmación explícita. Ese informe registra su propio RED y una suite de **132 aprobadas, 2 omitidas**; no sustituye ni reetiqueta los resultados históricos de STAB01 (**123 aprobadas, 2 omitidas**) o el resultado CLOSE01 comunicado por el operador (**131 aprobadas, 2 omitidas**, sin nueva verificación en STAB01).

La revisión independiente y aceptación de PLAN.md §01.6 continúan pendientes. TRACE01 no acredita el cierre de Sprint 01.
