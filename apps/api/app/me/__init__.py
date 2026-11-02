"""Módulo ``me``: vistas transversales acotadas al usuario autenticado (F0-T5b).

Resuelve recursos accesibles por el usuario a través de TODOS sus workspaces, sin pasar por el
gate de un workspace concreto. Solo depende de ``get_current_user`` (nunca filtra datos que el
usuario no pueda ya ver).
"""
