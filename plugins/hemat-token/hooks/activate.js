#!/usr/bin/env node
// SessionStart: stdout becomes hidden context. Rules are short on purpose: they are paid every session.
const fs = require('fs');
const path = require('path');
if (process.env.HEMAT_TOKEN === 'off') process.exit(0);
process.stdout.write(fs.readFileSync(path.join(__dirname, '..', 'rules.md'), 'utf8'));
