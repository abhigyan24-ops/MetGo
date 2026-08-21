/**
 * Official Kochi Metro Rail Limited (KMRL) Domain Data & Constants
 * Sourced directly from KMRL Technical Specifications, Corporate Reports & Phase II Projections.
 */

export const TRAIN_NAMES = {
  T01: { name: 'Krishna', malayalam: 'കൃഷ്ണ', type: 'Sacred River' },
  T02: { name: 'Tapti', malayalam: 'തപ്തി', type: 'Sacred River' },
  T03: { name: 'Nila', malayalam: 'നിള', type: 'Kerala Heritage River' },
  T04: { name: 'Sarayu', malayalam: 'സരയു', type: 'Sacred River' },
  T05: { name: 'Aruth', malayalam: 'അരുത്', type: 'Sacred River' },
  T06: { name: 'Vaigai', malayalam: 'വൈഗൈ', type: 'Heritage River' },
  T07: { name: 'Jhanavi', malayalam: 'ജാഹ്നവി', type: 'Sacred River' },
  T08: { name: 'Dhwanil', malayalam: 'ധ്വനിൽ', type: 'Sacred Stream' },
  T09: { name: 'Bhavani', malayalam: 'ഭവാനി', type: 'Western Ghats River' },
  T10: { name: 'Padma', malayalam: 'പത്മ', type: 'Sacred River' },
  T11: { name: 'Mandakini', malayalam: 'മന്ദാകിനി', type: 'Himalayan River' },
  T12: { name: 'Yamuna', malayalam: 'യമുന', type: 'Sacred River' },
  T13: { name: 'Periyar', malayalam: 'പെരിയാർ', type: 'Kochi Lifeline River' },
  T14: { name: 'Kabani', malayalam: 'കബനി', type: 'Kerala Tributary' },
  T15: { name: 'Vaayu', malayalam: 'വായു', type: 'Vedic Element' },
  T16: { name: 'Kaveri', malayalam: 'കാവേരി', type: 'Sacred Southern River' },
  T17: { name: 'Shiriya', malayalam: 'ശിരിയ', type: 'North Kerala River' },
  T18: { name: 'Pampa', malayalam: 'പമ്പ', type: 'Sacred Pilgrim River' },
  T19: { name: 'Narmada', malayalam: 'നർമദ', type: 'Sacred River' },
  T20: { name: 'Mahe', malayalam: 'മാഹി', type: 'Heritage River' },
  T21: { name: 'Maarut', malayalam: 'മാരുത്', type: 'Vedic Stream' },
  T22: { name: 'Sabarmathi', malayalam: 'സബർമതി', type: 'National Heritage River' },
  T23: { name: 'Godhavari', malayalam: 'ഗോദാവരി', type: 'Dakshin Ganga' },
  T24: { name: 'Ganga', malayalam: 'ഗംഗ', type: 'National River of India' },
  T25: { name: 'Pavan', malayalam: 'പവൻ', type: 'Sacred Stream' },
}

export function getTrainName(trainId) {
  const norm = String(trainId || '').toUpperCase()
  return TRAIN_NAMES[norm] || { name: norm, malayalam: '', type: 'Trainset' }
}

export function formatTrainLabel(trainId, currentBay = '') {
  const info = getTrainName(trainId)
  const bayStr = currentBay ? ` · ${currentBay}` : ''
  if (info.malayalam) {
    return `${trainId} · ${info.name.toUpperCase()} (${info.malayalam})${bayStr}`
  }
  return `${trainId}${bayStr}`
}

export const KMRL_SPECS = {
  fleetSize: 25,
  rollingStock: 'Alstom Metropolis (3 coaches)',
  trainLengthMeters: 66.55,
  traction: '750V DC Third Rail System',
  signaling: 'Alstom Urbalis 400 CBTC (CATC / ATP / ATO)',
  designSpeedKmh: 90,
  commercialSpeedKmh: 35,
  crushCapacityPassengers: 975,
  solarCapacityMwp: 5.389,
  muttomSolarMwp: 2.7,
  rooftopSolarMwp: 2.689,
  cleanEnergyRatio: '54%',
  depot: 'Muttom Maintenance Depot & Stabling Yard (24 Bays)',
}

export const MULTIMODAL_HUBS = {
  T01: { hub: 'Water Metro', label: 'Vyttila Ferry Sync', icon: '🚢' },
  T02: { hub: 'Water Metro', label: 'High Court Ferry Sync', icon: '🚢' },
  T03: { hub: 'Railways', label: 'Aluva IR Junction Sync', icon: '🚆' },
  T04: { hub: 'Railways', label: 'Ernakulam South IR Sync', icon: '🚆' },
  T05: { hub: 'Airport Feeder', label: 'CIAL Electric Feeder', icon: '✈️' },
  T06: { hub: 'KSRTC Feeder', label: 'Edappally Hub Feeder', icon: '🚌' },
}

export const KMRL_PHASES = [
  {
    id: 'phase1',
    name: 'Phase I + Extensions (Blue Line)',
    route: 'Aluva ↔ Thripunithura Terminal',
    length: '27.96 km',
    stations: 25,
    status: 'Operational',
    badgeClass: 'status-completed',
  },
  {
    id: 'phase2',
    name: 'Phase II (Pink Line)',
    route: 'JLN Stadium ↔ Kakkanad ↔ Infopark / SmartCity',
    length: '11.20 km',
    stations: 11,
    status: 'Under Construction (AIIB)',
    badgeClass: 'status-ongoing',
  },
  {
    id: 'water_metro',
    name: 'Kochi Water Metro',
    route: '15 Integrated Ferry Routes · 38 Terminals',
    length: '76.00 km',
    stations: 38,
    status: 'Operational (78 Battery-Hybrid Ferries)',
    badgeClass: 'status-completed',
  },
]
