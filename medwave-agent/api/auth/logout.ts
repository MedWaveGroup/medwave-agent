import type { NextApiRequest, NextApiResponse } from 'next'

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  res.setHeader('Set-Cookie', 'mw_session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0')
  return res.status(200).json({ ok: true })
}
