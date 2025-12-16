from __future__ import annotations

import uuid

# Committed namespace constant for deterministic UUIDv5 IDs.
# Changing this will change IDs for all generated content.
UUID_NAMESPACE: uuid.UUID = uuid.UUID("c9b4f65f-2d5a-4e62-9e04-8b6ea6c60b41")
