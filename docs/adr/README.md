# ADRs — Architecture Decision Records

Este directorio guarda las **decisiones de arquitectura** de TraceForge, una por
archivo, en orden consecutivo: `0001-titulo-corto.md`, `0002-...`, etc.

Un ADR registra el *porqué* de una decisión para que el equipo (y quien llegue
después) no tenga que reconstruirlo desde el código.

> Nota: la skill `documentacion-proyecto` también menciona `docs/arquitectura.md`
> como lugar para ADRs. Convención de este repo: los ADRs **individuales** viven
> aquí, en `docs/adr/`, y `docs/arquitectura.md` (cuando exista) sirve de índice y
> visión general que enlaza a cada ADR. Un ADR = un archivo aquí.

## Formato: contexto → decisión → consecuencias

Cada ADR sigue esta estructura mínima:

```markdown
# ADR-NNNN: Título corto de la decisión

- **Estado:** propuesto | aceptado | reemplazado por ADR-XXXX | obsoleto
- **Fecha:** AAAA-MM-DD

## Contexto
Qué problema o fuerza nos empuja a decidir. Restricciones, alternativas en juego,
lo que se sabía al momento. Sin solución todavía.

## Decisión
Qué se decide, en voz activa: "Usaremos ...". Clara e inequívoca.

## Consecuencias
Qué se vuelve más fácil y qué más difícil. Costos asumidos, deuda aceptada,
seguimientos que genera. Lo bueno y lo malo.
```

## Reglas

- Numeración consecutiva, sin reutilizar números.
- Un ADR no se borra ni se reescribe cuando cambia la realidad: se marca como
  *reemplazado* y se crea uno nuevo que lo supera.
- Toda decisión técnica con alternativas reales merece un ADR (ver skill
  `documentacion-proyecto`).
