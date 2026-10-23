// Catálogo de traducción es-MX. NINGÚN texto visible va hardcodeado en componentes:
// todo pasa por estas claves. Estructura lista para sumar idiomas sin tocar componentes.

export const esMX = {
  app: {
    name: "TraceForge",
    tagline: "Documentación técnica para TI / Ciberseguridad",
  },
  common: {
    loading: "Cargando…",
    error: "Ocurrió un error",
    retry: "Reintentar",
    email: "Correo electrónico",
    password: "Contraseña",
    displayName: "Nombre para mostrar",
    optional: "opcional",
  },
  theme: {
    toLight: "Cambiar a tema claro",
    toDark: "Cambiar a tema oscuro",
  },
  nav: {
    account: "Cuenta",
    logout: "Cerrar sesión",
  },
  auth: {
    loginTitle: "Iniciar sesión",
    loginSubmit: "Entrar",
    loginLoading: "Entrando…",
    registerTitle: "Crear cuenta",
    registerSubmit: "Registrarme",
    registerLoading: "Creando…",
    toRegister: "¿No tienes cuenta? Regístrate",
    toLogin: "¿Ya tienes cuenta? Inicia sesión",
    passwordHint: "Mínimo 8 caracteres",
  },
  home: {
    title: "Inicio",
    welcome: "Hola, {{name}}",
    sessionOk: "Tu sesión está activa.",
    placeholder: "Las pantallas de workspaces y proyectos llegan en la siguiente tanda.",
  },
  errors: {
    // Mapeo por `code` del envelope del backend (ADR-0009).
    invalid_credentials: "Correo o contraseña incorrectos",
    email_already_registered: "Ese correo ya está registrado",
    validation_error: "Revisa los datos del formulario",
    unauthenticated: "Tu sesión expiró. Inicia sesión de nuevo",
    forbidden: "No tienes permiso para esta acción",
    not_found: "No encontrado",
    csrf_failed: "Tu sesión expiró. Recarga e inténtalo de nuevo",
    conflict: "No se pudo completar la operación",
    sole_owner: "No puedes degradar ni quitar al único owner; transfiere la propiedad",
    guest_must_be_viewer: "Un invitado solo puede ser viewer del proyecto",
    member_exists: "El usuario ya es miembro",
    not_a_member: "El usuario no es miembro",
    not_workspace_member: "El usuario no es miembro del workspace",
    cannot_assign_owner: "El rol owner se asigna transfiriendo la propiedad",
    already_owner: "Ese usuario ya es el owner",
    user_has_memberships: "El usuario tiene membresías y no puede borrarse",
    user_not_found: "Usuario no encontrado",
    network: "No se pudo conectar con el servidor",
    unknown: "Ocurrió un error inesperado",
  },
};

export type Catalog = typeof esMX;
