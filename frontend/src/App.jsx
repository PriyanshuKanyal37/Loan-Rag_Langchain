import { useCallback, useEffect, useMemo, useState } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import './App.css'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') || 'http://127.0.0.1:8000'

const ALLOWED_HTML_TAGS = [
  'H1',
  'H2',
  'H3',
  'H4',
  'P',
  'BR',
  'HR',
  'STRONG',
  'EM',
  'CODE',
  'UL',
  'OL',
  'LI',
  'BLOCKQUOTE',
  'TABLE',
  'THEAD',
  'TBODY',
  'TR',
  'TH',
  'TD',
]

const ALLOWED_HTML_ATTRS = {
  td: ['colspan', 'rowspan', 'align'],
  th: ['colspan', 'rowspan', 'align'],
  a: ['href', 'title'],
}

marked.setOptions({ gfm: true, breaks: true })

const sanitiseFormValues = (values, fieldTypes = {}) => {
  const payload = {}
  Object.entries(values || {}).forEach(([key, value]) => {
    if (value === undefined || value === null) return
    const fieldType = fieldTypes[key]

    // Handle calculated fields - always send as numbers
    if (fieldType === 'calculated') {
      const numValue = typeof value === 'number' ? value : parseFloat(value) || 0
      payload[key] = numValue
      return
    }

    if (fieldType === 'multiselect' && Array.isArray(value)) {
      if (!value.length) return
      payload[key] = value.join(', ')
      return
    }
    if (fieldType === 'repeater') {
      if (!Array.isArray(value) || value.length === 0) return
      // Keep only items that have at least one non-empty field
      const cleaned = value
        .map((item) => {
          const out = {}
          Object.entries(item || {}).forEach(([k, v]) => {
            if (v === undefined || v === null) return
            if (typeof v === 'string') {
              const t = v.trim()
              if (!t) return
              out[k] = t
              return
            }
            out[k] = v
          })
          return out
        })
        .filter((obj) => Object.keys(obj).length > 0)
      if (cleaned.length) payload[key] = cleaned
      return
    }
    if (typeof value === 'string') {
      const trimmed = value.trim()
      if (!trimmed) return
      payload[key] = trimmed
      return
    }
    payload[key] = value
  })
  return payload
}

function App() {
  const [templates, setTemplates] = useState([])
  const [selectedForm, setSelectedForm] = useState('')
  const [formValues, setFormValues] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const renderedHtml = useMemo(() => {
    const rawHtml = result?.response_html
    if (rawHtml) {
      return DOMPurify.sanitize(rawHtml, {
        ALLOWED_TAGS: ALLOWED_HTML_TAGS,
        ALLOWED_ATTR: ALLOWED_HTML_ATTRS,
        USE_PROFILES: { html: true },
      })
    }

    const rawMarkdown = result?.response_markdown ?? result?.response
    if (!rawMarkdown) return ''

    const normalised = rawMarkdown.replace(/\r\n/g, '\n')
    const html = marked.parse(normalised)
    if (import.meta.env.DEV) {
      console.debug('[renderedHtml]', html)
    }
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: ALLOWED_HTML_TAGS,
      ALLOWED_ATTR: ALLOWED_HTML_ATTRS,
      USE_PROFILES: { html: true },
    })
  }, [result])

  useEffect(() => {
    const controller = new AbortController()

    const loadTemplates = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/form-templates`, {
          signal: controller.signal,
        })
        if (!response.ok) {
          throw new Error('Unable to load form templates.')
        }
        const data = await response.json()
        const forms = data.forms || []
        setTemplates(forms)
        if (forms.length) {
          setSelectedForm(forms[0].id)
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Failed to load form templates.')
        }
      }
    }

    loadTemplates()
    return () => controller.abort()
  }, [])

  const activeTemplate = useMemo(
    () => templates.find((template) => template.id === selectedForm),
    [templates, selectedForm]
  )

  const fieldTypeMap = useMemo(() => {
    if (!activeTemplate) return {}
    const map = {}
    activeTemplate.sections.forEach((section) =>
      section.fields.forEach((field) => {
        map[field.key] = field.type
      })
    )
    return map
  }, [activeTemplate])

  useEffect(() => {
    if (!activeTemplate) {
      setFormValues({})
      return
    }
    const initial = {}
    activeTemplate.sections.forEach((section) =>
      section.fields.forEach((field) => {
        if (field.type === 'multiselect') {
          initial[field.key] = []
        } else if (field.type === 'repeater') {
          initial[field.key] = []
        } else {
          initial[field.key] = ''
        }
      })
    )
    setFormValues(initial)
  }, [activeTemplate])

  const handleFieldChange = (key, value) => {
    setFormValues((prev) => ({
      ...prev,
      [key]: value,
    }))
  }

  const calculateFieldValue = useCallback((field) => {
    if (!field.formula) return '0.00'

    const formula = field.formula
    let sum = 0

    // Handle sum of regular fields
    if (formula.fields && Array.isArray(formula.fields)) {
      formula.fields.forEach((fieldKey) => {
        const val = parseFloat(formValues[fieldKey]) || 0
        sum += val
      })
    }

    // Handle sum of repeater subfields
    if (formula.repeaters && Array.isArray(formula.repeaters)) {
      formula.repeaters.forEach((repeaterConfig) => {
        const repeaterKey = repeaterConfig.key
        const subKey = repeaterConfig.subKey
        const repeaterArray = formValues[repeaterKey]

        if (Array.isArray(repeaterArray)) {
          repeaterArray.forEach((item) => {
            const val = parseFloat(item?.[subKey]) || 0
            sum += val
          })
        }
      })
    }

    // Handle ratio calculations (for LVR, etc.)
    if (formula.type === 'ratio') {
      let numerator = 0
      let denominator = 0

      if (formula.numerator_fields && Array.isArray(formula.numerator_fields)) {
        formula.numerator_fields.forEach((fieldKey) => {
          const val = parseFloat(formValues[fieldKey]) || 0
          numerator += val
        })
      }

      if (formula.denominator_field) {
        denominator = parseFloat(formValues[formula.denominator_field]) || 0
      }

      if (denominator === 0) return '0.00'

      const ratio = (numerator / denominator) * (formula.multiplier || 1)
      const decimals = formula.decimals !== undefined ? formula.decimals : 2
      return ratio.toFixed(decimals)
    }

    // Default: return sum
    const decimals = formula.decimals !== undefined ? formula.decimals : 2
    return sum.toFixed(decimals)
  }, [formValues])

  const handleSubmit = useCallback(
    async (event) => {
      event.preventDefault()
      setError('')

      if (!selectedForm) {
        setError('Please choose a scenario before submitting.')
        return
      }

      setLoading(true)
      setResult(null)

      try {
        // Calculate all calculated fields and add to formValues
        const enrichedFormValues = { ...formValues }

        if (activeTemplate) {
          activeTemplate.sections.forEach((section) => {
            section.fields.forEach((field) => {
              if (field.type === 'calculated') {
                const calculatedValue = calculateFieldValue(field)
                enrichedFormValues[field.key] = parseFloat(calculatedValue) || 0
              }
            })
          })
        }

        const sanitizedData = sanitiseFormValues(enrichedFormValues, fieldTypeMap)

        const payload = {
          form_type: selectedForm,
          form_data: sanitizedData,
          applicants: [],
        }

        // Debug log to verify data
        if (import.meta.env.DEV) {
          console.log('Form Data Being Sent:', sanitizedData)
          console.log('Full Payload:', payload)
        }

        const response = await fetch(`${API_BASE_URL}/ask`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })

        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`)
        }

        const data = await response.json()
        setResult(data)
      } catch (err) {
        setError(err.message || 'Something went wrong while contacting the assistant.')
      } finally {
        setLoading(false)
      }
    },
    [selectedForm, formValues, fieldTypeMap, activeTemplate, calculateFieldValue]
  )

  const renderField = (field) => {
    const value = formValues[field.key] ?? ''

    // Handle calculated fields
    if (field.type === 'calculated') {
      const calculatedValue = calculateFieldValue(field)

      // Format number with commas for display
      const numValue = parseFloat(calculatedValue) || 0
      const formattedValue = numValue.toLocaleString('en-AU', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })

      return (
        <div key={field.key} className="field calculated-field">
          <span>{field.label}</span>
          <div className="calculated-value">
            {field.suffix ? `${formattedValue} ${field.suffix}` : formattedValue}
          </div>
        </div>
      )
    }

    if (field.type === 'repeater') {
      const items = Array.isArray(value) ? value : []
      const max = field.max ?? 10
      const typeField = field.fields?.find((f) => f.key === 'type' && Array.isArray(f.options) && f.options.length)

      const updateItem = (index, subKey, subValue) => {
        const next = Array.isArray(value) ? [...value] : []
        next[index] = { ...(next[index] || {}) , [subKey]: subValue }
        handleFieldChange(field.key, next)
      }

      // If a type selector exists, drive items by selected types (chips)
      if (typeField) {
        const selected = items.map((it) => it?.type).filter(Boolean)
        const addType = (opt) => {
          if (!opt) return
          if (selected.includes(opt)) return
          if (items.length >= max) return
          const obj = {}
          field.fields?.forEach((f) => {
            if (f.key === 'type') {
              obj[f.key] = opt
            } else {
              obj[f.key] = f.type === 'multiselect' ? [] : ''
            }
          })
          handleFieldChange(field.key, [...items, obj])
        }
        const removeType = (opt) => {
          const next = items.filter((it) => it?.type !== opt)
          handleFieldChange(field.key, next)
        }

        return (
          <div key={field.key} className="field repeater">
            <span>{field.label}</span>
            <div className="repeater-controls">
              <select
                value=""
                onChange={(e) => {
                  addType(e.target.value)
                  e.target.value = ''
                }}
              >
                <option value="">{typeField.placeholder || 'Select one or more types'}</option>
                {typeField.options
                  .filter((opt) => !selected.includes(opt))
                  .map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
              </select>
              {selected.length > 0 && (
                <div className="chips">
                  {selected.map((opt) => (
                    <span key={opt} className="chip">
                      {opt}
                      <button type="button" className="chip-x" onClick={() => removeType(opt)}>
                        x
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {items.map((item, idx) => (
              <fieldset key={idx} className="repeater-item">
                <legend>{`${field.itemLabel || 'Item'} ${idx + 1} â€” ${item?.type || ''}`}</legend>
                <div className="repeater-grid">
                  {field.fields?.map((sub) => {
                    // Hide the type subfield; it is controlled by chips above
                    if (sub.key === 'type') return null
                    const subVal = (item || {})[sub.key] ?? (sub.type === 'multiselect' ? [] : '')
                    if (sub.type === 'multiselect') {
                      return (
                        <label key={sub.key} className="field">
                          <span>{sub.label}</span>
                          <select
                            multiple
                            value={Array.isArray(subVal) ? subVal : []}
                            onChange={(event) =>
                              updateItem(
                                idx,
                                sub.key,
                                Array.from(event.target.selectedOptions, (o) => o.value),
                              )
                            }
                          >
                            {sub.options?.map((option) => (
                              <option key={option} value={option}>
                                {option}
                              </option>
                            ))}
                          </select>
                        </label>
                      )
                    }
                    if (sub.type === 'select') {
                      return (
                        <label key={sub.key} className="field">
                          <span>{sub.label}</span>
                          <select
                            value={subVal}
                            onChange={(e) => updateItem(idx, sub.key, e.target.value)}
                          >
                            <option value="">{sub.placeholder || 'Select an option'}</option>
                            {sub.options?.map((option) => (
                              <option key={option} value={option}>
                                {option}
                              </option>
                            ))}
                          </select>
                        </label>
                      )
                    }
                    if (sub.type === 'number') {
                      return (
                        <label key={sub.key} className="field">
                          <span>{sub.label}</span>
                          <input
                            type="number"
                            value={subVal}
                            placeholder={sub.placeholder || ''}
                            onChange={(e) => updateItem(idx, sub.key, e.target.value)}
                            min={sub.min}
                            max={sub.max}
                            step={sub.step || 'any'}
                          />
                        </label>
                      )
                    }
                    return (
                      <label key={sub.key} className="field">
                        <span>{sub.label}</span>
                        <input
                          type="text"
                          value={subVal}
                          placeholder={sub.placeholder || ''}
                          onChange={(e) => updateItem(idx, sub.key, e.target.value)}
                        />
                      </label>
                    )
                  })}
                </div>
              </fieldset>
            ))}
          </div>
        )
      }

      // Fallback: simple add/remove by count when no type selector exists
      const count = items.length
      const min = field.min ?? 0
      const fallbackSetCount = (nextCount) => {
        const n = Math.max(min, Math.min(field.max ?? 10, nextCount))
        const next = [...items]
        if (n > next.length) {
          while (next.length < n) {
            const obj = {}
            field.fields?.forEach((f) => {
              obj[f.key] = f.type === 'multiselect' ? [] : ''
            })
            next.push(obj)
          }
        } else if (n < next.length) {
          next.length = n
        }
        handleFieldChange(field.key, next)
      }

      return (
        <div key={field.key} className="field repeater">
          <div className="repeater-header">
            <span>{field.label}</span>
            <label className="repeater-count">
              <span>Count</span>
              <input
                type="number"
                min={min}
                max={field.max ?? 10}
                value={count}
                onChange={(e) => fallbackSetCount(Number(e.target.value || 0))}
              />
            </label>
          </div>
          {items.map((item, idx) => (
            <fieldset key={idx} className="repeater-item">
              <legend>{`${field.itemLabel || 'Item'} ${idx + 1}`}</legend>
              <div className="repeater-grid">
                {field.fields?.map((sub) => {
                  const subVal = (item || {})[sub.key] ?? (sub.type === 'multiselect' ? [] : '')
                  if (sub.type === 'multiselect') {
                    return (
                      <label key={sub.key} className="field">
                        <span>{sub.label}</span>
                        <select
                          multiple
                          value={Array.isArray(subVal) ? subVal : []}
                          onChange={(event) =>
                            updateItem(
                              idx,
                              sub.key,
                              Array.from(event.target.selectedOptions, (o) => o.value),
                            )
                          }
                        >
                          {sub.options?.map((option) => (
                            <option key={option} value={option}>
                              {option}
                            </option>
                          ))}
                        </select>
                      </label>
                    )
                  }
                  if (sub.type === 'select') {
                    return (
                      <label key={sub.key} className="field">
                        <span>{sub.label}</span>
                        <select
                          value={subVal}
                          onChange={(e) => updateItem(idx, sub.key, e.target.value)}
                        >
                          <option value="">{sub.placeholder || 'Select an option'}</option>
                          {sub.options?.map((option) => (
                            <option key={option} value={option}>
                              {option}
                            </option>
                          ))}
                        </select>
                      </label>
                    )
                  }
                  if (sub.type === 'number') {
                    return (
                      <label key={sub.key} className="field">
                        <span>{sub.label}</span>
                        <input
                          type="number"
                          value={subVal}
                          placeholder={sub.placeholder || ''}
                          onChange={(e) => updateItem(idx, sub.key, e.target.value)}
                          min={sub.min}
                          max={sub.max}
                          step={sub.step || 'any'}
                        />
                      </label>
                    )
                  }
                  return (
                    <label key={sub.key} className="field">
                      <span>{sub.label}</span>
                      <input
                        type="text"
                        value={subVal}
                        placeholder={sub.placeholder || ''}
                        onChange={(e) => updateItem(idx, sub.key, e.target.value)}
                      />
                    </label>
                  )
                })}
              </div>
            </fieldset>
          ))}
        </div>
      )
    }

    if (field.type === 'multiselect') {
      const selected = Array.isArray(value) ? value : []
      const options = field.options || []

      const addSelection = (opt) => {
        if (!opt) return
        if (selected.includes(opt)) return
        handleFieldChange(field.key, [...selected, opt])
      }
      const removeSelection = (opt) => {
        handleFieldChange(field.key, selected.filter((v) => v !== opt))
      }

      return (
        <div key={field.key} className="field">
          <span>{field.label}</span>
          <div className="multiselect-dropdown">
            <select
              value=""
              onChange={(e) => {
                addSelection(e.target.value)
                e.target.value = ''
              }}
            >
              <option value="">{field.placeholder || 'Select one or more'}</option>
              {options
                .filter((opt) => !selected.includes(opt))
                .map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
            </select>
          </div>
          {selected.length > 0 && (
            <div className="chips">
              {selected.map((opt) => (
                <span key={opt} className="chip">
                  {opt}
                  <button type="button" className="chip-x" onClick={() => removeSelection(opt)}>
                    x
                  </button>
                </span>
              ))}
              <button type="button" className="chip-clear" onClick={() => handleFieldChange(field.key, [])}>
                Clear
              </button>
            </div>
          )}
        </div>
      )
    }

    if (field.type === 'select') {
      return (
        <label key={field.key} className="field">
          <span>{field.label}</span>
          <select
            value={value}
            onChange={(event) => handleFieldChange(field.key, event.target.value)}
          >
            <option value="">{field.placeholder || 'Select an option'}</option>
            {field.options?.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      )
    }

    if (field.type === 'number') {
      return (
        <label key={field.key} className="field">
          <span>{field.label}</span>
          <input
            type="number"
            value={value}
            placeholder={field.placeholder || ''}
            onChange={(event) => handleFieldChange(field.key, event.target.value)}
            min={field.min}
            max={field.max}
            step={field.step || 'any'}
          />
        </label>
      )
    }

    if (field.type === 'boolean') {
      const boolValue = value === true || value === 'true' || value === 'Yes'
      return (
        <div key={field.key} className="field checkbox-field">
          <label className="checkbox-container">
            <input
              type="checkbox"
              checked={boolValue}
              onChange={(event) => handleFieldChange(field.key, event.target.checked)}
            />
            <span className="checkbox-label">{field.label}</span>
            <span className="checkmark"></span>
          </label>
        </div>
      )
    }

    if (field.type === 'text') {
      return (
        <label key={field.key} className="field">
          <span>{field.label}</span>
          <input
            type="text"
            value={value}
            placeholder={field.placeholder || ''}
            onChange={(event) => handleFieldChange(field.key, event.target.value)}
          />
        </label>
      )
    }

    return (
      <label key={field.key} className="field">
        <span>{field.label}</span>
        <textarea
          rows={field.rows || 4}
          value={value}
          placeholder={field.placeholder || ''}
          onChange={(event) => handleFieldChange(field.key, event.target.value)}
        />
      </label>
    )
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar__copy">
          <h1 className="topbar__title">Loan Intelligence Assistant</h1>
          <p className="topbar__subtitle">
            Build lender-ready credit proposals grounded in your client fact find and policy PDFs.
          </p>
        </div>
        <div className="topbar__badges">
          {loading ? (
            <span className="badge badge--pulse">Drafting response…</span>
          ) : renderedHtml ? (
            <span className="badge badge--success">Proposal ready</span>
          ) : (
            <span className="badge">Awaiting input</span>
          )}
        </div>
      </header>

      <main className="workspace">
        <section className="workspace__panel workspace__panel--form">
          <form className="panel form-panel" onSubmit={handleSubmit}>
            <div className="panel__header">
              <h2>Scenario Builder</h2>
              <p>Select a template and capture the fact-find essentials needed for the proposal.</p>
            </div>

            <div className="form-section">
              <h3 className="form-section__title">Step 1 · Choose the loan scenario</h3>
              <div className="scenario-grid">
                {templates.map((template) => (
                  <button
                    type="button"
                    key={template.id}
                    className={template.id === selectedForm ? 'scenario selected' : 'scenario'}
                    onClick={() => setSelectedForm(template.id)}
                  >
                    <span className="scenario-label">{template.label}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="form-section">
              <h3 className="form-section__title">Step 2 · Capture the fact-find highlights</h3>
              {activeTemplate ? (
                <div className="fields">
                  {activeTemplate.sections.map((section) => (
                    <section className="section-block" key={section.title}>
                      <h4>{section.title}</h4>
                      {section.fields.map((field) => renderField(field))}
                    </section>
                  ))}
                </div>
              ) : (
                <p className="placeholder">Select a scenario to unlock the tailored fact-find inputs.</p>
              )}
            </div>

            <div className="form-actions">
              <button type="submit" disabled={loading}>
                {loading ? 'Generating...' : 'Generate Credit Proposal'}
              </button>
            </div>
          </form>

          {error && <div className="alert alert--error">{error}</div>}
          {loading && !error && (
            <div className="alert alert--info">Retrieving policy snippets and drafting the proposal…</div>
          )}
        </section>

        <section className="workspace__panel workspace__panel--result">
          {renderedHtml ? (
            <div className="panel result-panel">
              <div className="panel__header">
                <h2>Generated Credit Proposal</h2>
                <div className="panel__meta">
                  {result.form_type && <span>Scenario: {result.form_type.replace(/_/g, ' ')}</span>}
                </div>
              </div>
              <div
                className="result-view"
                dangerouslySetInnerHTML={{
                  __html: renderedHtml,
                }}
              />
            </div>
          ) : (
            <div className="panel panel--empty">
              <h2>Proposal Preview</h2>
              <p>Complete the scenario form to generate a lender-ready credit proposal with sourced policies.</p>
              <ul>
                <li>Select the loan type that matches your client.</li>
                <li>Capture the key fact-find details requested in each section.</li>
                <li>Submit to draft the HTML credit proposal with document citations.</li>
              </ul>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default App




