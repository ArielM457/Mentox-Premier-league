# Sistema de diseño de The Prime Moment

Este documento consolida el sistema visual actual del producto a partir del frontend y los estilos compartidos del proyecto. Está basado en los tokens definidos en:

- [../apps/frontend/src/styles/base.css](../apps/frontend/src/styles/base.css)
- [../apps/frontend/src/styles/theme.css](../apps/frontend/src/styles/theme.css)
- [../apps/frontend/src/styles/palette.css](../apps/frontend/src/styles/palette.css)
- [../apps/frontend/src/styles/ux.css](../apps/frontend/src/styles/ux.css)

El objetivo es documentar una base estable para la marca, los componentes y la experiencia de partido sin duplicar decisiones que ya estén codificadas en CSS.

## 1. Identidad visual

La marca visible del producto es The Prime Moment. El sistema visual combina:

- una base profunda de color oscuro para transmitir elite, control y foco deportivo;
- un acento violeta para identidad de acción y CTA;
- un lime como color de energía, realce y señal de estado activo;
- superficies claras y neutrales para lectura y jerarquía.

La identidad gráfica se apoya en dos familias tipográficas:

- `Space Grotesk`: títulos, marca, números y texto de impacto.
- `DM Sans`: cuerpo de texto, botones, formularios y lectura general.

## 2. Paleta base

### 2.1 Colores primarios

| Token | Valor | Uso recomendado |
|---|---|---|
| `--navy` | `#151329` | base principal, texto principal, marca |
| `--navy-2` | `#0e0c20` | fondos profundos |
| `--navy-3` | `#201d3d` | superficies elevadas |
| `--violet` | `#8257f5` | acción principal, highlights |
| `--violet-dark` | `#6337df` | hover / interacción más intensa |
| `--lime` | `#d8ff65` | acento energético, estado activo |
| `--white` | `#ffffff` | fondo base, texto sobre fondo oscuro |
| `--off-white` | `#f8f7fc` | fondo de página y contenedores claros |

### 2.2 Escala de violetas

La escala de violetas está definida por el sistema de tokens del diseño para soportar jerarquías visuales y estados:

- `--ds-violet-05`: `#f3eefe`
- `--ds-violet-1`: `#e6ddfd`
- `--ds-violet-15`: `#dacdfc`
- `--ds-violet-2`: `#cdbcfb`
- `--ds-violet-3`: `#b49af9`
- `--ds-violet-4`: `#9b79f7`
- `--ds-violet-5`: `#8257f5`
- `--ds-violet-6`: `#6a46cb`
- `--ds-violet-7`: `#5235a1`
- `--ds-violet-8`: `#3b2476`
- `--ds-violet-9`: `#23134c`
- `--ds-violet-10`: `#0b0222`

### 2.3 Escala de lime

| Token | Valor | Uso |
|---|---|---|
| `--ds-lime-05` | `#fbfff0` | fondos suaves |
| `--ds-lime-1` | `#f7ffe0` | superficie clara |
| `--ds-lime-2` | `#efffc1` | contraste suave |
| `--ds-lime-3` | `#e8ffa3` | acento tenue |
| `--ds-lime-4` | `#e0ff84` | realce activo |
| `--ds-lime-5` | `#d8ff65` | color principal de marca |
| `--ds-lime-6` | `#b6d851` | profundidad media |
| `--ds-lime-7` | `#94b13d` | tono de apoyo |
| `--ds-lime-8` | `#718a28` | texto sobre acento |
| `--ds-lime-9` | `#4f6314` | apoyo extremo |
| `--ds-lime-10` | `#2d3c00` | base profunda |

### 2.4 Neutros y semánticos

| Token | Valor | Uso recomendado |
|---|---|---|
| `--muted` | `#706d82` | textos secundarios |
| `--line` | `#dfdce8` | bordes y separadores |
| `--lavender` | `#e7dcff` | fondos suaves de soporte |
| `--red` | `#f15a67` | avisos, errores, estados de riesgo |
| `--accent-soft` | `#f1ebff` | fondo de acción o detalle |
| `--accent-ink` | `#6337df` | texto o elementos sobre fondo suave |

## 3. Tokens semánticos de interfaz

La capa semántica del sistema, definida en [../apps/frontend/src/styles/ux.css](../apps/frontend/src/styles/ux.css), permite usar nombres orientados a la experiencia en lugar de colores brutales. Estos son los más importantes:

| Token | Light | Dark |
|---|---|---|
| `--surface` | `#ffffff` | `#211d38` |
| `--surface-raised` | `#ffffff` | `#302849` |
| `--surface-soft` | `#f1ebff` | `#443663` |
| `--navigation` | `#ffffff` | `#171428` |
| `--text` | `#151329` | `#f5f3fb` |
| `--muted` | `#706d82` | `#b7b1cc` |
| `--line` | `#dfdce8` | `#413b58` |
| `--action` | `#8257f5` | `#8257f5` |
| `--off-white` | `#f8f7fc` | `#100e20` |

Estas variables están pensadas para que la interface fluya entre modo claro y oscuro sin romper la identidad visual.

## 4. Tema claro y oscuro

### Modo claro

- Fondo general: `--off-white`
- Superficies: blanco y violeta muy claro
- Texto principal: `--navy` / `--text`
- Acento principal: `--violet`
- Acento energético: `--lime`

### Modo oscuro

- Fondo general: `#100e20`
- Superficies: `#211d38`, `#302849`, `#443663`
- Texto principal: `#f5f3fb`
- Texto secundario: `#b7b1cc`
- Bordes: `#413b58`
- Mismo acento violeta y lime para mantener coherencia de marca.

La preferencia de tema se activa con `data-theme` en `:root`, con valores `light` o `dark` según la configuración del cliente.

## 5. Tipografía

### 5.1 Escala de títulos

La aplicación usa `Space Grotesk` para los encabezados y la identidad de marca:

- H1: `clamp(32px, 3.6vw, 48px)`
- H2: `24px`
- Letter spacing: `-0.045em` en títulos destacados
- Line height: `1.12` para encabezados principales

### 5.2 Texto de lectura

Para cuerpo, formularios y UI se usa `DM Sans`:

- fuente base: `DM Sans`, sans-serif
- peso de botones: `700`
- estado de formularios: `font-weight: 700`
- color de texto: `var(--text)`

### 5.3 Marca

La marca usa un bloque cuadrado con la inicial y un giro sutil para reforzar la sensación de movimiento y dinamismo. La clase `brand-mark` genera un símbolo con:

- fondo oscuro (`--navy`)
- color lime (`--lime`)
- bordes redondeados y rotación ligera

## 6. Componentes y patrones

### 6.1 Botones

Los botones están centralizados en clases base:

- `.btn`
- `.btn-primary`
- `.btn-lime`
- `.btn-secondary`
- `.btn-ghost`

Reglas principales:

- radio redondeado (`999px`)
- altura mínima de `48px`
- ajuste de padding horizontal a `22px`
- hover con elevación ligera
- active con reducción de escala
- acción principal en violeta
- acento secundario en lime para elementos de confirmación o destaque

Ejemplo visual recomendado:

```css
.btn-primary {
  color: var(--white);
  background: var(--violet);
  box-shadow: 0 10px 25px rgba(130, 87, 245, .25);
}

.btn-lime {
  background: var(--lime);
  color: var(--navy);
}
```

### 6.2 Formularios y selects

Los selectores y entradas comparten una mirada minimalista con profundidad muy baja:

- fondo: `var(--field-bg)`
- borde: `var(--line)`
- texto: `var(--field-text)`
- radio: `10px`
- altura mínima: `40px` en selects, `48px` en formularios de diálogo

Los estados de focus usan amarillo/lime para claridad y accesibilidad.

### 6.3 Tarjetas y superficies

La interfaz usa jerarquía de superficie clara:

- fondo base: `--surface`
- fondo elevado: `--surface-raised`
- fondo suave: `--surface-soft`
- borde: `--line`

Esto permite distinguir contenido principal, paneles secundarios y bloques de acción sin romper la narrativa visual.

### 6.4 Sombras

El sistema usa sombras suaves para no saturar la UI:

- `--shadow: 0 20px 70px rgba(35, 25, 76, 0.13)`
- sombras de botón y panel con transparencias sobre navy/violet

## 7. Estado visual y comportamiento

El sistema incluye señales claras de interacción:

- hover: elevación y cambio de fondo
- focus visible: color lime con contorno visible
- disabled: opacidad reducida y cursor no permitido
- loading: spinner con borde violeta y animación de giro

Esto se refleja en los estilos del proyecto para botones, paneles, formularios y estado de carga.

## 8. Accesibilidad y legibilidad

El sistema se diseña para mantener una lectura clara y usable:

- contraste alto entre texto principal y fondo
- uso consistente de `--muted` para texto secundario
- contornos de foco visibles con `var(--lime)`
- límites claros entre superficies para ayudar a la separación visual
- semántica de color apoyada por texto y estructura, no solo por tono

## 9. Reglas de uso

### Recomendado

- Usar violeta para acciones primarias y CTA.
- Usar lime como realce puntual, no como fondo dominante.
- Mantener navy como base o fondo principal de la experiencia en vivo.
- Usar blanco o neutros claros para secciones de lectura.
- Alinear jerarquía visual con prioridad de contenido: título > apoyo > detalle.

### Evitar

- Saturar la interfaz con lime en más de un punto focal.
- Usar violetas demasiado claras sobre fondos blancos sin contraste suficiente.
- Mezclar demasiados tonos sin respetar la escala del sistema.
- Reemplazar texto dedicado por color únicamente para comunicar estado.

## 10. Cómo evolucionar este sistema

Siempre que se añadan nuevas pantallas o componentes:

1. reutilizar los tokens existentes antes de crear nuevos colores;
2. mantener los mismos nombres semánticos del sistema;
3. asegurar compatibilidad con modo claro y oscuro;
4. comprobar que la nueva UI no rompa la identidad de The Prime Moment;
5. documentar cualquier nuevo token en este archivo.

## 11. Fuentes de verdad

- [../apps/frontend/src/styles/base.css](../apps/frontend/src/styles/base.css)
- [../apps/frontend/src/styles/theme.css](../apps/frontend/src/styles/theme.css)
- [../apps/frontend/src/styles/palette.css](../apps/frontend/src/styles/palette.css)
- [../apps/frontend/src/styles/ux.css](../apps/frontend/src/styles/ux.css)
- [../docs/07-decisiones-tomadas.md](07-decisiones-tomadas.md)

Este sistema está vivo y debe convivir con la evolución del producto, pero sus pilares actuales quedan definidos por la escala de colores, la tipografía y los patrones de UI ya implementados en el frontend.
