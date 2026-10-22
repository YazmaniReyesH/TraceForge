# ADR-0002: Modelo multiusuario (multi-tenant) y control de acceso (RBAC)

- **Estado:** aceptado
- **Fecha:** 2026-10-21

## Contexto

TraceForge es multiusuario desde el inicio: varios equipos y clientes externos (auditores,
contrapartes) conviven en la misma instancia, trabajando sobre documentación sensible de TI
y ciberseguridad (pentests, hallazgos, evidencia). Necesitamos un modelo de inquilinato y de
permisos que, desde la primera entidad, garantice dos cosas:

- **Aislamiento fuerte entre inquilinos**: un usuario jamás debe ver ni tocar datos de un
  inquilino al que no pertenece.
- **Acceso granular dentro del inquilino**: no todos los miembros ven todos los proyectos, y
  un cliente externo solo debe ver lo que se le comparte, en lectura.

El modelo debe ser lo bastante simple para arrancar, pero lo bastante expresivo para cubrir
los casos reales (owner que administra, colaboradores por proyecto, cliente de solo lectura).
Las skills del proyecto (`backend-fastapi`, `revision-modulo`) ya fijan dos principios no
negociables: el RBAC se valida **siempre en el servidor** y el aislamiento se aplica en
**cada consulta**. Este ADR elige el modelo concreto; F0-T3b lo materializa en entidades y su
migración.

Alternativas consideradas:

- **Un solo nivel de roles (solo por workspace)**: insuficiente; no distingue quién colabora
  en qué proyecto ni permite clientes de solo lectura acotados a un proyecto.
- **Roles totalmente libres / ACL por recurso desde el día uno**: demasiada complejidad para
  esta fase; difícil de auditar y de razonar. Se prefiere RBAC con dos niveles y, si hiciera
  falta más adelante, permisos por campo/recurso puntuales sobre esa base.
- **Multi-tenant por base de datos o por esquema (tenant = DB/schema)**: operación y
  migraciones más costosas; se prefiere **tenancy lógico** (discriminador por `workspace`)
  con aislamiento forzado en la capa de datos (ver ADR-0001).

## Decisión

Adoptamos un modelo **multi-tenant lógico con dos niveles de roles** (workspace y proyecto).

### Entidades conceptuales

- **users**: identidad de la persona (se autentica; su rol y su inquilino se resuelven del
  token, nunca del request).
- **workspaces**: el **inquilino**. Unidad de aislamiento y de facturación futura. Es hoy el
  **tope de la jerarquía** (ver consideración diferida).
- **projects**: unidad de trabajo dentro de un workspace (un pentest, una auditoría, un BCP,
  etc.). Lleva su clasificación y su política de IA (ver ADR-0005).
- **membresía de workspace**: vincula un `user` a un `workspace` con un **rol de workspace**.
- **membresía de proyecto**: vincula un `user` a un `project` con un **rol de proyecto**.

### Roles de workspace

- **owner**: control total del workspace. Facturación (futura), eliminar el workspace y
  transferir la propiedad. Acceso implícito a todos los proyectos.
- **admin**: gestiona miembros, proyectos, configuración y la política de IA del workspace.
  Acceso implícito a todos los proyectos. **No** puede eliminar el workspace ni tocar
  facturación ni transferir la propiedad.
- **member**: colaborador. **No** tiene visión global de los proyectos; su acceso a datos
  proviene **únicamente** de sus membresías de proyecto.
- **guest**: externo. Sin visión general del workspace; solo ve los **proyectos que se le
  comparten explícitamente**, y en **lectura**.

### Roles de proyecto

- **lead**: gestiona la membresía del proyecto; edita todo su contenido; define la
  clasificación y la política de IA del proyecto **dentro de lo que permita el workspace**.
- **contributor**: captura y edita evidencia, hallazgos y documentos; **no** gestiona
  miembros.
- **viewer**: solo lectura. Rol típico del cliente externo o del auditor interno.

### Regla de acceso

- **owner** y **admin** acceden a **todos** los proyectos de su workspace (acceso implícito).
- **member** y **guest** acceden **solo** a los proyectos donde tienen **membresía de
  proyecto explícita**.
- El **rol efectivo** de un usuario sobre un proyecto resulta de combinar su rol de workspace
  (acceso implícito de owner/admin) con su rol de proyecto cuando exista. Las reglas exactas de
  combinación están fijadas en la sección **"Rol efectivo e invariantes"** más abajo y se
  configuran en la matriz de permisos central.

### Aislamiento y aplicación

- **Toda** consulta de datos se filtra por el **workspace** del usuario autenticado; los datos
  de un proyecto se gobiernan **además** por la membresía de proyecto.
- El RBAC se valida **siempre en el servidor**: el rol y el workspace se resuelven del **token**
  de sesión, nunca de parámetros del cliente.
- La **matriz de permisos** (rol × acción/módulo) vive como **configuración central** en
  `app/core/security.py`, no como condicionales dispersos por el código. Los endpoints nacen
  con su dependencia de permiso (ver skill `backend-fastapi`).

### Rol efectivo e invariantes

Reglas resueltas que gobiernan la combinación de roles y la integridad del modelo. Son
**invariantes de dominio**: el backend las valida y las impone siempre; no son solo decisiones
de UI. F0-T3b debe materializarlas (constraints y/o validación en el servicio) y cubrirlas con
pruebas.

1. **Combinación de roles (el implícito es un piso).** Para **owner/admin**, el acceso implícito
   a todos los proyectos es un **piso**: una membresía de proyecto solo puede **sumar**
   capacidades, **nunca restar**. Es decir, agregar a un admin como `viewer` de un proyecto **no**
   reduce su acceso. Para **member/guest**, el rol de proyecto es su **único** acceso a ese
   proyecto (sin membresía explícita, no hay acceso).

2. **`guest` es viewer y nada más.** Un `guest` solo puede tener rol de proyecto **`viewer`**. La
   combinación `guest` + (`contributor` | `lead`) es **inválida** y el backend la **rechaza como
   regla dura** (invariante), no solo la oculta en la UI. Si un externo debe **aportar
   contenido**, se le promueve a **`member`** del workspace (y se le da el rol de proyecto que
   corresponda).

3. **Owner único y transferencia atómica.** Hay **exactamente un `owner`** por workspace.
   **"Transferir propiedad"** es una operación **atómica**: en la misma transacción el nuevo
   owner **sube** a `owner` y el anterior **baja** a `admin`. Nunca puede haber cero ni dos
   owners.

4. **Identidad global y multi-pertenencia.** La identidad del `user` es **global a la instancia**.
   Un mismo usuario puede pertenecer a **varios workspaces** con un **rol distinto en cada uno**.
   El **rol y el workspace activo** se resuelven **siempre del token**, nunca del cliente.

5. **Techo de política de IA (jerárquico).** El **techo** de política de IA lo fijan
   **owner/admin** a nivel **workspace**. El `lead` de un proyecto solo puede **igualar o
   restringir** ese techo en su proyecto, **nunca relajarlo**. En F0-T3b, la entidad
   **`workspaces`** reservará el campo de **política-techo** (su aplicación efectiva es de F1) y
   la entidad **`projects`** llevará su **política por proyecto** (ver ADR-0005).

## Consecuencias

**A favor:**

- Aislamiento claro y auditable: un discriminador por workspace en cada tabla de datos y un
  único punto (repository) que lo aplica.
- Expresividad suficiente para los casos reales (administración, colaboración por proyecto,
  cliente de solo lectura) sin la complejidad de ACLs por recurso.
- La matriz central facilita revisar y evolucionar permisos, y probarlos de forma aislada.

**En contra / costos asumidos:**

- Dos niveles de membresía implican resolver el **rol efectivo** por proyecto en cada petición
  (combinar workspace + proyecto) según las reglas de la sección "Rol efectivo e invariantes", y
  cubrirlas con pruebas (incluidos los casos límite: implícito como piso, `guest`=viewer,
  transferencia de owner).
- El tenancy lógico exige disciplina: **ninguna** consulta puede saltarse el filtro por
  workspace. Se mitiga centralizando el acceso en el repository y revisándolo en
  `revision-modulo`.

**Consideración diferida (importante):**

- El **workspace es hoy el tope de la jerarquía**. Una eventual capa de **"organización"** por
  encima de los workspaces (p. ej. para agrupar workspaces de una misma empresa, facturación
  consolidada o SSO corporativo) será una **decisión futura separada**, con su propio ADR. No
  se diseña ahora para no hipotecar el modelo base.

**Materialización:**

- **F0-T3b** materializa estas entidades (users, workspaces, projects, membresías de workspace
  y de proyecto) y su **primera migración**, definiendo ahí los nombres exactos de tablas,
  columnas, enums de rol y CHECK constraints. Debe además **imponer los invariantes** de la
  sección "Rol efectivo e invariantes" (owner único, `guest`=viewer, identidad global +
  multi-pertenencia) y **reservar el campo de política-techo** en `workspaces` y el de política
  por proyecto en `projects`. Este ADR no fija SQL ni nombres de columnas.
