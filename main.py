"""Chat por consola con el agente de inventario.

Uso:
    export ANTHROPIC_API_KEY="..."      (en Windows PowerShell: $env:ANTHROPIC_API_KEY="...")
    python main.py
"""

import os
import sys

from agente.agente import Agente
from agente.inventario import Inventario

MODELO_POR_DEFECTO = "claude-haiku-5-5"


def confirmar_en_consola(accion):
    """Pide al usuario que apruebe una acción que modifica datos."""

    respuesta = input(f"\n  ¿Confirmás? {accion} [s/N]: ").strip().lower()
    return respuesta in ("s", "si", "sí")


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Falta la variable de entorno ANTHROPIC_API_KEY. Mirá el README.")

    import anthropic  # se importa acá para que los tests no necesiten la librería

    agente = Agente(
        cliente=anthropic.Anthropic(),
        inventario=Inventario(os.environ.get("INVENTARIO_DB", "inventario.db")),
        confirmar=confirmar_en_consola,
        modelo=os.environ.get("MODELO", MODELO_POR_DEFECTO),
    )
    print("Agente de inventario. Escribí tu pregunta (o 'salir').")
    while True:
        try:
            pregunta = input("\nVos: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if pregunta.lower() in ("salir", "exit", "q"):
            break
        if pregunta:
            print(f"\nAgente: {agente.preguntar(pregunta)}")


if __name__ == "__main__":
    main()
