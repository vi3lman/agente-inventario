# Agente de inventario con Claude

Un agente de IA que responde preguntas sobre un inventario en lenguaje natural
y puede crear pedidos de compra, usando **tool calling** sobre la API de Claude.

```text
Vos: ¿Cuánto stock queda de teclados?
Agente: Hay dos modelos: el teclado mecánico (B300) con 15 unidades y el
        inalámbrico (B310) con 3 unidades.

Vos: Pedí 20 del inalámbrico.
  ¿Confirmás? Crear un pedido de 20 unidades de B310 [s/N]: s
Agente: Listo, creé el pedido N° 1 por 20 teclados inalámbricos (B310).
```

Simula lo que haría un agente conectado a un ERP como SAP Business One: el
modelo no tiene los datos, los consulta con herramientas.

## Cómo funciona

```text
         pregunta
Usuario ─────────▶ Agente ── mensajes + herramientas ──▶ Claude (API)
                     ▲                                     │
                     │        "usá consultar_stock(A100)"  │
                     │◀────────────────────────────────────┘
                     │
                     ├── ejecuta la herramienta en Python ──▶ SQLite
                     │
                     └── le devuelve el resultado ──▶ Claude ──▶ respuesta final
```

1. El agente le manda a Claude la pregunta, unas instrucciones y la
   descripción de las herramientas (nombre, para qué sirve y parámetros en
   JSON Schema).
2. Si Claude necesita datos, no responde con texto: responde con un pedido
   de herramienta (`stop_reason == "tool_use"`).
3. El código de Python ejecuta esa herramienta. **El modelo nunca ejecuta
   nada por sí solo.**
4. El resultado vuelve a Claude como `tool_result`, y el ciclo se repite
   hasta que Claude responde con texto.

### Herramientas

| Herramienta | Qué hace | ¿Modifica datos? |
| --- | --- | --- |
| `consultar_stock` | Stock y precio de un artículo por código | No |
| `buscar_articulos` | Busca por descripción cuando no se sabe el código | No |
| `crear_pedido` | Crea un pedido de compra | Sí, **pide confirmación** |

### Decisiones de diseño

- **Confirmación humana** en las acciones que modifican datos (*human in the
  loop*). Si el usuario dice que no, el agente se entera y no insiste.
- **Errores como resultado, no como caída.** Si el artículo no existe, el
  error vuelve al modelo con `is_error: true` y el modelo lo explica.
- **Límite de pasos** (`MAX_PASOS`) para que el agente no quede en un bucle de
  herramientas.
- **Instrucciones que limitan el rol**: usar herramientas y no inventar datos,
  para reducir alucinaciones.
- **Memoria de la conversación**: el historial se manda en cada llamada.
- **Testeable sin la API**: el cliente se inyecta, y los tests usan uno falso
  con respuestas guionadas.

## Estructura

```text
agente/
  inventario.py     datos en SQLite (artículos y pedidos)
  herramientas.py   definición de las herramientas y su ejecución
  agente.py         el ciclo del agente
main.py             chat por consola
tests/              tests con pytest, sin llamar a la API
```

## Cómo ejecutarlo

Requiere Python 3.10+ y una API key de Anthropic
([console.anthropic.com](https://console.anthropic.com)).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

export ANTHROPIC_API_KEY="tu-clave" # Windows: $env:ANTHROPIC_API_KEY="tu-clave"
python main.py
```

Variables opcionales: `MODELO` (por defecto `claude-haiku-5-5`) e
`INVENTARIO_DB` (por defecto `inventario.db`).

## Tests

```bash
pytest
```

Los tests no necesitan API key: prueban el ciclo del agente con un cliente
falso (respuesta directa, uso de herramientas, errores, confirmación aceptada
y rechazada, memoria y límite de pasos) y las herramientas por separado.

## Próximos pasos

- Conectar las herramientas a una API real (por ejemplo, el Service Layer de
  SAP Business One) en lugar de SQLite.
- Exponer las herramientas como servidor MCP (Model Context Protocol).
- Medir la calidad con un conjunto de preguntas de prueba.
