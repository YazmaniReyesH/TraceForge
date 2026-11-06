# ADR-0016: Cifrado del mapeo de redacción (rehidratación futura)

- **Estado:** aceptado
- **Fecha:** 2026-11-06

## Contexto

F1-T4a es la primera función de IA de **producto**: a partir de la evidencia **real** de una sesión,
la IA genera una sugerencia (descripción / siguiente paso). Por primera vez fluye evidencia real
hacia el proveedor, así que la **redacción** (ADR-0005) deja de ser un ejercicio sintético: produce
un **mapeo `marcador→valor real`** con secretos verdaderos (contraseñas, claves, tokens).

El ADR-0005 ya decidió *que* ese mapeo se guarda **cifrado** para poder **rehidratar** los valores a
un usuario autorizado más adelante (p. ej. al exportar un reporte final), y que los valores reales
**nunca** vuelven al modelo ni entran en la narrativa. Aquí se concretan las decisiones con
alternativas reales:

1. **Con qué se cifra** y **qué se cifra**.
2. **Dónde** se guarda el mapeo cifrado (tabla vs columna).
3. **Qué pasa si no hay clave** de cifrado configurada.

(La tanda también crea la entidad de **sugerencia** con procedencia y máquina de estados —ADR-0003—,
y conecta el andamiaje de F1-T3; eso sigue esos ADRs y no requiere decisión nueva. Esta decisión se
centra en el **almacén cifrado**.)

## Decisión

### 1. Librería y qué se cifra

Se cifra con **Fernet** (de la librería `cryptography`): cifrado **simétrico autenticado**
(AES-128-CBC + HMAC-SHA256) con un formato de token versionado, estándar y probado. Se eligió sobre
un esquema propio porque trae **integridad/anti-manipulación** de serie, es simple y es difícil de
usar mal. Se descartó diseñar un esquema a mano (riesgo de errores criptográficos) y usar cifrado
asimétrico (innecesario: el mismo servicio cifra y —en el futuro— descifra).

**Qué se cifra:** el JSON del mapa `{marcador: valor_real}` completo (UTF-8), que produce un **token**
(texto urlsafe base64). **Qué no:** nunca el valor crudo suelto; el token es lo único que se persiste.
La **clave** vive solo en el entorno (`TF_ENCRYPTION_KEY`), **jamás** en el repo ni en la base; se
genera con `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

### 2. Dónde: tabla propia `ai_redaction_maps`

El mapeo cifrado vive en una **tabla aparte** (`ai_redaction_maps`), no en una columna de la
sugerencia. Razones: es material de **otro nivel de seguridad** (secretos cifrados) con su propio
control de acceso y **retención/purga** futuros; es **append-only** y 1:1 con una generación; y
mantiene la fila de la sugerencia limpia de blobs cifrados. Guarda: `ciphertext`, `scheme` (`fernet`,
para rotación futura), `marker_count` (métrica, sin valores), aislamiento (`workspace_id`/
`project_id`/`session_id`) y el enlace a la sugerencia (`ai_suggestion_id`, CASCADE). Alternativa
descartada: una columna `ciphertext` en `ai_suggestions` (mezcla niveles de sensibilidad y complica
una purga selectiva del material cifrado).

### 3. Sin clave configurada: degradación segura (no persistir)

Si `TF_ENCRYPTION_KEY` **no está** (o es inválida), el cifrador queda *no configurado* y **no se
persiste el mapeo** (jamás se escribe en claro). La generación **sigue funcionando**: la redacción ya
protegió lo que cruzó el perímetro; lo único que se pierde es la capacidad de **rehidratar** esa
sugerencia en el futuro. La sugerencia se marca con `redaction_map_stored=false` (y conserva su
`redaction_count`) para que la UI lo advierta. Se eligió esto sobre **rechazar la generación** (sería
excesivo: la redacción no depende de la clave) y sobre **guardar en claro** (inaceptable, viola
ADR-0005).

### 4. Enlace con la bitácora y la procedencia

La sugerencia enlaza la **llamada que la originó** (`ai_call_log_id`, F1-T3) y las **entradas usadas**
(`input_refs`: ids+versión de la evidencia, ya redactada). El **prompt redactado** que cruzó el
perímetro sigue viviendo en `ai_call_log` (ADR-0015); el **mapeo cifrado** vive en
`ai_redaction_maps`; la **sugerencia** guarda el contenido propuesto/editado y la procedencia. Así
cada pieza queda en su lugar sin reintroducir secretos: la bitácora nunca ve el valor crudo, y el
único lugar con valores (cifrados) es `ai_redaction_maps`.

## Consecuencias

**A favor:** rehidratación futura posible sin reenviar secretos al modelo; cifrado estándar y
autenticado; separación limpia de niveles de sensibilidad (narrativa / auditoría redactada / material
cifrado); degradación segura sin clave (nunca se escribe en claro).

**En contra / costos:** una dependencia más (`cryptography`); una clave de entorno que **hay que
gestionar y respaldar** (perderla = no poder rehidratar); el material cifrado crece con cada
generación con secretos; la **rehidratación efectiva** (descifrar y mostrar a un usuario autorizado)
aún no existe (solo se persiste). La redacción determinista sigue sin ser perfecta (ADR-0005/0015).

`[[POR LLENAR: rotación/rencifrado de la clave (p. ej. MultiFernet con varias claves) y
retención/purga del mapeo cifrado; UI/endpoint de rehidratación para usuarios autorizados.]]`

## Alcance

Backend de F1-T4a. Crea `ai_suggestions` y `ai_redaction_maps` (migración `f3a1c9d7b2e4`, la aplica el
equipo). No hay UI ni el violeta de IA (F1-T4b), ni rehidratación efectiva, ni OpenAI/Gemini, ni
validación contra catálogos (CWE/CVE/ATT&CK, F2). La lectura de `ai_policy` para elegir modelo queda
como base de la futura selección desde UI.
