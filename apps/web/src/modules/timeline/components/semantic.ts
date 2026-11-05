// Realce semántico de entidades de seguridad: una capa DETERMINISTA por patrones (regex), NO IA y
// NO un lenguaje de Prism. Se aplica al comando y a la salida, y toma cada entidad como una UNIDAD
// (p. ej. una IP completa, que Prism partiría en los puntos). Convive con Prism porque se calcula
// ANTES: el texto se parte en [entidad | resto]; las entidades se envuelven aquí y el "resto" lo
// resalta Prism (ver highlight.ts). Colores por tokens --sem-* (timeline.css). Síncrono y barato.

export interface Segment {
  type: "text" | "sem";
  text: string;
  kind?: string; // nombre del grupo que casó (ip4/ip6/cve/hash/port/state/path)
}

// Patrones por entidad. El ORDEN define prioridad ante solapamientos (específico → genérico).
// Grupos con nombre (identificadores válidos) para saber qué casó. Documentado en timeline.md.
const PATTERNS: Array<[string, string]> = [
  // CVE: CVE-AAAA-N (4+ dígitos de secuencia).
  ["cve", "CVE-\\d{4}-\\d{4,}"],
  // Hashes hex por longitud: sha256 (64), sha1 (40), md5 (32). Más largo primero.
  ["hash", "\\b[0-9a-fA-F]{64}\\b|\\b[0-9a-fA-F]{40}\\b|\\b[0-9a-fA-F]{32}\\b"],
  // IPv6 (formas completas y comprimidas con ::).
  [
    "ip6",
    "(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}" +
      "|(?:[0-9a-fA-F]{1,4}:){1,7}:" +
      "|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}" +
      "|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}" +
      "|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}" +
      "|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}" +
      "|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}" +
      "|[0-9a-fA-F]{1,4}:(?::[0-9a-fA-F]{1,4}){1,6}" +
      "|:(?::[0-9a-fA-F]{1,4}){1,7}",
  ],
  // IPv4 con octetos válidos y CIDR opcional.
  ["ip4", "(?:(?:25[0-5]|2[0-4]\\d|1?\\d?\\d)\\.){3}(?:25[0-5]|2[0-4]\\d|1?\\d?\\d)(?:/\\d{1,2})?"],
  // Puerto/protocolo: 22/tcp, 443/udp, …
  ["port", "\\b\\d{1,5}/(?:tcp|udp|sctp)\\b"],
  // Estados de escaneo.
  ["state", "\\b(?:open|closed|filtered)\\b"],
  // Rutas de archivo absolutas (Unix), ≥2 segmentos para evitar falsos positivos de flags.
  ["path", "(?:/[A-Za-z0-9._-]+){2,}/?"],
];

const COMBINED = new RegExp(PATTERNS.map(([name, src]) => `(?<${name}>${src})`).join("|"), "gi");

function matchedKind(groups: Record<string, string | undefined> | undefined): string {
  if (!groups) return "";
  for (const key of Object.keys(groups)) {
    if (groups[key] !== undefined) return key;
  }
  return "";
}

/** Clase CSS para una entidad (color por token). ip4/ip6 → sem-ip; state → sem-state-<valor>. */
export function semClass(kind: string, text: string): string {
  if (kind === "ip4" || kind === "ip6") return "sem sem-ip";
  if (kind === "state") return `sem sem-state-${text.toLowerCase()}`;
  return `sem sem-${kind}`;
}

/** Parte el texto en segmentos de entidad y de resto (para que Prism resalte solo el resto). */
export function splitBySemantic(text: string): Segment[] {
  const segments: Segment[] = [];
  let last = 0;
  COMBINED.lastIndex = 0;
  for (const m of text.matchAll(COMBINED)) {
    const index = m.index ?? 0;
    if (index > last) segments.push({ type: "text", text: text.slice(last, index) });
    segments.push({ type: "sem", text: m[0], kind: matchedKind(m.groups) });
    last = index + m[0].length;
  }
  if (last < text.length) segments.push({ type: "text", text: text.slice(last) });
  return segments;
}

export function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** HTML con solo el realce semántico (sin Prism): para la SALIDA y como estado inicial del comando. */
export function renderSemanticHtml(text: string): string {
  return splitBySemantic(text)
    .map((seg) =>
      seg.type === "sem"
        ? `<span class="${semClass(seg.kind ?? "", seg.text)}">${escapeHtml(seg.text)}</span>`
        : escapeHtml(seg.text),
    )
    .join("");
}
