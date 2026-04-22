import type { NextApiRequest, NextApiResponse } from 'next'
import { SignJWT } from 'jose'

// Team members allowed to log in
const TEAM = [
  {
    id: 'davide',
    name: 'Davide Duranti',
    email: 'info@medwavegroup.com',
    phone: '+27794272486',
    role: 'CEO / Strategy',
    passwordEnvKey: 'TEAM_PASSWORD_DAVIDE',
  },
  {
    id: 'francois',
    name: 'Francois',
    email: 'francois@medwavegroup.com',
    role: 'COO',
    passwordEnvKey: 'TEAM_PASSWORD_FRANCOIS',
  },
  {
    id: 'erich',
    name: 'Erich',
    email: 'erich@medwavegroup.com',
    role: 'MedWave Team',
    passwordEnvKey: 'TEAM_PASSWORD_ERICH',
  },
  {
    id: 'sterrenberg',
    name: 'Sterrenberg',
    email: 'sterrenberg@medwavegroup.com',
    role: 'MedWave Team',
    passwordEnvKey: 'TEAM_PASSWORD_STERRENBERG',
  },
  {
    id: 'hazel',
    name: 'Hazel',
    email: 'hazel@medwavegroup.com',
    role: 'Lead Scraper & Caller',
    passwordEnvKey: 'TEAM_PASSWORD_HAZEL',
  },
  {
    id: 'azola',
    name: 'Azola',
    email: 'azola@medwavegroup.com',
    role: 'Lead Scraper & Caller',
    passwordEnvKey: 'TEAM_PASSWORD_AZOLA',
  },
]

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' })

  const { email, password } = req.body

  if (!email || !password) {
    return res.status(400).json({ error: 'Email and password required' })
  }

  const member = TEAM.find(m => m.email.toLowerCase() === email.toLowerCase())
  if (!member) return res.status(401).json({ error: 'Invalid credentials' })

  const correctPassword = process.env[member.passwordEnvKey]
  if (!correctPassword || password !== correctPassword) {
    return res.status(401).json({ error: 'Invalid credentials' })
  }

  // Issue a JWT session token (24h expiry)
  const secret = new TextEncoder().encode(process.env.AUTH_SECRET)
  const token = await new SignJWT({
    sub: member.id,
    name: member.name,
    email: member.email,
    role: member.role,
  })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('24h')
    .sign(secret)

  // Set as httpOnly cookie — JS in the browser can never read this
  res.setHeader('Set-Cookie', [
    `mw_session=${token}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=86400`,
  ])

  return res.status(200).json({
    user: { id: member.id, name: member.name, email: member.email, role: member.role },
  })
}
