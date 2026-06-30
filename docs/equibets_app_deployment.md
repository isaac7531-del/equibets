# equibets.app deployment

`equibets.app` is the production domain for the Equibets static web app and PWA.

## Recommended first launch

Use Vercel first unless you already prefer Netlify or Cloudflare Pages. This
repo now includes `vercel.json`, `netlify.toml`, and Netlify `_redirects`
defaults for static PWA deployment.

| Setting | Value |
| --- | --- |
| Build command | `npm ci && npm run build` |
| Output directory | `dist` |
| Production domain | `equibets.app` |
| WWW redirect | `www.equibets.app` -> `equibets.app` |

## Vercel launch steps

1. Import the GitHub repository in Vercel.
2. Select the Vite framework preset.
3. Confirm build command `npm run build`.
4. Confirm output directory `dist`.
5. Add domains:
   - `equibets.app`
   - `www.equibets.app`
6. In your domain registrar DNS, add:
   - Apex `A`: `76.76.21.21`
   - `www` `CNAME`: `cname.vercel-dns.com`
7. Wait for Vercel to issue HTTPS certificates.
8. Set `equibets.app` as the primary domain so `www` redirects to the apex.

## Netlify launch steps

1. Import the GitHub repository in Netlify.
2. Netlify will read `netlify.toml`.
3. Confirm build command `npm ci && npm run build`.
4. Confirm publish directory `dist`.
5. Add domains:
   - `equibets.app`
   - `www.equibets.app`
6. In your domain registrar DNS, add:
   - Apex `A`: `75.2.60.5`
   - `www` `CNAME`: the Netlify site hostname
7. Wait for Netlify DNS/HTTPS verification.

## Cloudflare Pages launch steps

1. Create a Pages project from the GitHub repository.
2. Set build command `npm ci && npm run build`.
3. Set output directory `dist`.
4. Add `equibets.app` as a custom domain.
5. If the domain is on Cloudflare DNS, use Cloudflare's generated CNAME records
   and keep the records proxied.

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

Before public marketing, run the event-data refresh workflow with `FEI_COOKIE`
configured and review these artifacts:

- `data/upcoming_events.json`
- `data/fei_results.json`
- `data/horse_index.json`

The in-app sample rows are not the production corpus. `horse_index.json` is the
source-derived list that should become the production horse dataset.

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
