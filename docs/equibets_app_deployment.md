# equibets.app deployment

`equibets.app` is the production domain for the Equibets static web app and PWA.

## Recommended first launch

Use Vercel, Netlify, or Cloudflare Pages as a static frontend host.

| Setting | Value |
| --- | --- |
| Build command | `npm ci && npm run build` |
| Output directory | `dist` |
| Production domain | `equibets.app` |
| WWW redirect | `www.equibets.app` -> `equibets.app` |

## DNS records

Pick the records requested by the host. Common examples:

### Vercel

- Apex `A`: `76.76.21.21`
- `www` `CNAME`: `cname.vercel-dns.com`

### Netlify

- Apex `A`: `75.2.60.5`
- `www` `CNAME`: the Netlify site hostname

### Cloudflare Pages

- Apex `CNAME`: the Pages hostname, proxied through Cloudflare
- `www` `CNAME`: the Pages hostname, proxied through Cloudflare

## Required launch checks

Run these before promoting a deploy:

```bash
npm test
npm run build
python3 -m unittest discover -s tests
```

After DNS is live:

1. Visit `https://equibets.app`.
2. Confirm HTTPS is active.
3. Confirm `https://equibets.app/manifest.webmanifest` loads.
4. Confirm `https://equibets.app/robots.txt` and `https://equibets.app/sitemap.xml` load.
5. In Chrome DevTools, confirm the service worker registers on HTTPS.
6. Confirm install prompts use the Equibets app name and icon.

## Compliance boundary

Launch `equibets.app` only as legal analytics, horse data, score tracking, and
free-play prediction markets. Do not add deposits, withdrawals, paid betting
odds, staking, or real-money settlement until legal advice and all required
gambling licences are in place.
