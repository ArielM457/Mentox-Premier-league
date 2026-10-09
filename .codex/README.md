# Configuración de Codex

Este proyecto configura Context7 como servidor MCP para consultar documentación actualizada de bibliotecas y frameworks durante la implementación.

## Requisitos

- Codex CLI con soporte para MCP remoto y OAuth.
- Proyecto marcado como confiable en Codex.
- Cuenta de Context7 para límites de uso autenticados.

## Activación por integrante

Cada integrante debe abrir este repositorio con Codex y aceptar la solicitud para confiar en el proyecto. Codex solo carga `.codex/config.toml` en proyectos confiables.

Si Codex no muestra la solicitud, se puede registrar la ruta local en `~/.codex/config.toml`:

```toml
[projects."/ruta/absoluta/Mentox-Premier-league"]
trust_level = "trusted"
```

Desde la raíz del repositorio, ejecutar:

```bash
codex mcp list
codex mcp login context7
```

Si la extensión de Codex está instalada pero la terminal responde `codex: command not found`, se debe abrir una terminal nueva después de instalar o actualizar la extensión. También se puede ejecutar temporalmente el binario incluido en la extensión usando su ruta absoluta. No se recomienda instalar un paquete con el mismo nombre desde Snap sin verificar que sea el CLI oficial esperado.

Si el entorno no puede abrir un navegador:

```bash
codex mcp login context7 --no-browser
```

Después del inicio de sesión se debe abrir una sesión nueva de Codex para que el inventario de herramientas incluya Context7.

## Verificación

```bash
codex mcp get context7
codex mcp list
```

La configuración compartida está en `.codex/config.toml` y usa el endpoint OAuth remoto:

```text
https://mcp.context7.com/mcp/oauth
```

Las credenciales pertenecen a cada integrante y no deben añadirse a `.codex/config.toml`, archivos `.env`, documentación ni commits.

## Uso esperado

Context7 se consulta cuando una tarea depende de la API o del comportamiento vigente de una biblioteca externa. No reemplaza la lectura de los requisitos, contratos y decisiones propias del repositorio.

Una respuesta debe distinguir entre documentación consultada con Context7, comportamiento comprobado mediante pruebas y decisiones propias del proyecto. Context7 no instala ni actualiza dependencias automáticamente; las versiones elegidas se declaran en `pyproject.toml` o `package.json` y se fijan en sus archivos de bloqueo.
