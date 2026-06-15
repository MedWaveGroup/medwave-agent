import type { NextApiRequest, NextApiResponse } from 'next'
import nodemailer from 'nodemailer'
import { requireAuth } from '@/lib/auth'

const TEAM = [
  { id: 'davide',      name: 'Davide Duranti', email: 'info@medwavegroup.com' },
  { id: 'francois',   name: 'Francois',        email: 'francois@medwavegroup.com' },
  { id: 'erich',      name: 'Erich',           email: 'erich@medwavegroup.com' },
  { id: 'sterrenberg',name: 'Sterrenberg',     email: 'sterrenberg@medwavegroup.com' },
  { id: 'hazel',      name: 'Hazel',           email: 'hazel@medwavegroup.com' },
  { id: 'azola',      name: 'Azola',           email: 'azola@medwavegroup.com' },
]

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' })

  const user = await requireAuth(req, res)
  if (!user) return

  const { recipientIds, subject, body } = req.body
  if (!recipientIds?.length || !body) {
    return res.status(400).json({ error: 'recipientIds and body required' })
  }

  const recipients = TEAM.filter(m => recipientIds.includes(m.id))
  if (recipients.length === 0) return res.status(400).json({ error: 'No valid recipients' })

  const toAddresses = recipients.map(r => `${r.name} <${r.email}>`).join(', ')

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
      <div style="background:#0a0a0b;border-radius:10px;padding:16px 24px;margin-bottom:20px;">
        <span style="color:#e8ff47;font-weight:800;">⚡ MedWave Agent</span>
        <span style="color:#6b6b7e;font-size:12px;margin-left:12px;">Team Dispatch from ${user.name}</span>
      </div>
      <div style="background:white;border-radius:10px;padding:24px;font-size:14px;line-height:1.8;color:#333;white-space:pre-wrap;">${body}</div>
      <div style="margin-top:16px;color:#888;font-size:11px;text-align:center;">
        Sent via MedWave Agent · <a href="https://medwave-agent.vercel.app" style="color:#e8ff47;">Open Dashboard</a>
      </div>
    </div>
  `

  await transporter.sendMail({
    from: `"MedWave Agent" <${process.env.SMTP_USER}>`,
    to: toAddresses,
    subject: subject || `📤 MedWave Team Update from ${user.name}`,
    html,
  })

  return res.status(200).json({ ok: true, sent_to: recipients.map(r => r.email) })
}
