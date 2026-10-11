# **Pruebas de Postman**

Importa [match-intelligence.postman_collection.json](match-intelligence.postman_collection.json) en Postman. La colección ya trae `baseUrl` con el valor `http://localhost:8000`. Si inicias la API en otro puerto, cambia esa variable dentro de la colección.

## **Iniciar la API**

Desde la raíz del repositorio:

```powershell
python -m pip install -e '.\apps\backend[dev]'
python -m uvicorn match_intelligence.main:app --reload --app-dir apps/backend/src
```

La documentación OpenAPI queda en `http://localhost:8000/docs`.

## **Ejecutar las pruebas**

Abre la colección en Postman y usa Run collection. También puedes enviar las peticiones una por una. Cada petición comprueba el código HTTP y el resultado esperado. No necesitas importar un entorno aparte.

La colección cubre salud, validación de eventos y partidos, filtro y enrutamiento de agentes, narración en directo, preguntas, resumen final y reportes de error. Incluye casos válidos y casos de rechazo. Los cuerpos contienen solo datos sintéticos.

Las peticiones de enrutamiento muestran dos caminos. Un pase normal actualiza métricas sin llamar agentes. Un tiro peligroso produce una solicitud pequeña y un despacho para el agente de peligro y simulación. Este flujo todavía no guarda estado entre peticiones ni usa un canal durable.

Las peticiones de narrativa llevan `provider=fixture`. Ese proveedor produce una respuesta local repetible y no llama a Azure. Para probar Azure OpenAI, instala `apps/backend[agents]`, configura `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT` y `AZURE_OPENAI_API_KEY`, y elimina `?provider=fixture` de la URL de una petición de narrativa. Esa ejecución depende de tu despliegue de Azure y puede producir un texto o una selección diferente, así que las pruebas automáticas de la colección están diseñadas para el proveedor sintético.

Las rutas de validación solo revisan el formato; no guardan partidos ni eventos. El resumen se entrega pendiente de revisión editorial y estas rutas no publican contenido.
