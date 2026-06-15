import type { NextApiRequest, NextApiResponse } from 'next'
import { jwtVerify } from 'jose'

export interface AuthUser {
  sub: string
  name: string
  email: string
  role: string
}

export async function requireAuth(
  req: NextApiRequest,
  res: NextApiResponse
): Promise<AuthUser | null> {
  const token = req.cookies['mw_session']
  if (!token) {
    res.status(401).json({ error: 'Not authenticated' })
    return null
  }
  try {
    const secret = new TextEncoder().encode(process.env.AUTH_SECRET)
    const { payload } = await jwtVerify(token, secret)
    return payload as unknown as AuthUser
  } catch {
    res.status(401).json({ error: 'Session expired — please log in again' })
    return null
  }
}
