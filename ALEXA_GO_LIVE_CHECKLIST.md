# Alexa Go-Live Checklist

Use this when you are back and ready to make Ev work with real Alexa.

## 1. Start the backend

From the project root:

```bash
cd ev-backend
docker compose up --build
```

Confirm health:

```bash
curl http://localhost:8000/api/v1/health
```

Expected result: a JSON response with `status: ok`.

## 2. Check the local environment

Run:

```bash
make doctor
```

On Windows, you can also use:

```bat
windows\alexa-doctor.bat
```

This checks:
- Python
- Docker
- ngrok
- required files
- endpoint assumptions

## 3. Expose the backend publicly over HTTPS

Alexa cannot call `localhost`.

Recommended:

```bash
ngrok http 8000
```

If ngrok is installed and available, the automation can often detect it for you.

## 4. Prepare the Alexa local dev setup

Run:

```bash
make alexa-local-dev
```

This can:
- detect or try to start ngrok
- sync the public Alexa endpoint into the skill manifest
- validate the Alexa package
- print a ready summary

If needed, set the endpoint manually:

```bash
ALEXA_PUBLIC_ENDPOINT=https://YOUR-PUBLIC-URL/api/v1/alexa/webhook make alexa-endpoint
make alexa-validate
```

## 5. Create the skill in the Alexa Developer Console

Go to:

- https://developer.amazon.com/alexa/console/ask

Create a new skill with:
- Name: `Ev`
- Type: `Custom`
- Provisioning: `Provision your own`
- Locale: `English (UK)`

## 6. Set the invocation name

Use:

```text
ev
```

If Amazon rejects `ev`, use the shortest fallback that passes and then update the interaction model later.

## 7. Import the interaction model

Use:

- `alexa/skill-package/interactionModels/custom/en-GB.json`

## 8. Configure the endpoint

Use your public HTTPS webhook URL:

```text
https://YOUR-PUBLIC-URL/api/v1/alexa/webhook
```

## 9. Build the model

In the Alexa console:
- Save Model
- Build Model

Wait for the build to complete.

## 10. Test these phrases

Core:
- Alexa, open Ev
- Alexa, ask Ev what is on my calendar
- Alexa, ask Ev who is Ada Lovelace

Home:
- Alexa, ask Ev turn on the living room light
- Alexa, ask Ev check the lamp

Dev command:
- Alexa, ask Ev prep
- Alexa, ask Ev ready
- Alexa, ask Ev sync

## 11. If it does not work

Run:

```bash
make check
make doctor
make alexa-local-dev
```

Then inspect:
- whether the tunnel is still live
- whether the Alexa console endpoint exactly matches the tunnel URL
- whether the invocation name was accepted
- whether the skill model was built successfully

## 12. What you still need to provide yourself

I cannot fill these in for you:
- your actual public HTTPS endpoint
- your Amazon Developer Console configuration
- your Home Assistant credentials
- your OpenAI API key
- your Google Calendar API key if you use Google Calendar

## 13. Safe secrets reminder

Do not store real secrets directly in uploaded public files.
Use:
- `.env`
- GitHub repository secrets if you later automate deployment
