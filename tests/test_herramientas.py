"""Prueba las herramientas y el inventario, sin modelo de por medio."""

import json

import pytest

from agente.herramientas import HerramientaError, ejecutar_herramienta
from agente.inventario import Inventario


@pytest.fixture
def inventario():
    return Inventario()  # base en memoria, nueva en cada test


def siempre_si(accion):
    return True


def test_consultar_stock(inventario):
    resultado = json.loads(ejecutar_herramienta("consultar_stock", {"codigo": "a100"}, inventario, siempre_si))
    assert resultado["stock"] == 42
    assert resultado["codigo"] == "A100"


def test_buscar_articulos_sin_importar_mayusculas(inventario):
    resultado = json.loads(ejecutar_herramienta("buscar_articulos", {"texto": "TECLADO"}, inventario, siempre_si))
    assert [a["codigo"] for a in resultado] == ["B300", "B310"]


def test_herramienta_inexistente(inventario):
    with pytest.raises(HerramientaError, match="no existe"):
        ejecutar_herramienta("borrar_todo", {}, inventario, siempre_si)


def test_falta_un_argumento(inventario):
    with pytest.raises(HerramientaError, match="Falta el argumento"):
        ejecutar_herramienta("crear_pedido", {"codigo": "A100"}, inventario, siempre_si)


def test_cantidad_invalida(inventario):
    with pytest.raises(HerramientaError, match="mayor que cero"):
        ejecutar_herramienta("crear_pedido", {"codigo": "A100", "cantidad": 0}, inventario, siempre_si)
    assert inventario.pedidos() == []


def test_consultar_no_pide_confirmacion(inventario):
    def no_deberia_llamarse(accion):
        raise AssertionError("consultar no modifica datos")

    ejecutar_herramienta("consultar_stock", {"codigo": "A100"}, inventario, no_deberia_llamarse)
