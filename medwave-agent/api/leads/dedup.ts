import type { NextApiRequest, NextApiResponse } from 'next'
import { requireAuth } from '@/lib/auth'

interface Lead {
  id: number
  name: string
  practice: string
  city: string
  specialty: string
  phone: string
  score: number
  status: string
  source: string
}

interface DedupResult {
  newLeads: Lead[]
  crmLeads: Lead[]
  log: string[]
}

async function checkInGHL(lead: Lead): Promise<boolean> {
  const apiKey = process.env.GHL_API_KEY
  const locationId = process.env.GHL_LOCATION_ID
  if (!apiKey || !locationId) return false

  const headers = {
    'Authorization': `Bearer ${apiKey}`,
    'Version': '2021-07-28',
    'Content-Type': 'application/json',
  }

  // Search by name first, then by phone if name has no results
  const queries = [
    `https://services.leadconnectorhq.com/contacts/?locationId=${locationId}&query=${encodeURIComponent(lead.name)}&limit=5`,
    `https://services.leadconnectorhq.com/contacts/?locationId=${locationId}&query=${encodeURIComponent(lead.phone.replace(/\s+/g, ''))}&limit=5`,
  ]

  for (const url of queries) {
    try {
      const res = await fetch(url, { headers })
      if (!res.ok) continue
      const data = await res.json()
      const contacts: unknown[] = data.contacts ?? []
      if (contacts.length > 0) return true
    } catch {
      // If GHL unreachable, fail open (keep lead in pipeline)
      continue
    }
  }
  return false
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' })

  const user = await requireAuth(req, res)
  if (!user) return

  const { leads }: { leads: Lead[] } = req.body
  if (!Array.isArray(leads)) return res.status(400).json({ error: 'leads array required' })

  const result: DedupResult = { newLeads: [], crmLeads: [], log: [] }
  result.log.push(`Starting CRM dedup for ${leads.length} leads against GoHighLevel…`)

  for (const lead of leads) {
    result.log.push(`Checking: ${lead.name} (${lead.phone})`)
    const inCRM = await checkInGHL(lead)

    if (inCRM) {
      result.crmLeads.push(lead)
      result.log.push(`✓ IN CRM: ${lead.name} — moved to "In CRM Already"`)
    } else {
      result.newLeads.push(lead)
      result.log.push(`✦ NEW: ${lead.name} — kept in pipeline`)
    }

    // Small delay to respect GHL rate limits (100 req/10s)
    await new Promise(r => setTimeout(r, 150))
  }

  result.log.push('')
  result.log.push(
    `✅ Done: ${result.newLeads.length} new leads | ${result.crmLeads.length} already in CRM`
  )

  return res.status(200).json(result)
}
