// Die aktuell 15 MITRE-Enterprise-Taktiken in Kill-Chain-Reihenfolge — feste
// Taxonomie, analog backend/scripts/seed_data.py TACTIC_GROUPS. Kein eigener
// Endpunkt nötig, da sich diese Liste nicht durch Nutzerdaten ändert.
//
// "Stealth" war früher "Defense Evasion" — MITRE hat die Taktik umbenannt
// (TA0005), unsere interne tactic.id bleibt "defense-evasion" (Abschnitt
// 10f). "Defense Impairment" (TA0112) ist eine neue, 15. Taktik.
export const TACTIC_NAMES = [
  'Reconnaissance',
  'Resource Development',
  'Initial Access',
  'Execution',
  'Persistence',
  'Privilege Escalation',
  'Stealth',
  'Credential Access',
  'Discovery',
  'Lateral Movement',
  'Collection',
  'Command and Control',
  'Exfiltration',
  'Impact',
  'Defense Impairment',
] as const
