# Plan general de datos, visión e ingesta

## 1. Objetivo

Entregar eventos de fútbol normalizados, reproducibles y rastreables para que el resto del sistema pueda calcular el estado del partido, seleccionar momentos y generar explicaciones.

El flujo sintético será el camino obligatorio de la demo. La percepción desde vídeo será una fuente experimental. Azure Event Hubs transportará los eventos en el entorno integrado y Azure Blob Storage conservará los archivos autorizados y artefactos de prueba. Todos los recursos de Azure podrán desplegarse desde comandos en la suscripción de cada integrante.

## 2. Resultado esperado

Al finalizar esta parte debe ser posible:

1. Crear o cargar un partido sintético corto y determinista.
2. Validar sus metadatos y eventos contra `MatchEvent 1.0`.
3. Reproducir los eventos de acuerdo con el reloj del partido y del vídeo.
4. Rechazar o registrar eventos inválidos y evitar el doble conteo de duplicados.
5. Publicar los eventos mediante una interfaz local o mediante Azure Event Hubs.
6. Guardar muestras y artefactos autorizados en el sistema local o en Azure Blob Storage.
7. Evaluar Roboflow Sports y SoccerNet sin convertir sus resultados experimentales en hechos confirmados.
8. Fusionar observaciones de vídeo solo cuando exista evidencia temporal y espacial suficiente.
9. Entregar ejemplos y pruebas que permitan a las otras personas trabajar sin depender del vídeo ni de Azure.

## 3. Alcance

### Incluido en el MVP

- Metadatos de partido, equipos, jugadores, dimensiones y direcciones de ataque.
- Generación determinista de un partido sintético.
- Eventos de pase, tiro, entrada, cambio de posesión, presión y recuperación.
- Validación de `MatchEvent 1.0`.
- Identificación de duplicados por `match_id` y `event_id`.
- Registro explícito de eventos inválidos, incompletos y tardíos.
- Reproducción progresiva del partido.
- Publicador y consumidor local para desarrollo.
- Publicador y consumidor de Azure Event Hubs para integración.
- Almacenamiento opcional de archivos en Azure Blob Storage.
- Infraestructura de Azure definida con Bicep y desplegable mediante Azure CLI.
- Pruebas unitarias, de contrato y una prueba de integración con Azure.

### Investigación posterior al flujo sintético

- Detección y seguimiento con Roboflow Sports.
- Detección de acciones con SoccerNet.
- Homografía y coordenadas normalizadas del campo.
- Asociación entre `track_id` y jugador conocido.
- Fusión de observaciones provenientes de varios modelos.

Estas capacidades solo entrarán en la demo principal si se verifican sus permisos, calidad y tiempo de procesamiento.

### Repositorios de referencia para visión

**Roboflow Sports.** Usaremos como referencia el [ejemplo de fútbol de Roboflow Sports](https://github.com/roboflow/sports/tree/main/examples/soccer). Incluye ejemplos de detección del campo, jugadores y balón, seguimiento, clasificación por equipo y una vista de posiciones tipo radar. Antes de incorporar código o modelos se revisarán por separado las licencias de sus componentes; el ejemplo indica AGPL-3.0 para Ultralytics y MIT para el código basado en Supervision.

**SoccerNet Team Ball Action Spotting.** Usaremos como referencia el repositorio [SoccerNet `sn-teamspotting`](https://github.com/SoccerNet/sn-teamspotting). Es un kit de desarrollo y evaluación para detectar acciones, su posición temporal y el equipo que las realiza. No se tratará como una biblioteca lista para producción: requiere revisar datasets, etiquetas, checkpoint, configuración, licencia GPL-3.0 y rendimiento sobre nuestro vídeo.

Los repositorios se fijarán a una revisión concreta cuando comience el experimento para evitar que cambios posteriores alteren los resultados. Ninguno será dependencia obligatoria del generador sintético, la validación o el transporte Azure.

### Fuera de esta responsabilidad

- Cálculo de marcador y estadísticas acumuladas.
- xT, VAEP, xG y patrones tácticos.
- Selección final de momentos.
- Narraciones, traducción y agentes.
- Superposiciones y experiencia React.
- Revisión editorial del análisis.

## 4. Arquitectura propuesta

```text
Generador sintético ──────────────┐
                                  │
Archivo de eventos ───────────────┤
                                  ▼
Vídeo → Roboflow/SoccerNet → adaptadores → validador MatchEvent 1.0
                                                │
                                                ▼
                                      deduplicación y orden
                                                │
                              ┌─────────────────┴─────────────────┐
                              ▼                                   ▼
                    publicador local                    Azure Event Hubs
                              │                                   │
                              └─────────────────┬─────────────────┘
                                                ▼
                                      consumidores del backend

Vídeos, muestras y observaciones originales → almacenamiento local/Blob Storage
```

El dominio y los generadores dependerán de interfaces propias, no del SDK de Azure. La selección del adaptador se realizará mediante configuración.

## 5. Contratos

### Evento de dominio

La carga útil seguirá `MatchEvent 1.0`, definido en `docs/08-formato-de-eventos.md`. No se cambiará ese contrato sin revisión de sus productores y consumidores.

### Sobre de transporte

Event Hubs transportará el evento dentro de un sobre que permita observar la publicación sin alterar el evento deportivo:

```json
{
  "message_version": "1",
  "message_id": "msg-104",
  "message_type": "match_event.created",
  "produced_at": "2026-10-08T18:30:00Z",
  "producer": "synthetic-generator",
  "correlation_id": "demo-001",
  "payload": {
    "schema_version": "1.0",
    "event_id": "evt-104",
    "match_id": "demo-001",
    "period": 1,
    "clock_ms": 802000,
    "video_time_ms": 805500,
    "type": "pass",
    "team_id": "team-a",
    "player_id": "player-7",
    "start": {"x": 43.0, "y": 51.0},
    "end": {"x": 62.0, "y": 46.0},
    "outcome": "success",
    "source": "synthetic",
    "confidence": null,
    "related_event_ids": []
  }
}
```

`produced_at` mide el transporte. No reemplaza `clock_ms` ni `video_time_ms`. El consumidor seguirá usando `event_id` como clave de idempotencia del evento deportivo.

## 6. Azure reproducible

### Servicios confirmados para esta parte

- **Azure Event Hubs:** transporte de eventos normalizados.
- **Azure Blob Storage:** vídeos autorizados, partidos sintéticos y observaciones de prueba.

### Infraestructura como código

El repositorio incorpora:

```text
infra/
└── azure/
    ├── main.bicep
    ├── dev.bicepparam.example
    └── README.md
```

`main.bicep` debe crear como mínimo:

- Un namespace de Event Hubs.
- Un event hub para eventos del partido.
- Grupos de consumidores separados cuando sea necesario.
- Una cuenta de StorageV2.
- Contenedores para partidos, vídeos autorizados y observaciones.
- Salidas con los nombres y endpoints necesarios para configurar la aplicación.

Los nombres globalmente únicos se derivarán de un prefijo suministrado por cada integrante y de un sufijo calculado por Bicep. No se guardarán identificadores de suscripción, contraseñas ni cadenas de conexión reales en Git.

### Flujo de despliegue

El despliegue documentado usará Azure CLI:

```bash
az login
az account set --subscription "<suscripción>"
az group create --name "<grupo>" --location "<región>"
az deployment group create \
  --resource-group "<grupo>" \
  --template-file infra/azure/main.bicep \
  --parameters projectPrefix="<prefijo-personal>"
```

Antes de desplegar se ofrecerá un comando `what-if`. La eliminación será un paso separado y explícito; nunca formará parte de las pruebas normales.

### Configuración de la aplicación

La aplicación elegirá adaptadores mediante variables de entorno. Se documentarán los nombres, pero no se confirmará ningún secreto en el repositorio. Para desarrollo individual se admitirá autenticación de Azure CLI. Para un despliegue compartido se preferirá identidad administrada y permisos RBAC.

El modo local debe funcionar sin cuenta de Azure:

```text
EVENT_TRANSPORT=memory
ARTIFACT_STORAGE=local
```

El modo integrado usará Azure:

```text
EVENT_TRANSPORT=azure_event_hubs
ARTIFACT_STORAGE=azure_blob
```

Los nombres definitivos de las variables se cerrarán al implementar los adaptadores.

## 7. Fases de trabajo

### Fase 0: contratos y muestra de aceptación

- Confirmar los campos de `MatchEvent 1.0` utilizados por el MVP.
- Crear ejemplos válido, inválido y sin campos opcionales.
- Definir un partido corto que incluya todos los tipos P0.
- Acordar con Persona 2 la política inicial para eventos tardíos.

**Salida:** conjunto de ejemplos revisado por productores y consumidores.

### Fase 1: flujo sintético local

- Implementar metadatos y generador determinista.
- Implementar validación, deduplicación y registro de errores.
- Implementar reproducción progresiva.
- Implementar publicador y consumidor en memoria.

**Salida:** flujo completo ejecutable sin nube ni modelos externos.

### Fase 2: infraestructura y transporte Azure

- Crear Bicep parametrizado.
- Documentar inicio de sesión, selección de suscripción, `what-if` y despliegue.
- Implementar adaptadores para Event Hubs y Blob Storage.
- Probar despliegue en al menos dos suscripciones o prefijos diferentes.
- Medir tiempo de publicación y consumo durante el partido de muestra.

**Salida:** cada integrante puede desplegar sus recursos y ejecutar el mismo flujo.

### Fase 3: sincronización con vídeo

- Elegir un vídeo sintético, propio o autorizado.
- Definir la relación entre reloj del partido y tiempo del vídeo.
- Verificar pausa, reinicio y adelanto.
- Registrar desfases y límites conocidos.

**Salida:** eventos sintéticos sincronizados con el vídeo permitido.

### Fase 4: experimentos de percepción

- Evaluar Roboflow Sports con una muestra anotada.
- Evaluar SoccerNet con la misma referencia temporal.
- Medir calidad por clase y tiempo de procesamiento.
- Registrar licencias, pesos y condiciones de uso.

**Salida:** informe de viabilidad; la demo sintética permanece operativa aunque el resultado sea negativo.

### Fase 5: fusión opcional

- Definir ventanas temporales y tolerancias espaciales.
- Conservar observaciones originales.
- Evitar duplicados entre fuentes.
- Emitir confianza y procedencia.
- Comparar eventos fusionados contra la muestra manual.

**Salida:** adaptador de vídeo solo si supera los criterios acordados.

## 8. Estrategia de pruebas

- **Unitarias:** validación, generación determinista, orden y deduplicación.
- **Contrato:** ejemplos de `MatchEvent 1.0` aceptados y rechazados de la misma forma por productor y consumidor.
- **Integración local:** partido completo mediante transporte en memoria.
- **Integración Azure:** publicación y consumo de una secuencia en Event Hubs y lectura/escritura autorizada en Blob Storage.
- **Reproducibilidad:** dos ejecuciones con la misma semilla producen los mismos eventos e identificadores.
- **Fallas:** credenciales ausentes, red interrumpida, evento duplicado, evento tardío y mensaje inválido.
- **Vídeo:** precisión y latencia se miden por separado; no se infiere identidad de jugador sin evidencia.

## 9. Definición de terminado

Una capacidad de esta parte está terminada cuando tiene:

1. Entrada definida.
2. Salida definida.
3. Implementación intercambiable cuando depende de Azure o de un modelo externo.
4. Prueba automatizada proporcional al riesgo.
5. Evidencia de ejecución.
6. Documentación para repetirla desde un entorno limpio.
7. Limitaciones conocidas registradas.

## 10. Dependencias y decisiones por cerrar

- Política exacta para eventos tardíos, corregidos o retirados.
- Región de Azure recomendada y límites de coste del equipo.
- Retención y particiones de Event Hubs.
- Política de retención y versionado de Blob; DV-US-09 fija la estructura inicial `matches`, `authorized-videos` y `observations`.
- Vídeo permitido para la demo; DV-US-10 ya define la sincronización local mediante `video_time_ms`, pero no decide el material.
- Criterios mínimos para integrar Roboflow o SoccerNet.
- Mecanismo operativo para producir y revisar evidencia de asociación; DV-US-12 ya exige confirmación manual o mapeo externo verificado antes de asignar `player_id`.
- Tolerancias definitivas para vídeo real; DV-US-13 implementa una política configurable y exige coincidencia temporal, espacial, de partido, seguimiento y equipo.

Estas decisiones no bloquean la Fase 1.
