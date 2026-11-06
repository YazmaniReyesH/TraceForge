"""Cifrado del mapeo de redacción marcador→valor (F1-T4a, ADR-0016).

Usa **Fernet** (de la librería ``cryptography``): cifrado simétrico autenticado (AES-128-CBC +
HMAC-SHA256) con un formato de token versionado y probado. Se eligió sobre un esquema propio porque
es estándar, sencillo y ya trae integridad/anti-manipulación; ver ADR-0016.

La clave vive solo en el entorno (``TF_ENCRYPTION_KEY``), nunca en el repo ni en la base. Si no hay
clave (o es inválida), el cifrador queda **no configurado**: el llamador NO persiste el mapeo (jamás
se escribe en claro) y degrada avisando. El mapeo marcador→valor contiene secretos reales, así que
solo se guarda cifrado.

Rotación de claves: ``[[POR LLENAR: rotación/rencifrado (p. ej. MultiFernet con varias claves) y
retención/purga del mapeo cifrado — ADR-0016.]]``
"""

import json

from cryptography.fernet import Fernet

SCHEME = "fernet"


class RedactionCipher:
    """Cifra/descifra el mapa ``{marcador: valor}``. Sin clave => no cifra (degradación segura)."""

    scheme = SCHEME

    def __init__(self, key: str) -> None:
        # Clave malformada o ausente => no configurado (no se rompe la app; el llamador degrada).
        try:
            self._fernet: Fernet | None = Fernet(key.encode("utf-8")) if key else None
        except (ValueError, TypeError):
            self._fernet = None

    @property
    def is_configured(self) -> bool:
        return self._fernet is not None

    def encrypt_mapping(self, mapping: dict[str, str]) -> str:
        """Cifra el JSON del mapeo y devuelve el token (texto). Requiere estar configurado."""
        if self._fernet is None:
            raise RuntimeError("RedactionCipher no configurado: no se puede cifrar")
        payload = json.dumps(mapping, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return self._fernet.encrypt(payload).decode("utf-8")

    def decrypt_mapping(self, token: str) -> dict[str, str]:
        """Descifra un token y devuelve el mapeo (rehidratación; uso futuro)."""
        if self._fernet is None:
            raise RuntimeError("RedactionCipher no configurado: no se puede descifrar")
        payload = self._fernet.decrypt(token.encode("utf-8"))
        data: dict[str, str] = json.loads(payload.decode("utf-8"))
        return data
