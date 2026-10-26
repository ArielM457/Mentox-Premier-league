export function Tabs({ items, value, onChange, label, id }) {
  function onKeyDown(event, index) {
    let next
    if (event.key === 'ArrowRight') next = (index + 1) % items.length
    else if (event.key === 'ArrowLeft') next = (index - 1 + items.length) % items.length
    else if (event.key === 'Home') next = 0
    else if (event.key === 'End') next = items.length - 1
    else return
    event.preventDefault()
    onChange(items[next][0])
    event.currentTarget.parentElement.children[next].focus()
  }
  return (
    <nav className="match-tabs" role="tablist" aria-label={label}>
      {items.map(([key, text], index) => <button key={key} type="button" id={`${id}-${key}`} role="tab" aria-selected={value === key} aria-controls={`${id}-panel`} tabIndex={value === key ? 0 : -1} className={value === key ? 'active' : ''} onClick={() => onChange(key)} onKeyDown={(event) => onKeyDown(event, index)}>{text}</button>)}
    </nav>
  )
}
