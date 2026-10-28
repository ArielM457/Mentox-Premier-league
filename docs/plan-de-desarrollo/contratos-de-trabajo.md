# **Contratos de trabajo entre módulos**

Estos ejemplos permiten desarrollar los módulos en paralelo. Son una propuesta de integración para cerrar al comienzo del trabajo. El contrato de entrada ya definido es [`MatchEvent 1.0`](../08-formato-de-eventos.md); los demás nombres y campos de este documento todavía no son API implementada.

## **Reglas comunes**

Cada objeto lleva `match_id`, versión de contrato y referencias a eventos cuando describe un hecho del partido. Usamos milisegundos para tiempo de partido y vídeo. Una métrica sin datos suficientes se omite o se marca como no disponible; no se reemplaza por cero. Los identificadores son estables durante la reproducción.

Los ejemplos se guardarán como archivos de prueba en una carpeta compartida del repositorio. Quien produce un contrato añade un ejemplo válido, uno sin datos opcionales y uno inválido. Quien lo consume prueba su módulo con esos tres casos.

## **Entrada: evento y preferencias**

Persona 1 entrega eventos según `MatchEvent 1.0`. Persona 4 entrega preferencias con idioma `es`, `en`, `de`, `zh`, `hi`, `fr` o `pt`; modo `casual`, `analyst`, `professional_analyst` o `player`; nivel `simple`, `normal` o `advanced`; y los identificadores opcionales de club y jugador favoritos. `professional_analyst` fuerza el nivel avanzado. Persona 2 usa esas preferencias solo para puntuar relevancia; Persona 3 las usa para redactar y seleccionar contenido.

## **Salida de Persona 2: estado**

```json
{
  "contract_version": "1",
  "match_id": "demo-001",
  "period": 1,
  "clock_ms": 802000,
  "score": {"team-a": 0, "team-b": 0},
  "metrics": [
    {
      "key": "shots",
      "team_id": "team-a",
      "value": 2,
      "unit": "count",
      "window_ms": 600000,
      "formula_version": "1",
      "source_event_ids": ["evt-101", "evt-103"]
    }
  ],
  "recent_event_ids": ["evt-101", "evt-103", "evt-104"]
}
```

`MatchSnapshot v1` debe poder generarse de forma reproducible desde eventos normalizados. Persona 2 define los nombres finales de métricas y documenta sus fórmulas.

## **Salida de Persona 2: momento candidato**

```json
{
  "contract_version": "1",
  "candidate_id": "moment-12",
  "match_id": "demo-001",
  "period": 1,
  "clock_ms": 802000,
  "kind": "pressure_shift",
  "priority": 75,
  "facts": [
    {
      "key": "recoveries",
      "team_id": "team-a",
      "value": 3,
      "unit": "count",
      "window_ms": 600000,
      "source_event_ids": ["evt-98", "evt-101", "evt-103"]
    }
  ],
  "source_event_ids": ["evt-98", "evt-101", "evt-103"],
  "evidence_limits": []
}
```

`InsightCandidate v1` contiene hechos estructurados y un motivo de selección. La prioridad propuesta va de 0 a 100; Persona 2 documenta cómo la calcula.

## **Salida de Persona 3: narración propuesta**

```json
{
  "contract_version": "1",
  "draft_id": "draft-12-es",
  "candidate_id": "moment-12",
  "match_id": "demo-001",
  "language": "es",
  "mode": "casual",
  "content_kind": "live",
  "headline": "La presión del Equipo A está creciendo",
  "explanation": "Recuperó el balón tres veces en este tramo.",
  "source_event_ids": ["evt-98", "evt-101", "evt-103"],
  "verification_status": "approved",
  "editorial_status": null
}
```

`NarrativeDraft v1` no se publica si la verificación rechaza una afirmación. Un análisis con `content_kind` igual a `final` necesita estado editorial aprobado. El flujo exacto de revisión en directo está pendiente. Persona 3 conserva una referencia a la versión original si corrige un borrador.

## **Salida de Persona 4: mensaje para pantalla**

```json
{
  "contract_version": "1",
  "message_id": "overlay-12-es",
  "draft_id": "draft-12-es",
  "match_id": "demo-001",
  "video_time_ms": 805500,
  "show_for_ms": 6000,
  "priority": 75,
  "language": "es",
  "headline": "La presión del Equipo A está creciendo",
  "source_event_ids": ["evt-98", "evt-101", "evt-103"]
}
```

`OverlayMessage v1` necesita un tiempo de vídeo confiable. Si no existe, Persona 4 lo obtiene de la sincronización del partido y no finge que proviene del detector.

## **Reportes y aprobación**

Persona 4 recibe la acción de reportar, aprobar o rechazar desde la interfaz y conserva el estado publicado. Persona 3 recibe un reporte con identificador de borrador, motivo y evidencia disponible; devuelve resultado de verificación, corrección propuesta o confirmación de que la salida era correcta. La publicación final requiere la aprobación definida por el equipo.

## **Cambios del contrato**

Una persona propone el cambio con un ejemplo y su motivo. Las personas que producen y consumen ese contrato revisan el impacto. Si rompe datos existentes, se crea otra versión y se mantienen ejemplos de ambas durante la migración.
