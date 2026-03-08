import { useState } from 'react'

export default function GoalInput({ onSubmit }) {
  const [goal, setGoal] = useState('')

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (goal.trim()) onSubmit(goal.trim())
    }
  }

  return (
    <div className="goal-screen">
      <h1 className="goal-title">What do you need to do today?</h1>
      <textarea
        className="goal-textarea"
        placeholder="e.g. finish the report, prep for 3pm meeting, review pull requests"
        value={goal}
        onChange={e => setGoal(e.target.value)}
        onKeyDown={handleKeyDown}
        autoFocus
        rows={3}
      />
      <button
        className="btn-primary"
        onClick={() => goal.trim() && onSubmit(goal.trim())}
        disabled={!goal.trim()}
      >
        Plan my day
      </button>
      <p className="goal-hint">Press Enter to submit</p>
    </div>
  )
}
