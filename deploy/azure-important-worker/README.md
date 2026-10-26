# Worker de eventos importantes

Imagen CPU de The Prime Moment para consumir `important-events`. No contiene
pesos de visión ni necesita GPU. Azure Container Apps Job la inicia únicamente
cuando Service Bus tiene mensajes.

El worker usa identidad administrada, valida `RoutingOutcome` y aplica
`complete`, `abandon` o `dead-letter`. El ejecutor actual confirma el despacho;
los ejecutores de CrewAI se conectan posteriormente mediante
`ImportantEventHandler`.

Si Azure for Students bloquea ACR Tasks, construya con Docker local:

```bash
export MENTOX_IMAGE_BUILD_MODE=local
bash infra/azure/deploy-important-worker.sh
```

El script solicita `sudo` para Docker. El Job queda con escala `0-1`, 0,5 vCPU
y 1 GiB; no usa GPU.
