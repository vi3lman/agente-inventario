"""El ciclo del agente: pensar, actuar, observar y repetir."""

from .herramientas import HERRAMIENTAS, HerramientaError, ejecutar_herramienta

INSTRUCCIONES = """Sos un asistente de inventario de una empresa paraguaya.
Respondé en español, en pocas oraciones.
- Usá las herramientas para obtener datos: nunca inventes stock, precios ni códigos.
- Si el usuario no sabe el código, buscá el artículo por su descripción.
- Los precios están en guaraníes: mostralos con punto de miles (por ejemplo, 4.500.000 Gs).
- Solo creá un pedido si el usuario lo pide. Si lo rechaza, no insistas."""

MAX_PASOS = 6
"""int: Máximo de rondas de herramientas por pregunta, para que el agente no quede en bucle."""


class Agente:
    """Agente que responde preguntas de inventario usando herramientas.

    Args:
        cliente: Cliente de la API de Anthropic (``anthropic.Anthropic()``).
            Los tests le pasan uno falso.
        inventario (agente.inventario.Inventario): Datos del inventario.
        confirmar (callable): Pregunta al usuario si aprueba una acción.
        modelo (str): Modelo de Claude a usar.
        registrar (callable | None): Si se indica, recibe una línea de texto
            por cada herramienta que el modelo usa (para ver el ciclo en vivo).
    """

    def __init__(self, cliente, inventario, confirmar, modelo, registrar=None):
        self.cliente = cliente
        self.inventario = inventario
        self.confirmar = confirmar
        self.modelo = modelo
        self.registrar = registrar or (lambda linea: None)
        self.mensajes = []  # historial: el agente recuerda la conversación

    def preguntar(self, texto):
        """Responde una pregunta del usuario, usando herramientas si hace falta.

        Returns:
            str: Respuesta final del modelo.
        """
        self.mensajes.append({"role": "user", "content": texto})

        for _ in range(MAX_PASOS):
            respuesta = self.cliente.messages.create(
                model=self.modelo,
                max_tokens=1024,
                system=INSTRUCCIONES,
                tools=HERRAMIENTAS,
                messages=self.mensajes,
            )
            # La respuesta del modelo pasa a formar parte del historial.
            self.mensajes.append({"role": "assistant", "content": respuesta.content})

            if respuesta.stop_reason != "tool_use":
                return _texto(respuesta.content)

            # El modelo pidió una o más herramientas: se ejecutan y se le devuelven los resultados.
            resultados = [
                self._usar_herramienta(bloque)
                for bloque in respuesta.content
                if bloque.type == "tool_use"
            ]
            self.mensajes.append({"role": "user", "content": resultados})

        return "No pude completar la consulta en los pasos permitidos. Probá reformularla."

    def _usar_herramienta(self, bloque):
        """Ejecuta un pedido de herramienta y arma el ``tool_result`` para el modelo.

        Un error no corta el programa: se le informa al modelo con
        ``is_error`` para que lo explique o pruebe otra cosa.
        """
        self.registrar(f"  → el modelo pide: {bloque.name}({bloque.input})")
        try:
            contenido = ejecutar_herramienta(bloque.name, bloque.input, self.inventario, self.confirmar)
            es_error = False
        except HerramientaError as error:
            contenido, es_error = str(error), True
        self.registrar(f"  ← resultado{' (error)' if es_error else ''}: {contenido}")
        return {
            "type": "tool_result",
            "tool_use_id": bloque.id,
            "content": contenido,
            "is_error": es_error,
        }


def _texto(contenido):
    """Une los bloques de texto de una respuesta del modelo."""

    return "\n".join(bloque.text for bloque in contenido if bloque.type == "text").strip()
