// AI prompt input component for IDES 2.0 enabling natural language queries about sensor data with smart suggestions and real-time processing for chart generation and insights.

import React, { useState } from 'react'
import { Send, Brain, Loader } from 'lucide-react'

interface PromptInputProps {
  onSubmit: (prompt: string) => Promise<void>
}

const PromptInput: React.FC<PromptInputProps> = ({ onSubmit }) => {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim() || loading) return

    setLoading(true)
    try {
      await onSubmit(prompt.trim())
      setPrompt('')
    } catch (error) {
      console.error('Failed to submit prompt:', error)
    } finally {
      setLoading(false)
    }
  }

  const suggestions = [
    "Show me today's temperature and humidity",
    "Compare CO₂ levels over the last week",
    "Forecast temperature for the next 24 hours",
    "What's the air quality trend?",
    "Create a chart showing all metrics",
    "Are there any concerning patterns?"
  ]

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4">
      <div className="flex items-center mb-3">
        <Brain className="h-5 w-5 text-blue-600 mr-2" />
        <h3 className="text-lg font-semibold text-gray-900">AI Assistant</h3>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="relative">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Ask me anything about your sensor data..."
            className="form-textarea w-full h-20 pr-12 resize-none"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!prompt.trim() || loading}
            className="absolute bottom-2 right-2 p-2 bg-blue-600 text-white rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
          >
            {loading ? (
              <Loader className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* Quick suggestions */}
        <div className="flex flex-wrap gap-2">
          {suggestions.map((suggestion, index) => (
            <button
              key={index}
              type="button"
              onClick={() => setPrompt(suggestion)}
              className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
              disabled={loading}
            >
              {suggestion}
            </button>
          ))}
        </div>
      </form>

      <div className="mt-3 text-xs text-gray-500">
        💡 Try asking about trends, forecasts, or request specific charts
      </div>
    </div>
  )
}

export default PromptInput