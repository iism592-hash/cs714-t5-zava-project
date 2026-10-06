"""Create local deployment credentials once; never print the secret or commit it."""
import json
import os
from pathlib import Path
import secrets
from promotions.auth import password_hash

folder = Path('scripts/local-diagnostics')
folder.mkdir(parents=True, exist_ok=True)
credentials = folder / 'promotion-manager.credentials.json'
if credentials.exists():
    data = json.loads(credentials.read_text())
else:
    data = {'username':'store-manager','password':secrets.token_urlsafe(24)}
    credentials.write_text(json.dumps(data,indent=2))
settings = {
    'PROMOTION_MANAGER_USERNAME':data['username'],
    'PROMOTION_MANAGER_PASSWORD_HASH':password_hash(data['password']),
    'INVENTORY_CHECK_TIMEZONE':'America/Los_Angeles',
    'INVENTORY_CHECK_HOUR':'8',
}
(folder / 'promotion-appsettings.json').write_text(json.dumps(settings))
print('Manager login saved locally; deployment uses only a salted scrypt password hash.')
