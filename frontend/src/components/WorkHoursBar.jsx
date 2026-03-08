import { useRef, useCallback } from 'react'

const MAX_HOUR = 23

export default function WorkHoursBar({ workHours, onChange }) {
  const [startH, endH] = workHours.split('-').map(Number)
  const trackRef = useRef(null)
  const totalHours = endH - startH

  const pxToHour = useCallback((clientX) => {
    const rect = trackRef.current.getBoundingClientRect()
    const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
    return Math.round(pct * MAX_HOUR)
  }, [])

  function startDrag(type, e) {
    e.preventDefault()
    const isTouch = e.type === 'touchstart'

    function onMove(ev) {
      const clientX = isTouch ? ev.touches[0].clientX : ev.clientX
      const h = pxToHour(clientX)
      if (type === 'start' && h < endH && h >= 0) onChange(`${h}-${endH}`)
      if (type === 'end' && h > startH && h <= MAX_HOUR) onChange(`${startH}-${h}`)
    }

    function onUp() {
      window.removeEventListener(isTouch ? 'touchmove' : 'mousemove', onMove)
      window.removeEventListener(isTouch ? 'touchend' : 'mouseup', onUp)
    }

    window.addEventListener(isTouch ? 'touchmove' : 'mousemove', onMove)
    window.addEventListener(isTouch ? 'touchend' : 'mouseup', onUp)
  }

  const startPct = (startH / MAX_HOUR) * 100
  const endPct = (endH / MAX_HOUR) * 100

  return (
    <div className="work-hours-bar">
      <div className="work-hours-label">
        <span>Work window</span>
        <span className="work-hours-span">
          {String(startH).padStart(2, '0')}:00 → {String(endH).padStart(2, '0')}:00 · {totalHours} hrs
        </span>
      </div>
      <div className="work-hours-track" ref={trackRef}>
        {/* inactive left */}
        <div className="wh-segment wh-inactive" style={{ width: `${startPct}%` }} />
        {/* active fill */}
        <div className="wh-segment wh-active" style={{ width: `${endPct - startPct}%` }} />
        {/* inactive right */}
        <div className="wh-segment wh-inactive" style={{ width: `${100 - endPct}%` }} />

        {/* start handle */}
        <div
          className="wh-handle"
          style={{ left: `${startPct}%` }}
          onMouseDown={e => startDrag('start', e)}
          onTouchStart={e => startDrag('start', e)}
        >
          <span className="wh-handle-label wh-label-left">{String(startH).padStart(2, '0')}:00</span>
        </div>

        {/* end handle */}
        <div
          className="wh-handle"
          style={{ left: `${endPct}%` }}
          onMouseDown={e => startDrag('end', e)}
          onTouchStart={e => startDrag('end', e)}
        >
          <span className="wh-handle-label wh-label-right">{String(endH).padStart(2, '0')}:00</span>
        </div>
      </div>
    </div>
  )
}
