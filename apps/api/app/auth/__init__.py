"""Autenticación de TraceForge (F0-T4a).

Autenticación local (email + contraseña, argon2id + JWT) detrás del puerto de dominio
``AuthProvider`` (ver ADR-0007), para poder sumar SSO en el futuro sin reescribir.
La AUTORIZACIÓN fina (RBAC, workspace activo, rol efectivo) es F0-T4b: aquí solo
identidad y sesión.
"""
