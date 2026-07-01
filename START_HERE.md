# Start Here

If you come back later and want the shortest path:

## Fastest path

1. Open the project folder.
2. Run:

```bash
make doctor
```

3. Start the backend:

```bash
docker compose up --build
```

4. Run:

```bash
make alexa-local-dev
```

5. Open:
- `ALEXA_GO_LIVE_CHECKLIST.md`

That file contains the real Alexa go-live sequence.

## Windows shortcuts

If `make` is annoying on Windows, use:

```bat
windows\alexa-doctor.bat
windows\alexa-local-dev.bat
```

## Key files

- `README.md`
- `ALEXA_GO_LIVE_CHECKLIST.md`
- `alexa/README.md`

## If you only remember one thing

Alexa needs a public HTTPS endpoint. `localhost` will not work directly.
