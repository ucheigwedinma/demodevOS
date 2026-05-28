# Docker Secrets

This directory holds secret files for Docker Compose production deployments.
Each file contains a single secret value with no trailing newline.

## Required Files

| File | Description |
|------|-------------|
| `django_secret_key` | Django SECRET_KEY (cryptographic signing) |
| `db_password` | PostgreSQL password |
| `email_host_password` | SMTP password (ZeptoMail send-mail token) |
| `oauth_google_client_id` | Google OAuth client ID |
| `oauth_google_client_secret` | Google OAuth client secret |
| `oauth_microsoft_client_id` | Microsoft OAuth client ID |
| `oauth_microsoft_client_secret` | Microsoft OAuth client secret |

## How to Populate

```bash
# Generate a Django secret key
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" | tr -d '\n' > secrets/django_secret_key

# Write secrets (use -n to avoid trailing newline)
echo -n 'your-db-password' > secrets/db_password
echo -n 'your-zeptomail-token' > secrets/email_host_password
echo -n 'your-google-client-id' > secrets/oauth_google_client_id
echo -n 'your-google-client-secret' > secrets/oauth_google_client_secret
echo -n 'your-microsoft-client-id' > secrets/oauth_microsoft_client_id
echo -n 'your-microsoft-client-secret' > secrets/oauth_microsoft_client_secret

# Lock down permissions (owner-only read)
chmod 600 secrets/*
```

## How It Works

Docker Compose mounts these files into containers at `/run/secrets/<name>`.
Django reads them via `config.secrets.get_secret()`, which checks
`/run/secrets/<name>` first and falls back to environment variables
for local development.

## Security

- Never commit secret files to Git (they are gitignored)
- Set file permissions to `600` (owner read/write only)
- On the production host, ensure the `secrets/` directory is owned by root
- Rotate secrets by updating the file and restarting containers
