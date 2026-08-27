const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'https://metgo-backend.onrender.com').replace(/\/$/, '')

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })

  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      detail = body.detail || detail
    } catch (_) {}
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  return response.json()
}

export const api = {
  baseUrl: API_BASE,
  health: () => request('/health'),
  generatePlan: () => request('/plan/generate', { method: 'POST' }),
  whatIf: (override) => request('/plan/what-if', {
    method: 'POST',
    body: JSON.stringify({ override }),
  }),
  explain: (planId, trainId) => request(`/plan/${encodeURIComponent(planId)}/explain/${encodeURIComponent(trainId)}`),
  trains: () => request('/trains/'),
  train: (trainId) => request(`/trains/${encodeURIComponent(trainId)}`),
}

export function normalizeTrain(summary, detail) {
  const cert = [...(detail?.fitness_certs || [])].sort((a, b) =>
    String(a.expiry_date).localeCompare(String(b.expiry_date))
  )[0]
  const branding = detail?.branding_contracts?.[0]

  return {
    train_id: summary.train_id,
    status: summary.status,
    current_bay: summary.current_bay_id,
    mileage: Number(summary.mileage_km || 0),
    coach_count: summary.coach_count,
    fitness_cert_expiry: cert?.expiry_date || null,
    fitness_days: cert?.days_to_expiry ?? null,
    fitness_expired: cert?.is_expired ?? false,
    fitness_expiring_soon: cert?.is_expiring_soon ?? false,
    job_cards: detail?.job_cards || [],
    cleaning_due: Boolean(detail?.cleaning_due),
    branding_hours_target: Number(branding?.hours_target || 0),
    branding_hours_delivered: Number(branding?.hours_delivered || 0),
  }
}
