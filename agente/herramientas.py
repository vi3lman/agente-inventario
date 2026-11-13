"""Herramientas que el modelo puede pedir usar y el código que las ejecuta.

El modelo nunca ejecuta nada: solo pide usar una herramienta con ciertos
argumentos. Este módulo valida el pedido, lo ejecuta y devuelve el resultado
como texto JSON para que el modelo lo lea.
"""

import json

from .inventario import ArticuloNoEncontradoError

HERRAMIENTAS = [
    {
        "name": "consultar_stock",
        "description": (
            "Devuelve la descripción, el stock disponible y el precio en guaraníes "
            "de un artículo a partir de su código exacto (por ejemplo, A100)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "codigo": {"type": "string", "description": "Código del artículo."},
            },
            "required": ["codigo"],
        },
    },
    {
        "name": "buscar_articulos",
        "description": (
            "Busca artículos por una palabra de su descripción (por ejemplo, 'teclado'). "
            "Usala cuando el usuario no sepa el código."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "texto": {"type": "string", "description": "Palabra a buscar."},
            },
            "required": ["texto"],
        },
    },
    {
        "name": "crear_pedido",
        "description": (
            "Crea un pedido de compra para reponer stock de un artículo. Modifica datos: "
            "el usuario debe confirmarlo, y puede rechazarlo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "codigo": {"type": "string", "description": "Código del artículo."},
                "cantidad": {"type": "integer", "description": "Unidades a pedir (mayor que 0)."},
            },
            "required": ["codigo", "cantidad"],
        },
    },
]
"""list[dict]: Descripción de cada herramienta en el formato de la API (JSON Schema)."""

HERRAMIENTAS_QUE_MODIFICAN = frozenset({"crear_pedido"})
"""frozenset[str]: Herramientas que necesitan la confirmación del usuario."""


class HerramientaError(Exception):
    """El pedido de herramienta no se pudo ejecutar; el mensaje se le devuelve al modelo."""


def ejecutar_herramienta(nombre, entrada, inventario, confirmar):
    """Ejecuta una herramienta pedida por el modelo.

    Args:
        nombre (str): Nombre de la herramienta.
        entrada (dict): Argumentos que eligió el modelo.
        inventario (agente.inventario.Inventario): Datos sobre los que actúa.
        confirmar (callable): Recibe una descripción de la acción y devuelve
            True si el usuario la aprueba. Solo se usa para las herramientas
            que modifican datos.

    Returns:
        str: Resultado en JSON.

    Raises:
        HerramientaError: Si la herramienta no existe, faltan argumentos, el
            artículo no existe o el usuario rechazó la acción.
    """
    try:
        if nombre == "consultar_stock":
            resultado = inventario.consultar_stock(entrada["codigo"])
        elif nombre == "buscar_articulos":
            resultado = inventario.buscar_articulos(entrada["texto"])
        elif nombre == "crear_pedido":
            codigo, cantidad = entrada["codigo"], int(entrada["cantidad"])
            if not confirmar(f"Crear un pedido de {cantidad} unidades de {codigo}"):
                raise HerramientaError("El usuario rechazó crear el pedido. No se creó nada.")
            resultado = inventario.crear_pedido(codigo, cantidad)
        else:
            raise HerramientaError(f"La herramienta {nombre} no existe.")
    except KeyError as error:
        raise HerramientaError(f"Falta el argumento {error}.") from error
    except (ArticuloNoEncontradoError, ValueError) as error:
        raise HerramientaError(str(error)) from error
    return json.dumps(resultado, ensure_ascii=False)
