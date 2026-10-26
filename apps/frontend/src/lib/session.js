export function readDemoSession() {
  try { return sessionStorage.getItem('itg:demo-user') || '' } catch { return '' }
}
