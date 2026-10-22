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
- El catálogo exacto de patrones y su configuración por clasificación se detallará al construir
  la capa de redacción. `[[POR LLENAR: catálogo de patrones de redacción y niveles de
  clasificación — definir con la implementación de la redacción en F1]]`.

## Limitación conocida

- **No existe un modo totalmente aislado (sin nube)** mientras no se retomen los modelos locales.
  Hoy la protección se basa en redacción + política por proyecto + API bajo contrato, no en
  evitar la nube por completo. Ver ADR-0005.

## Estado

Resumen fundacional (F0-T3a). La **capa de redacción** y el **gateway `AIProvider`** se
construyen en **F1**; los campos de clasificación/política viven en la entidad `projects`
(**F0-T3b**).
