"""Prueba el ciclo del agente con un cliente falso: no llama a la API real."""

from types import SimpleNamespace

from agente.agente import MAX_PASOS, Agente
from agente.inventario import Inventario


def texto(contenido):
    return SimpleNamespace(type="text", text=contenido)


def pide_herramienta(nombre, entrada, id_="toolu_1"):
    return SimpleNamespace(type="tool_use", id=id_, name=nombre, input=entrada)


def respuesta(*bloques, stop_reason="end_turn"):
    return SimpleNamespace(content=list(bloques), stop_reason=stop_reason)


class ClienteFalso:
    """Devuelve respuestas guionadas, una por llamada, y guarda lo que recibió."""

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []
        self.messages = self  # imita cliente.messages.create(...)

    def create(self, **kwargs):
        # Copia del historial tal como estaba en esta llamada.
        self.llamadas.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.respuestas.pop(0)


def crear_agente(cliente, confirmar=lambda accion: True):
    return Agente(cliente, Inventario(), confirmar, modelo="modelo-de-prueba")


def test_respuesta_directa_sin_herramientas():
    cliente = ClienteFalso(respuesta(texto("¡Hola! ¿En qué te ayudo?")))

    assert crear_agente(cliente).preguntar("Hola") == "¡Hola! ¿En qué te ayudo?"
    assert len(cliente.llamadas) == 1


def test_usa_la_herramienta_y_le_devuelve_el_resultado_al_modelo():
    cliente = ClienteFalso(
        respuesta(pide_herramienta("consultar_stock", {"codigo": "A100"}), stop_reason="tool_use"),
        respuesta(texto("Quedan 42 notebooks.")),
    )

    final = crear_agente(cliente).preguntar("¿Cuántas notebooks A100 quedan?")

    assert final == "Quedan 42 notebooks."
    resultado = cliente.llamadas[1]["messages"][-1]["content"][0]
    assert resultado["type"] == "tool_result"
    assert resultado["tool_use_id"] == "toolu_1"
    assert '"stock": 42' in resultado["content"]
    assert resultado["is_error"] is False


def test_envia_las_herramientas_y_las_instrucciones():
    cliente = ClienteFalso(respuesta(texto("ok")))

    crear_agente(cliente).preguntar("Hola")

    llamada = cliente.llamadas[0]
    assert {h["name"] for h in llamada["tools"]} == {"consultar_stock", "buscar_articulos", "crear_pedido"}
    assert "nunca inventes" in llamada["system"]


def test_articulo_inexistente_se_informa_como_error_al_modelo():
    cliente = ClienteFalso(
        respuesta(pide_herramienta("consultar_stock", {"codigo": "Z999"}), stop_reason="tool_use"),
        respuesta(texto("Ese código no existe.")),
    )

    crear_agente(cliente).preguntar("¿Stock de Z999?")

    resultado = cliente.llamadas[1]["messages"][-1]["content"][0]
    assert resultado["is_error"] is True
    assert "No existe el artículo Z999" in resultado["content"]


def test_pedido_rechazado_por_el_usuario_no_se_crea():
    inventario = Inventario()
    cliente = ClienteFalso(
        respuesta(pide_herramienta("crear_pedido", {"codigo": "A200", "cantidad": 10}), stop_reason="tool_use"),
        respuesta(texto("Entendido, no creé el pedido.")),
    )
    agente = Agente(cliente, inventario, confirmar=lambda accion: False, modelo="modelo-de-prueba")

    agente.preguntar("Pedí 10 monitores")

    assert inventario.pedidos() == []
    resultado = cliente.llamadas[1]["messages"][-1]["content"][0]
    assert resultado["is_error"] is True


def test_pedido_confirmado_se_crea():
    inventario = Inventario()
    acciones = []
    cliente = ClienteFalso(
        respuesta(pide_herramienta("crear_pedido", {"codigo": "A200", "cantidad": 10}), stop_reason="tool_use"),
        respuesta(texto("Listo, pedido creado.")),
    )
    agente = Agente(cliente, inventario, confirmar=lambda accion: acciones.append(accion) or True,
                    modelo="modelo-de-prueba")

    agente.preguntar("Pedí 10 monitores")

    assert [p["cantidad"] for p in inventario.pedidos()] == [10]
    assert acciones == ["Crear un pedido de 10 unidades de A200"]


def test_recuerda_la_conversacion():
    cliente = ClienteFalso(respuesta(texto("Hola")), respuesta(texto("Dijiste hola")))
    agente = crear_agente(cliente)

    agente.preguntar("hola")
    agente.preguntar("¿Qué dije antes?")

    roles = [m["role"] for m in cliente.llamadas[1]["messages"]]
    assert roles == ["user", "assistant", "user"]


def test_corta_si_el_modelo_pide_herramientas_sin_fin():
    pedido = respuesta(pide_herramienta("buscar_articulos", {"texto": "x"}), stop_reason="tool_use")
    cliente = ClienteFalso(*[pedido] * MAX_PASOS)

    final = crear_agente(cliente).preguntar("buscá algo")

    assert "No pude completar" in final
    assert len(cliente.llamadas) == MAX_PASOS
