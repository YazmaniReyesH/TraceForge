import { useEffect, useState } from "react";

import { getHealth, type HealthResponse } from "./api";

type Estado =
  { tipo: "cargando" } | { tipo: "ok"; datos: HealthResponse } | { tipo: "error"; mensaje: string };

function App() {
  const [estado, setEstado] = useState<Estado>({ tipo: "cargando" });

  useEffect(() => {
    let activo = true;
    getHealth()
      .then((datos) => {
        if (activo) setEstado({ tipo: "ok", datos });
      })
      .catch((error: unknown) => {
        const mensaje = error instanceof Error ? error.message : "Error desconocido";
        if (activo) setEstado({ tipo: "error", mensaje });
      });
    return () => {
      activo = false;
    };
  }, []);

  return (
    <main className="app">
      <h1>TraceForge</h1>
      <p className="subtitle">Documentación técnica para TI / Ciberseguridad</p>

      <section className="health-card">
        <h2>Estado del backend</h2>
        {estado.tipo === "cargando" && (
          <p>
            Consultando <code>/health</code>…
          </p>
        )}
        {estado.tipo === "ok" && (
          <p>
            <span className="badge badge-ok">{estado.datos.status}</span>
            <span className="version">versión {estado.datos.version}</span>
          </p>
        )}
        {estado.tipo === "error" && (
          <p>
            <span className="badge badge-error">sin conexión</span>
            <span className="version">{estado.mensaje}</span>
          </p>
        )}
      </section>
    </main>
  );
}

export default App;
