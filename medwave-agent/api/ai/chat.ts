import type { NextApiRequest, NextApiResponse } from 'next'
import { requireAuth } from '@/lib/auth'

const SYSTEM_PROMPT = `You are the MedWave Agent — a smart business assistant for the MedWave Group team in South Africa.
MedWave sells photobiomodulation (PBM) therapy devices (635nm and 810nm) to healthcare practitioners in SA and the USA.

TEAM:
- Davide Duranti — CEO / Strategy (info@medwavegroup.com, +27794272486)
- Francois — COO, oversees operations and team performance (francois@medwavegroup.com)
- Erich — MedWave Team (erich@medwavegroup.com)
- Sterrenberg — MedWave Team (sterrenberg@medwavegroup.com)
- Hazel — Lead Scraper & Caller (hazel@medwavegroup.com)
- Azola — Lead Scraper & Caller (azola@medwavegroup.com)

TASK ASSIGNMENT LOGIC:
- Scraping & calling tasks → Hazel or Azola
- Operations & process tasks → Francois
- Strategy & high-value closes → Davide
- General team tasks → Erich or Sterrenberg

BUSINESS CONTEXT:
Current focus: scaling cold outreach 100→1000 leads/day via Google Maps scraping (OpenClaw).
ICP: 80% women buyers, Wellness/Holistic 33%, Gauteng 32%, Western Cape 26%.
Sales sequence: Science → Demo → Close. Website leads close 3x faster than Facebook leads.
When asked to create tasks, format as numbered list with [NAME] prefixes using real team member names.
When asked to draft a dispatch, write crisp action-oriented messages under 100 words.
Keep responses concise and operational.`

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' })

  const user = await requireAuth(req, res)
  if (!user) return // requireAuth already sent 401

  const { message, history = [] } = req.body
  if (!message) return res.status(400).json({ error: 'message required' })

  const apiKey = process.env.ZAI_API_KEY
  if (!apiKey) return res.status(500).json({ error: 'AI service not configured' })

  try {
    const response = await fetch('https://open.bigmodel.cn/api/paas/v4/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: 'glm-4.5-air',
        max_tokens: 800,
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          ...history,
          { role: 'user', content: message },
        ],
      }),
    })

    const data = await response.json()
    if (!response.ok) {
      return res.status(502).json({ error: data.error?.message || 'AI error' })
    }

    return res.status(200).json({
      reply: data.choices?.[0]?.message?.content ?? 'No response',
    })
  } catch (err) {
    console.error('AI chat error:', err)
    return res.status(500).json({ error: 'Failed to reach AI service' })
  }
}
