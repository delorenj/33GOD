#!/usr/bin/env bash
set -euo pipefail
read -sp "Enter password: " PASSWORD
echo ""
PASSWORD="$PASSWORD" node -e "
  const p = process.env.PASSWORD;
  require('bcryptjs').hash(p, 8).then(h => console.log(h));
"
