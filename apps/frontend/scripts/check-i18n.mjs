// Español e inglés deben tener las mismas claves. Un texto que solo existe en un idioma deja
// huecos en la interfaz o la rompe al cambiar de idioma (pasó con los textos de Visión IA).
import { strings } from '../src/i18n/strings.js'

const keys = (value, path = '') => (
  value && typeof value === 'object' && !Array.isArray(value)
    ? Object.entries(value).flatMap(([key, child]) => keys(child, path ? `${path}.${key}` : key))
    : [path]
)

const [es, en] = [keys(strings.es), keys(strings.en)].map((list) => new Set(list))
const onlyEs = [...es].filter((key) => !en.has(key))
const onlyEn = [...en].filter((key) => !es.has(key))

if (onlyEs.length || onlyEn.length) {
  if (onlyEs.length) console.error(`Solo en español (${onlyEs.length}): ${onlyEs.join(', ')}`)
  if (onlyEn.length) console.error(`Solo en inglés (${onlyEn.length}): ${onlyEn.join(', ')}`)
  process.exit(1)
}
console.log(`i18n: ${es.size} claves iguales en español e inglés.`)
