# Plan de integración de modelos de visión e inteligencia futbolística

## 1. Objetivo

La solución utilizará **Roboflow Sports + SoccerNet** como capa de percepción del video y los combinará con modelos analíticos de fútbol para transformar un partido en inteligencia explicable y personalizada.

La separación será:

```text
Roboflow Sports → ¿Quién está y dónde?
SoccerNet       → ¿Qué ocurrió y cuándo?
xT / VAEP / xG → ¿Cuánto valor/peligro tuvo?
Match Intelligence → ¿Qué está pasando?
Attention Engine    → ¿Qué importa ahora?
Agente IA           → ¿Por qué importa y cómo se lo explico al usuario?
```

El proyecto seguirá soportando **eventos sintéticos** como entrada principal y controlada. El análisis de video será una segunda fuente que producirá el mismo formato de eventos.

---

## 2. Arquitectura propuesta

```text
                         PARTIDO
                            │
              ┌─────────────┴─────────────┐
              │                           │
       EVENTOS SINTÉTICOS                VIDEO
              │                           │
              │              ┌────────────┴────────────┐
              │              ▼                         ▼
              │      ROBOfLOW SPORTS              SOCCERNET
              │       ¿Quién/dónde?               ¿Qué pasó?
              │              │                         │
              │      jugadores/equipos          Pass / Shot
              │      balón/tracking             Tackle / Cross
              │      posiciones campo           Goal / etc.
              │              │                         │
              │              └────────────┬────────────┘
              │                           ▼
              │                    EVENT FUSION
              │                           │
              └──────────────┬────────────┘
                             ▼
                       EVENT STREAM
                             │
                             ▼
                    NORMALIZACIÓN / SPADL
                             │
                 ┌───────────┼───────────┐
                 ▼           ▼           ▼
                xT         VAEP          xG
                 │           │           │
                 └───────────┼───────────┘
                             ▼
                     MATCH STATE ENGINE
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
          Momentum        Pressure       Patterns
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                     ATTENTION ENGINE
                             │
                             ▼
                         AGENTE IA
                             │
             ┌───────────────┼───────────────┐
             ▼               ▼               ▼
          Overlay           Chat            Voz
                             │
                             ▼
                       Recap personalizado
```

---

## 3. Modelos y responsabilidad

### Roboflow Sports

Se utilizará para obtener la **estructura espacial del partido**:

- detección de jugadores;
- detección y tracking del balón;
- tracking de jugadores;
- clasificación por equipo;
- detección del campo;
- transformación de perspectiva/homografía;
- posiciones de jugadores y balón sobre el terreno.

Ejemplo:

```text
Track 21
Team A
posición = (42,30)

Track 34
Team A
posición = (68,35)

Ball
posición = (44,31)
```

Su principal valor para nuestro proyecto será permitir análisis espaciales: progresión, ocupación, presión, formaciones, distancias y patrones.

### SoccerNet

Se utilizará principalmente para **Action Spotting / Team Ball Action Spotting**.

Su función será detectar acciones futbolísticas y su instante:

```text
12:31 PASS
12:34 DRIVE
12:39 SHOT
12:45 GOAL
```

Cuando sea posible, Team Ball Action Spotting permitirá además asociar el evento con un equipo.

Su principal valor será convertir video en un flujo de acciones futbolísticas sin tener que inferir todas las acciones únicamente mediante reglas propias.

### Event Fusion Engine — componente propio

Combinará ambas fuentes.

```text
SoccerNet
PASS @ 12:34
Team A

+

Roboflow
Track 21 Team A (42,30)
Track 34 Team A (71,35)
Ball trajectory

↓

Evento enriquecido
```

Resultado conceptual:

```json
{
  "timestamp": 754.2,
  "type": "pass",
  "team": "A",
  "player_track": 21,
  "receiver_track": 34,
  "start": [42, 30],
  "end": [71, 35],
  "source": "video",
  "confidence": 0.91
}
```

### xT

Medirá cuánto peligro genera principalmente una progresión del balón.

```text
(42,30) → (71,35)
     ↓
ΔxT = +0.09
```

Será una señal rápida e interpretable para detectar progresiones peligrosas.

### VAEP

Valorará las acciones teniendo en cuenta el contexto reciente y su efecto sobre las probabilidades de marcar/recibir.

Permitirá diferenciar una acción estadísticamente común de una acción realmente valiosa dentro de la secuencia.

### xG

Se utilizará en tiros para estimar la calidad de la oportunidad.

```text
SHOT
xG = 0.41
```

### Match State + motores propios

Mantendrán el contexto acumulado del partido y derivarán:

- estadísticas recientes;
- momentum/control;
- presión;
- secuencias;
- patrones tácticos;
- desempeño de equipos/jugadores.

### Attention Engine — innovación principal

Combinará señales como:

```text
xT
VAEP
xG
MomentumChange
PressureChange
EventType
UserRelevance
```

para responder:

> **¿Qué merece la atención del usuario ahora?**

Solo los momentos suficientemente importantes llegarán al agente o generarán una interrupción por voz.

---

# 4. Cobertura de los casos de uso generales

## CU01 — Inteligencia del partido en tiempo real

**Cobertura: alta.**

Roboflow mantiene información espacial y SoccerNet detecta acciones. xT/VAEP/xG y Match State transforman esos datos en inteligencia actualizada.

```text
Video → percepción → eventos → analytics → Match State
```

---

## CU02 — Detección automática de momentos importantes

**Cobertura: muy alta.**

SoccerNet aporta acciones; Roboflow aporta contexto espacial; xT/VAEP/xG cuantifican el peligro y Attention Engine decide la importancia.

```text
PASS → DRIVE → PASS → SHOT
              +
xT / VAEP / xG
              ↓
momento importante
```

---

## CU03 — Explicación de por qué un momento es importante

**Cobertura: muy alta, indirectamente.**

Los modelos proporcionan la evidencia. El agente explica:

> La jugada fue importante porque el equipo progresó rápidamente, generó +0.18 xT y terminó con una oportunidad de 0.41 xG.

---

## CU04 — Modo aficionado casual

**Cobertura: indirecta.**

La percepción y analítica son las mismas; el agente/personalización transforma los resultados técnicos en explicaciones sencillas.

---

## CU05 — Modo analista

**Cobertura: muy alta.**

Es uno de los casos más beneficiados por Roboflow:

- posiciones;
- ocupación;
- distancias;
- xT;
- VAEP;
- xG;
- presión;
- momentum;
- patrones tácticos.

---

## CU06 — Modo equipo favorito

**Cobertura: alta.**

Roboflow clasifica jugadores por equipo y Team Action Spotting puede aportar equipo asociado a acciones. Personalization Engine aumenta la relevancia de eventos del club seleccionado.

---

## CU07 — Seguimiento de jugador

**Cobertura: alta, con una limitación.**

Roboflow permite mantener `track IDs`, pero identificar de forma fiable al jugador real/dorsal puede requerir una capa adicional de identificación.

Una vez asociado:

```text
Jugador favorito
     ↓
Track ID
     ↓
posición + acciones
     ↓
xT / VAEP / stats
     ↓
insights personalizados
```

---

## CU08 — Hitos individuales

**Cobertura: alta.**

Tracking + acciones permiten derivar hitos como:

- acciones peligrosas;
- pases/progresiones;
- tiros;
- distancia aproximada;
- participación en secuencias;
- máximos de velocidad si la calibración lo permite.

---

## CU09 — Impulso/control del partido

**Cobertura: muy alta.**

Nuestro Momentum Engine podrá combinar:

```text
posesión reciente
territorio
xT reciente
VAEP reciente
tiros
entradas al último tercio
recuperaciones
presión
```

Roboflow aporta especialmente la dimensión espacial.

---

## CU10 — Índice de control y caos

**Cobertura: alta.**

Se pueden combinar:

- cambios rápidos de posesión;
- tackles;
- transiciones;
- pases fallidos;
- tiros consecutivos;
- desplazamiento rápido del balón;
- cambios territoriales.

El índice será desarrollado por nosotros.

---

## CU11 — Patrones tácticos

**Cobertura: muy alta.**

Es otro de los principales motivos para usar Roboflow.

Las posiciones permiten derivar:

- anchura;
- altura;
- compactación;
- ocupación por zonas;
- superioridades;
- líneas;
- formaciones aproximadas;
- cambios de estructura;
- presión espacial.

---

## CU12 — Pregúntale al partido

**Cobertura: indirecta pero fundamental.**

El agente no analizará el video directamente.

```text
Usuario
"¿Por qué está dominando A?"
       ↓
Agente
       ↓
Match State + Analytics
       ↓
respuesta respaldada por datos
```

Los datos originales pueden haber sido obtenidos mediante Roboflow y SoccerNet.

---

## CU13 — Comentarista automático con IA

**Cobertura: alta como fuente de contexto.**

SoccerNet detecta lo ocurrido, analytics determina su importancia y Attention Engine decide si vale la pena hablar.

```text
evento
 ↓
importance
 ↓
¿hablar?
```

Esto evita narrar cada pase.

---

## CU14 — Resumen automático del partido

**Cobertura: alta.**

Los eventos importantes seleccionados durante el encuentro quedan almacenados y el agente puede construir el recap a partir de ellos.

---

## CU15 — Resumen personalizado

**Cobertura: alta.**

El mismo conjunto de momentos puede reorganizarse según:

- equipo favorito;
- jugador favorito;
- casual;
- analista.

---

## CU16 — Experiencia multilingüe

**Cobertura directa de estos modelos: ninguna.**

Será responsabilidad del agente/modelo de lenguaje y de la capa de voz.

SoccerNet y Roboflow producen la misma evidencia independientemente del idioma.

---

## CU17 — Modo transmisión

**Cobertura: alta.**

Los insights podrán exponerse como objetos estructurados:

```json
{
  "type": "dangerous_attack",
  "timestamp": 402.7,
  "team": "A",
  "priority": 91,
  "metrics": {
    "xT": 0.18,
    "xG": 0.41
  },
  "display_duration": 6
}
```

Esto permite alimentar overlays, dashboards o integraciones de broadcaster.

---

# 5. Resumen de cobertura

| Caso de uso | Roboflow | SoccerNet | Analytics / sistema propio |
|---|---|---|---|
| CU01 Inteligencia real-time | Alto | Alto | Esencial |
| CU02 Momentos importantes | Medio | Alto | Esencial |
| CU03 Explicar importancia | Evidencia | Evidencia | Esencial |
| CU04 Casual | Indirecto | Indirecto | Esencial |
| CU05 Analista | Muy alto | Alto | Esencial |
| CU06 Equipo favorito | Alto | Alto | Alto |
| CU07 Jugador favorito | Alto* | Medio | Alto |
| CU08 Hitos individuales | Alto | Alto | Alto |
| CU09 Momentum | Muy alto | Alto | Esencial |
| CU10 Control/caos | Alto | Alto | Esencial |
| CU11 Patrones tácticos | Muy alto | Medio | Esencial |
| CU12 Pregúntale al partido | Indirecto | Indirecto | Esencial |
| CU13 Comentarista IA | Indirecto | Alto | Esencial |
| CU14 Recap | Indirecto | Alto | Esencial |
| CU15 Recap personalizado | Indirecto | Indirecto | Esencial |
| CU16 Multilingüe | — | — | Esencial |
| CU17 Broadcast | Alto | Alto | Esencial |

`*` El seguimiento visual es fuerte; la identidad real/dorsal puede requerir un componente adicional.

---

# 6. Estrategia de implementación

## Fase 1 — Núcleo del producto

Usar los eventos sintéticos proporcionados/generados para construir primero:

```text
Event Stream
→ SPADL
→ xT / VAEP / xG
→ Match State
→ Attention Engine
→ Agent
→ UI / Voice
```

Esto garantiza que la inteligencia principal no dependa de Computer Vision.

## Fase 2 — Video Intelligence

Integrar:

```text
Roboflow Sports
+
SoccerNet
+
Event Fusion
```

y hacer que produzcan el mismo formato de evento utilizado en Fase 1.

## Fase 3 — Inteligencia espacial

Utilizar las posiciones de Roboflow para:

```text
Momentum
Pressure
Formations
Tactical Patterns
Player Movement
```

## Fase 4 — Experiencia avanzada

Conectar la inteligencia con:

```text
Personalization
Conversational Agent
Voice
Automatic Recap
Broadcaster API
```

---

# 7. Resultado final

La arquitectura no dependerá de un único modelo.

Cada componente tendrá una responsabilidad clara:

```text
ROBOfLOW SPORTS
      ↓
¿QUIÉN Y DÓNDE?

SOCCERNET
      ↓
¿QUÉ PASÓ?

xT / VAEP / xG
      ↓
¿CUÁNTO VALIÓ?

MATCH INTELLIGENCE
      ↓
¿QUÉ ESTÁ PASANDO?

ATTENTION ENGINE
      ↓
¿QUÉ IMPORTA AHORA?

AGENTE IA
      ↓
¿POR QUÉ IMPORTA?

PERSONALIZATION
      ↓
¿CÓMO TE LO CUENTO?
```

Esto permite que los modelos open source resuelvan la percepción y parte de la analítica, mientras que la diferenciación del proyecto se concentra en **fusión de eventos, inteligencia contextual, Attention Engine, explicabilidad, personalización y experiencia conversacional en tiempo real**.
