#!/usr/bin/env bash
read -sp "Enter password: " PASSWORD
echo ""
node -e "require('bcryptjs').hash('$PASSWORD', 8).then(h => console.log(h))"
