import type { NextApiRequest, NextApiResponse } from 'next'
import nodemailer from 'nodemailer'
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

async function callAI(prompt: string): Promise<string> {
  const apiKey = process.env.ZAI_API_KEY!
  const res = await fetch('https://open.bigmodel.cn/api/paas/v4/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: 'glm-4.5-air',
      max_tokens: 600,
      messages: [{ role: 'user', content: prompt }],
    }),
  })
  const data = await res.json()
  return data.choices?.[0]?.message?.content ?? 'Verification unavailable'
}

async function sendEmail(lead: Lead, verifiedBrief: string) {
  const transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port: Number(process.env.SMTP_PORT),
    secure: false,
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS,
    },
  })

  const html = `
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#f9f9f9;padding:32px;border-radius:12px;">
      <div style="background:#0a0a0b;border-radius:10px;padding:20px 24px;margin-bottom:24px;">
        <span style="color:#e8ff47;font-weight:800;font-size:18px;">⚡ MedWave Agent</span>
        <span style="color:#6b6b7e;font-size:12px;margin-left:12px;">New Verified Lead</span>
      </div>

      <table style="width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;margin-bottom:20px;">
        <tr style="background:#f4f4f4;">
          <td colspan="2" style="padding:12px 16px;font-weight:700;font-size:13px;color:#0a0a0b;">LEAD PROFILE</td>
        </tr>
        ${[
          ['Name', lead.name],
          ['Practice', lead.practice],
          ['City', lead.city],
          ['Specialty', lead.specialty],
          ['Phone', lead.phone],
          ['ICP Score', `${lead.score}/100`],
          ['Status', lead.status.toUpperCase()],
          ['Source', lead.source],
        ].map(([k, v]) => `
          <tr>
            <td style="padding:10px 16px;border-bottom:1px solid #eee;font-size:12px;color:#666;width:35%;">${k}</td>
            <td style="padding:10px 16px;border-bottom:1px solid #eee;font-size:12px;font-weight:600;">${v}</td>
          </tr>
        `).join('')}
      </table>

      <div style="background:#0a0a0b;border-radius:10px;padding:20px 24px;margin-bottom:20px;">
        <div style="color:#e8ff47;font-size:11px;font-family:monospace;margin-bottom:10px;">// AI VERIFICATION REPORT</div>
        <div style="color:#e8e8f0;font-size:12px;font-family:monospace;white-space:pre-wrap;line-height:1.8;">${verifiedBrief}</div>
      </div>

      <div style="color:#888;font-size:11px;text-align:center;">
        Sent by MedWave Agent · <a href="https://medwave-agent.vercel.app" style="color:#e8ff47;">Open Dashboard</a>
      </div>
    </div>
  `

  await transporter.sendMail({
    from: `"MedWave Agent" <${process.env.SMTP_USER}>`,
    to: process.env.ALERT_EMAIL,
    subject: `🔍 Verified Lead: ${lead.name} — Score ${lead.score}/100 [${lead.status.toUpperCase()}]`,
    html,
  })
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' })

  const user = await requireAuth(req, res)
  if (!user) return

  const lead: Lead = req.body.lead
  if (!lead) return res.status(400).json({ error: 'lead required' })

  try {
    // Step 1: AI multi-source verification
    const verifyPrompt = `You are verifying a South African healthcare lead for MedWave PBM device sales.

Lead data (scraped from Google Maps):
Name: ${lead.name}
Practice: ${lead.practice}
City: ${lead.city}
Specialty: ${lead.specialty}
Phone: ${lead.phone}
ICP Score: ${lead.score}/100

Cross-check this lead against:
1. HPCSA registration — is this specialty regulated in South Africa?
2. Typical practice profile for this specialty and city
3. Contact reliability for this practice type
4. LinkedIn / web presence signals
5. Any red flags or verification concerns

Respond in this exact format:
VERIFICATION STATUS: [CONFIRMED / NEEDS MANUAL CHECK / FLAGGED]
CONFIDENCE: [0-100]%
HPCSA REGULATED: [Yes/No]
CONTACT RELIABILITY: [High/Medium/Low]
RECOMMENDED ACTION: [one sentence]
NOTES: [2-3 lines Davide should know before calling]
EMAIL SUBJECT: [suggested cold email subject line]
EMAIL OPENER: [first 2 sentences of personalised cold outreach]`

    const verifiedBrief = await callAI(verifyPrompt)

    // Step 2: Email Davide the full brief
    await sendEmail(lead, verifiedBrief)

    return res.status(200).json({ ok: true, brief: verifiedBrief })
  } catch (err) {
    console.error('Verify error:', err)
    return res.status(500).json({ error: 'Verification failed' })
  }
}
