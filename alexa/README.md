# Alexa Skill Setup for Ev

This directory contains the Alexa skill package artifacts for Ev.

## What this is

The backend in `app/` is the service logic.
The Alexa skill package in `alexa/skill-package/` is the Amazon-side configuration that tells Alexa how to talk to the backend.

## Files

- `skill-package/skill.json` — Alexa skill manifest
- `skill-package/interactionModels/custom/en-GB.json` — interaction model for British English

## Important note about local development

Alexa cannot call `localhost` directly.
You need a public HTTPS URL for the backend endpoint.

Also important: Alexa device Wi-Fi connection is managed through Amazon/device setup, not through this skill backend. This project can automate the skill manifest endpoint, but it cannot directly force an Echo device onto Wi-Fi from the backend.

Examples:
- ngrok
- Cloudflare Tunnel
- a deployed server

The webhook endpoint Alexa should call is:

```text
https://YOUR-PUBLIC-URL/api/v1/alexa/webhook
```

## Recommended setup flow

1. Start the backend.
2. Expose it over HTTPS with a public URL.
3. Update `alexa/skill-package/skill.json` endpoint URI.
4. Import or recreate the interaction model in the Alexa Developer Console.
5. Test using the Alexa Developer Console or a connected device.

## Invocation name

Current default invocation name:

```text
ev bot
```

Example phrases:
- Alexa, open Ev
- Alexa, ask Ev what is on my calendar
- Alexa, ask Ev to turn on the living room light
- Alexa, ask Ev prep
- Alexa, ask Ev ready
- Alexa, ask Ev sync

## Validation and automation

Validate your local tooling and critical files first:

```bash
make doctor
```

Validate the skill package locally:

```bash
make alexa-validate
```

Verify the package files are present and valid JSON:

```bash
make alexa-generate
```

Automatically sync a running ngrok HTTPS tunnel into the Alexa manifest and a local helper env file:

```bash
make alexa-sync
```

Or do the fuller local Alexa development flow, which can detect or try to start an ngrok tunnel, sync the endpoint, validate the package, and print a summary:

```bash
make alexa-local-dev
```

Or do the basic local Alexa preparation flow in one go:

```bash
make alexa-ready
python scripts/print_alexa_ready_summary.py
```

If you prefer to set the endpoint manually:

```bash
ALEXA_PUBLIC_ENDPOINT=https://YOUR-PUBLIC-URL/api/v1/alexa/webhook make alexa-endpoint
```

Run the full project validation pipeline:

```bash
make check
```

## What you still need to do in Amazon Developer Console

- Create a **Custom** skill
- Set the invocation name
- Configure the HTTPS endpoint
- Paste/import the interaction model
- Save and build the model
- Test requests against the backend

## Suggested next Alexa work

- add more intent coverage
- add locale variants
- align backend intent routing more directly with named intents
- add deployment-time endpoint injection for the skill manifest
