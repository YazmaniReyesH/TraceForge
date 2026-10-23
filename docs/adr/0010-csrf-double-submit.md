# ADR-0010: Protección CSRF con double-submit token

- **Estado:** aceptado
- **Fecha:** 2026-10-23

## Contexto

La sesión viaja en una **cookie httpOnly** (ADR-0007): el navegador la envía automáticamente en
toda petición al backend, incluidas las que origina un sitio atacante → riesgo **CSRF** en las
mutaciones. En F0-T4b quedó como deuda (mitigada solo por `SameSite=Lax` y la regla "GET nunca
muta"). F0-T5a lo cierra.

Alternativas: (a) **double-submit token** (cookie legible + header que la repite); (b) token
sincronizado en servidor (requiere estado por sesión); (c) depender solo de `SameSite=Strict`
(rompe navegaciones legítimas y no protege same-site). Se elige (a): sin estado en servidor y
estándar para SPAs.

## Decisión

**Patrón double-submit token:**

- Al iniciar sesión (y al hidratar con `GET /auth/me`, y vía `GET /auth/csrf`) el backend emite
  una cookie **legible por JS** `tf_csrf` (no httpOnly, `SameSite=Lax`, `Secure` en prod).
- El frontend lee `tf_csrf` y la repite en el header **`X-CSRF-Token`** en **toda mutación**
  (POST/PATCH/DELETE). Un atacante cross-site no puede leer la cookie (same-origin policy), así
  que no puede construir el header → la mutación falla.
- La dependencia `require_csrf` (`app/core/csrf.py`) valida que header == cookie (comparación en
  tiempo constante) y se aplica **a nivel de router** en los recursos que mutan.
  - Los **métodos seguros** (GET/HEAD/OPTIONS) **nunca** se validan (y nunca mutan).
  - Si **no hay cookie de sesión**, no hay nada que un CSRF pueda reenviar: se deja pasar para que
    la autenticación responda 401 (en vez de un 403 CSRF confuso). Con sesión presente —el caso
    explotable— la validación es obligatoria.
- **Exentos:** `login` y `register` (flujo de arranque, pre-sesión). `logout` **sí** exige CSRF.
- Fallo de CSRF → envelope `{code: "csrf_failed"}` con **403** (ADR-0009).

**Dev same-origin:** en desarrollo, Vite hace **proxy** de `/api` (y `/health`) al backend, así
el navegador ve todo bajo `http://localhost:5173`: las cookies `SameSite=Lax` (sesión + CSRF)
viajan sin CORS. En producción se sirve el frontend same-origin.

## Consecuencias

**A favor:** CSRF cubierto sin estado en servidor; el frontend solo repite una cookie en un
header; GET siempre a salvo; mensajes claros (`csrf_failed`).

**En contra / costos:** el frontend debe enviar el header en cada mutación (centralizado en el
cliente HTTP `src/shared/api`); la cookie CSRF caduca con la sesión y se renueva en `/me` y
`/login` (o `GET /auth/csrf`). La defensa asume same-origin o un proxy/misma raíz; un despliegue
cross-site exigiría revisitar `SameSite`/CORS. `[[POR LLENAR: endurecer SameSite=Strict si el
despliegue lo permite]]`.
