// Die 14 MITRE-Enterprise-Taktiken in Kill-Chain-Reihenfolge — feste Taxonomie,
// analog backend/scripts/seed_data.py TACTIC_GROUPS. Kein eigener Endpunkt
// nötig, da sich diese Liste nicht durch Nutzerdaten ändert.
export const TACTIC_NAMES = [
  'Reconnaissance',
  'Resource Development',
  'Initial Access',
  'Execution',
  'Persistence',
  'Privilege Escalation',
  'Defense Evasion',
  'Credential Access',
  'Discovery',
  'Lateral Movement',
  'Collection',
  'Command and Control',
  'Exfiltration',
  'Impact',
] as const
