# ADR-0007: Autenticación local — ubicación de credenciales, hashing y transporte de token

- **Estado:** aceptado
- **Fecha:** 2026-10-21

## Contexto

F0-T4a necesita que un usuario pueda registrarse e iniciar sesión, y dejar un contexto de
sesión del que F0-T4b resuelva el usuario autenticado. La decisión marco (opción C) ya estaba
tomada: **autenticación propia con email + contraseña detrás de un puerto `AuthProvider`** para
poder sumar SSO en el futuro sin reescribir. Dentro de eso quedan varias decisiones con
alternativas reales que conviene registrar: **dónde viven las credenciales**, **con qué
algoritmo se hashea la contraseña** y **cómo viaja el token** en una SPA React.

TraceForge maneja datos sensibles (ADR-0005) y es multiusuario (ADR-0002); la identidad es
global a la instancia (F0-T3b).

## Decisión

### 1. Ubicación de credenciales → tabla aparte `user_credentials`

Las credenciales viven en una tabla **separada** de `users` (no como columnas en `users`),
con **una credencial de contraseña por usuario** (`UNIQUE user_id`) y `ON DELETE CASCADE`.

*Por qué:* aísla el secreto (`password_hash`) de la identidad y deja espacio para **otros
métodos de login** (SSO/OIDC) como filas/tablas propias detrás del `AuthProvider`, sin
reescribir `users`. (Ante duda, la convención del proyecto ya pedía "tabla aparte".)

### 2. Hashing → argon2id (argon2-cffi)

Las contraseñas se hashean con **argon2id**, con **factor de costo configurable** vía settings
(`TF_ARGON2_TIME_COST`, `TF_ARGON2_MEMORY_COST`, `TF_ARGON2_PARALLELISM`).

*Por qué:* es la primera recomendación de OWASP (memory-hard, resistente a GPU) y evita el
límite de 72 bytes de bcrypt. Nunca se guarda la contraseña en claro ni se registra en logs.

### 3. Transporte del token → cookie httpOnly (para la SPA)

El JWT (HS256, secreto y caducidad desde settings) viaja en una **cookie httpOnly**,
`Secure` (en prod), `SameSite=Lax`, emitida en `/login` y borrada en `/logout`.

*Por qué, para una SPA React:* una cookie **httpOnly** no es accesible desde JavaScript, lo que
**mitiga el robo de token por XSS** (el mayor riesgo de guardar el token en `localStorage`).
`SameSite=Lax` da una defensa razonable de CSRF para una SPA servida en el mismo sitio. Como
conveniencia para clientes de API y pruebas, `get_current_user` **también** acepta
`Authorization: Bearer`, pero el mecanismo de la SPA es la cookie.

### 4. Contexto de sesión

Una dependencia `get_current_user` resuelve el usuario autenticado desde el token (cookie o
Bearer) y responde **401** si falta o es inválido. **No** resuelve workspace activo ni rol
(eso es F0-T4b).

### 5. Anti-enumeración de usuarios

`/login` responde **401 con un mensaje genérico** ("Credenciales inválidas") tanto si el email
no existe como si la contraseña es incorrecta, y hace una **verificación señuelo** de hash
cuando el usuario no existe para igualar los tiempos. El email se **normaliza** (minúsculas +
trim) en el servicio antes de registrar/buscar.

## Consecuencias

**A favor:**

- Secreto aislado, extensible a SSO sin tocar `users`; argon2id fuerte y parametrizable;
  cookie httpOnly reduce el impacto de XSS; mensajes de login sin fugas de existencia.

**En contra / costos asumidos:**

- **CSRF con cookies:** `SameSite=Lax` cubre el caso común, pero un endurecimiento con
  **token anti-CSRF (double-submit)** queda pendiente. `[[POR LLENAR: decidir estrategia CSRF
  (double-submit vs. SameSite=Strict) al construir el frontend]]`.
- **Logout con JWT stateless:** `/logout` borra la cookie, pero el token sigue siendo válido
  hasta expirar (no hay lista de revocación). Si se requiere revocación inmediata, habrá que
  añadir denylist/rotación. `[[POR LLENAR: revocación de tokens / refresh tokens si se necesita]]`.
- **Registro y enumeración — DEUDA DE SEGURIDAD CONOCIDA:** `POST /auth/register` responde
  **409** cuando el email ya existe. Tanto el **código de estado** (409 vs 201) como —desde
  F0-T5a— el **`code` específico `email_already_registered`** del envelope (ADR-0009) permiten
  **enumeración de usuarios** por registro: un atacante puede sondear qué emails están dados de
  alta. Ambos (status y code) forman parte de esta deuda y se asumen a conciencia por ahora (sin
  sistema de correo). Se **cerrará junto con la verificación por email**: el registro responderá
  siempre 200/202 "revisa tu correo" (sin distinguir en status ni en code si la cuenta ya existía)
  y, si existía, se notificará por email fuera de la respuesta HTTP.
  `[[POR LLENAR: flujo de verificación por email cuando exista envío de correo]]`.
- Argon2 añade una dependencia nativa (argon2-cffi) y coste de CPU/memoria por login (deseado).

## Alcance

Decisiones **implementadas en F0-T4a**. La autorización fina (RBAC, `requiere_permiso`,
workspace activo, rol efectivo) y los invariantes de servicio son **F0-T4b**.
