export const LANGUAGES = [
  { value: 'es', code: 'ES', name: 'Español', description: 'Experiencia en español' },
  { value: 'en', code: 'EN', name: 'English', description: 'Experience in English' },
  { value: 'de', code: 'DE', name: 'Deutsch', description: 'Erlebnis auf Deutsch' },
  { value: 'zh', code: '中文', name: '中文', description: '中文体验' },
  { value: 'hi', code: 'HI', name: 'हिन्दी', description: 'हिन्दी में अनुभव' },
  { value: 'fr', code: 'FR', name: 'Français', description: 'Expérience en français' },
  { value: 'pt', code: 'PT', name: 'Português', description: 'Experiência em português' },
]

export const languageName = (value) => LANGUAGES.find((item) => item.value === value)?.name ?? value
