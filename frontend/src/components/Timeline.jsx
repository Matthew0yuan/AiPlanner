import { useState, useEffect, useRef } from 'react'

const FOCUS_SEC = 25 * 60
const BREAK_SEC = 5 * 60

function fmt(sec) {
  return `${String(Math.floor(sec / 60)).padStart(2, '0')}:${String(sec % 60).padStart(2, '0')}`
}

const POPUP_HTML = `<!DOCTYPE html>
<html>
<head>
  <title>Focus Timer</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #0f0f0f;
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      padding: 16px 20px 18px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      user-select: none;
    }
    #task-wrap {
      background: #1e1a2e;
      border: 1px solid #a78bfa44;
      border-radius: 8px;
      padding: 8px 12px;
    }
    #task-label {
      font-size: 0.62rem;
      color: #a78bfa99;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 3px;
    }
    #task {
      font-size: 0.85rem;
      font-weight: 600;
      color: #e0d9ff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    #time {
      font-size: 2.6rem;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
      letter-spacing: -2px;
      line-height: 1;
      transition: color 0.4s;
    }
    #phase-label {
      font-size: 0.65rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #555;
      margin-top: 2px;
    }
  </style>
</head>
<body>
  <div id="task-wrap">
    <div id="task-label">Current task</div>
    <div id="task">—</div>
  </div>
  <div id="time">--:--</div>
  <div id="phase-label">focus</div>
  <script>
    window.addEventListener('message', function(e) {
      if (e.data.task !== undefined) document.getElementById('task').textContent = e.data.task
      if (e.data.time !== undefined) document.getElementById('time').textContent = e.data.time
      if (e.data.color !== undefined) {
        document.getElementById('time').style.color = e.data.color
        document.getElementById('task-wrap').style.borderColor = e.data.color + '44'
        document.getElementById('task-wrap').style.background = e.data.color + '11'
        document.getElementById('task-label').style.color = e.data.color + 'aa'
        document.getElementById('task').style.color = e.data.taskColor || '#e0d9ff'
      }
      if (e.data.phase !== undefined) document.getElementById('phase-label').textContent = e.data.phase
      if (e.data.title !== undefined) document.title = e.data.title
    })
  </script>
</body>
</html>`

function openTimerPopup() {
  const popup = window.open(
    '',
    'focusTimer',
    'width=280,height=160,menubar=no,toolbar=no,location=no,status=no,resizable=yes'
  )
  if (popup) {
    popup.document.write(POPUP_HTML)
    popup.document.close()
  }
  return popup
}

export default function Timeline({ blocks, onAction, onReset }) {
  const done = blocks.filter(b => b.status === 'done').length
  const total = blocks.filter(b => b.mode !== 'break').length
  const [activeTimer, setActiveTimer] = useState(null)
  const popupRef = useRef(null)
  const intervalRef = useRef(null)

  useEffect(() => {
    if (!activeTimer || (activeTimer.phase !== 'focus' && activeTimer.phase !== 'break')) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
      return
    }

    intervalRef.current = setInterval(() => {
      setActiveTimer(current => {
        if (!current) {
          return null
        }

        if (current.phase !== 'focus' && current.phase !== 'break') {
          return current
        }

        if (current.remaining <= 1) {
          if (current.phase === 'focus') {
            return { ...current, phase: 'break', remaining: BREAK_SEC }
          }

          return { ...current, phase: 'finished', remaining: 0 }
        }

        return { ...current, remaining: current.remaining - 1 }
      })
    }, 1000)

    return () => {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [activeTimer?.index, activeTimer?.phase])

  useEffect(() => {
    if (!activeTimer || activeTimer.phase === 'finished') {
      if (popupRef.current && !popupRef.current.closed) {
        popupRef.current.close()
      }
      popupRef.current = null
      return
    }

    // open popup if not already open
    if (!popupRef.current || popupRef.current.closed) {
      popupRef.current = openTimerPopup()
    }

    const { phase, remaining } = activeTimer
    const task = blocks[activeTimer.index]?.task_title || ''
    const isFocus = phase === 'focus'
    const timeStr = isFocus ? fmt(remaining) : `Break ${fmt(remaining)}`
    const color = isFocus ? '#a78bfa' : '#4ade80'

    popupRef.current?.postMessage({
      task,
      time: timeStr,
      color,
      taskColor: isFocus ? '#e0d9ff' : '#d1fae5',
      phase: isFocus ? 'focus' : 'break',
      title: timeStr,
    }, '*')
  }, [activeTimer, blocks])

  useEffect(() => {
    if (!activeTimer) {
      return
    }

    const block = blocks[activeTimer.index]
    if (!block || block.status !== 'pending') {
      setActiveTimer(null)
    }
  }, [activeTimer, blocks])

  // clean up popup on unmount
  useEffect(() => {
    return () => {
      clearInterval(intervalRef.current)
      if (popupRef.current && !popupRef.current.closed) {
        popupRef.current.close()
      }
    }
  }, [])

  function startTimer(index) {
    setActiveTimer({ index, phase: 'focus', remaining: FOCUS_SEC })
  }

  function resetTimer() {
    setActiveTimer(null)
  }

  function skipBreak() {
    setActiveTimer(current => current ? { ...current, phase: 'focus', remaining: FOCUS_SEC } : null)
  }

  function addFocusSession() {
    setActiveTimer(current => current ? { ...current, phase: 'focus', remaining: FOCUS_SEC } : null)
  }

  function completeBlock(index) {
    setActiveTimer(current => current?.index === index ? null : current)
    onAction(index, 'done')
  }

  function updateBlockStatus(index, action) {
    setActiveTimer(current => current?.index === index ? null : current)
    onAction(index, action)
  }

  return (
    <div className="timeline">
      <div className="timeline-header">
        <div>
          <h2>Today's plan</h2>
          <span className="timeline-progress">{done}/{total} done</span>
        </div>
        <button className="btn-secondary" onClick={onReset}>New day</button>
      </div>

      {blocks.map((block, i) => {
        const isBreak = block.mode === 'break'
        const isDone = block.status === 'done'
        const isSkipped = block.status === 'skip'
        const isActiveTimer = activeTimer?.index === i
        const hasOtherActiveTimer = activeTimer && !isActiveTimer

        return (
          <div
            key={i}
            className={`time-block${isBreak ? ' break' : ''}${isDone ? ' done' : ''}${isSkipped ? ' skip' : ''}`}
          >
            <div className={`mode-dot ${block.mode}`} />
            <div className="time-block-time">{block.start} – {block.end}</div>
            <div className="time-block-title">{block.task_title}</div>

            {!isBreak && !isDone && !isSkipped && (
              <div className="time-block-actions">
                {!isActiveTimer && (
                  <button className="btn-sm" onClick={() => startTimer(i)} disabled={hasOtherActiveTimer}>
                    Start 25:00
                  </button>
                )}

                {isActiveTimer && activeTimer.phase === 'focus' && (
                  <div className="pomodoro-running">
                    <span className="pomodoro-time focus">{fmt(activeTimer.remaining)}</span>
                    <button className="btn-sm" onClick={resetTimer}>
                      Reset
                    </button>
                  </div>
                )}

                {isActiveTimer && activeTimer.phase === 'break' && (
                  <div className="pomodoro-running">
                    <span className="pomodoro-time brk">Break {fmt(activeTimer.remaining)}</span>
                    <button className="btn-sm" onClick={skipBreak}>
                      Skip break
                    </button>
                  </div>
                )}

                {isActiveTimer && activeTimer.phase === 'finished' && (
                  <div className="pomodoro-running">
                    <button className="btn-sm" onClick={addFocusSession}>
                      +25:00
                    </button>
                    <button className="btn-sm done" onClick={() => completeBlock(i)}>
                      Mark done
                    </button>
                  </div>
                )}

                <button className="btn-sm skip" onClick={() => updateBlockStatus(i, 'skip')}>Skip</button>
                <button className="btn-sm delay" onClick={() => updateBlockStatus(i, 'delay')}>Delay</button>
              </div>
            )}

            {isDone && <span className="status-label done">Done</span>}
            {isSkipped && <span className="status-label skip">Skipped</span>}
          </div>
        )
      })}
    </div>
  )
}
