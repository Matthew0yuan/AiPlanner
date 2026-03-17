import { useState } from 'react'
import GoalInput from './components/GoalInput'
import Timeline from './components/Timeline'
import WorkHoursBar from './components/WorkHoursBar'
import { decomposeGoal, scheduleDay, rescheduleDay } from './api'
import './App.css'

function defaultWorkHours() {
  const h = new Date().getHours()
  if (h >= 23) {
    return '9-17'
  }
  const end = Math.min(h + 8, 23)
  if (end <= h) {
    return '9-17'
  }
  return `${h}-${end}`
}

export default function App() {
  const [step, setStep] = useState('goal')
  const [blocks, setBlocks] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [workHours, setWorkHours] = useState(defaultWorkHours)

  async function handleGoalSubmit(goal) {
    setLoading(true)
    setError(null)
    try {
      const { tasks } = await decomposeGoal(goal, workHours)
      const { blocks: scheduled } = await scheduleDay(tasks, workHours)
      setBlocks(scheduled.map(b => ({ ...b, status: 'pending' })))
      setStep('timeline')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleDelay(blockIndex) {
    const now = new Date()
    const currentTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
    const remainingTasks = blocks
      .slice(blockIndex)
      .filter(b => b.status === 'pending' && b.mode !== 'break')
      .map(b => ({ task_title: b.task_title, mode: b.mode }))

    if (!remainingTasks.length) return
    setLoading(true)
    setError(null)
    try {
      const { blocks: rescheduled } = await rescheduleDay(remainingTasks, currentTime, workHours)
      setBlocks(prev => [
        ...prev.slice(0, blockIndex),
        ...rescheduled.map(b => ({ ...b, status: 'pending' })),
      ])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleBlockAction(index, action) {
    if (action === 'delay') {
      handleDelay(index)
    } else {
      setBlocks(prev => prev.map((b, i) => i === index ? { ...b, status: action } : b))
    }
  }

  return (
    <div className={`app ${step === 'goal' ? 'centered' : ''}`}>
      {error && <div className="error">{error}</div>}

      {loading && (
        <div className="loading-screen">
          <div className="loading-text">Planning your day...</div>
        </div>
      )}

      {!loading && step === 'goal' && (
        <div className="goal-wrapper">
          <WorkHoursBar workHours={workHours} onChange={setWorkHours} />
          <GoalInput onSubmit={handleGoalSubmit} />
        </div>
      )}

      {!loading && step === 'timeline' && (
        <Timeline
          blocks={blocks}
          onAction={handleBlockAction}
          onReset={() => { setStep('goal'); setBlocks([]) }}
        />
      )}
    </div>
  )
}
