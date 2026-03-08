const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function post(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export function decomposeGoal(goal, workHours = '9-18', deadline = null) {
  return post('/agent/decompose', { goal, work_hours: workHours, deadline })
}

export function scheduleDay(tasks, workHours = '9-18', date = null) {
  return post('/agent/schedule', { tasks, work_hours: workHours, date })
}

export function rescheduleDay(remainingTasks, currentTime, workHours = '9-18', stateSignal = null) {
  return post('/agent/reschedule', {
    remaining_tasks: remainingTasks,
    current_time: currentTime,
    work_hours: workHours,
    state_signal: stateSignal,
  })
}
