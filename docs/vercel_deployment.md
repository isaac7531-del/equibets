# Vercel deployment

Equibets is a static Vite application. Vercel should install dependencies with
`npm ci`, build with `npm run build`, and serve the generated `dist` directory.
Those settings are captured in `vercel.json` so GitHub-connected deployments and
CLI deployments use the same build.

## Vercel project setup

1. In Vercel, import the GitHub repository as a new project.
2. Use the Vite framework preset.
3. Confirm these project settings:
   - Install Command: `npm ci`
   - Build Command: `npm run build`
   - Output Directory: `dist`
4. Deploy the `main` branch once the setup branch has been merged.

## Domain setup for `equibets.app`

Add both domains in Vercel under Project Settings -> Domains:

- `equibets.app`
- `www.equibets.app`

In GoDaddy DNS management, keep the GoDaddy nameservers and set these records:

| Type | Name | Value | TTL |
| --- | --- | --- | --- |
| A | `@` | `76.76.21.21` | 1 hour |
| CNAME | `www` | `cname.vercel-dns.com` | 1 hour |

Remove or replace any existing GoDaddy parking, forwarding, or conflicting `A`,
`AAAA`, and `CNAME` records for `@` or `www` before saving these records.

## Verification

After DNS propagates, verify both hostnames resolve through Vercel:

```bash
dig +short equibets.app
dig +short www.equibets.app
```

Then confirm the production app loads at:

- `https://equibets.app`
- `https://www.equibets.app`
