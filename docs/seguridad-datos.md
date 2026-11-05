# Seguridad de datos y redacción — TraceForge

Documento vivo que resume **qué protege TraceForge y cómo** cuando datos del proyecto cruzan el
perímetro hacia un proveedor de IA en la nube. La **decisión fundacional** que lo gobierna es el
[ADR-0005: Política de datos y redacción](./adr/0005-politica-de-datos-y-redaccion.md); aquí se
mantiene el resumen operativo y se irá ampliando a medida que se implementen la capa de redacción
y el gateway de IA (F1+).

## Principios (resumen)

- **Nube permitida con redacción activada por defecto.** Antes de cualquier llamada a un
  proveedor en la nube, una **capa de redacción determinista** reemplaza secretos por marcadores
  estables. Ver ADR-0005.
- **Los valores reales nunca entran en la narrativa.** Viven en la evidencia cruda; el mapeo
  marcador→valor real se guarda **cifrado**.
- **Política por proyecto.** Clasificación del proyecto, proveedores permitidos, si se envían
  imágenes y redacción on/off (override) se configuran por proyecto, dentro de lo que permita el
  workspace (ver ADR-0002).
- **Auditoría de cada llamada de IA**: proveedor, modelo y **qué se envió ya redactado**.
- **Siempre API bajo contrato**, nunca suscripciones de consumo, para datos de clientes.

## Qué se redacta (según clasificación)

- Siempre: contraseñas, hashes, claves privadas, tokens, API keys.
- Según clasificación/política del proyecto: PII e IPs y otros datos sensibles.
- **Implementado en F1-T3** (ver [`modulos/ia.md`](./modulos/ia.md) y ADR-0015): la capa de redacción
  determinista `app/ai/redaction.py` enmascara **siempre** claves privadas PEM, JWT, claves
  `sk-`/`pk-`/`rk-`, `AKIA…` (AWS), token tras `Bearer`, asignaciones `api_key/secret/token/…=` y
  `password=`, y hashes hex (sha256/sha1/md5), con **marcadores estables** y **sin romper la
  estructura** (enmascara solo el valor, conserva la clave). **PII e IPs quedan fuera por defecto**
  (dependen de la política/clasificación del proyecto).
- El catálogo exacto de patrones y su configuración por clasificación se seguirá ampliando.
  `[[POR LLENAR: catálogo de patrones ampliado y redacción de PII/IPs por clasificación — con la
  política de IA por proyecto en F1-T4; persistencia cifrada del mapeo marcador→valor.]]`

## Gateway de IA, anti-inyección y auditoría (F1-T3)

- **Gateway `AIProvider`** (puerto/adaptador, Claude detrás): toda llamada a la nube pasa por él. Si
  no hay API key (`TF_ANTHROPIC_API_KEY`), degrada con claridad ("IA no configurada"), no rompe.
- **Antes de salir**: el contenido pasa por **redacción** y se **ensambla como dato no confiable** —
  la evidencia se envuelve en una frontera única con nonce y el sistema instruye al modelo a tratarla
  como datos, nunca como instrucciones (defensa contra inyección de prompt del objetivo).
- **Auditoría**: cada llamada se registra en la tabla `ai_call_log` con el prompt **ya redactado** (+
  su SHA-256), el conteo de redacciones, proveedor, modelo, estado, tokens y workspace/project.
  **Nunca** se guarda el contenido crudo, el mapeo marcador→valor ni la API key (ADR-0015).

## Limitación conocida

- **No existe un modo totalmente aislado (sin nube)** mientras no se retomen los modelos locales.
  Hoy la protección se basa en redacción + política por proyecto + API bajo contrato, no en
  evitar la nube por completo. Ver ADR-0005.

## Estado

Resumen fundacional (F0-T3a), ampliado en **F1-T3**: la **capa de redacción**, el **gateway
`AIProvider`** (Claude), el **ensamblado anti-inyección** y la **bitácora de llamadas** ya están
implementados (andamiaje; sin función de producto aún — F1-T4). Los campos de clasificación/política
viven en la entidad `projects` (`ai_policy`, aún reservada). Pendiente: redacción de PII/IPs por
clasificación, persistencia cifrada del mapeo marcador→valor y retención/purga de la bitácora.
