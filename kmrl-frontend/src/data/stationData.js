/**
 * KMRL Station & Route Data
 * Sourced from official KMRL coordinates
 */

// Sourced from OpenStreetMap Overpass API and Wikipedia
export const NETWORK_STATIONS = [
  { id: 'aluva', name: 'Aluva', lat: 10.1100952, lng: 76.3495159 },
  { id: 'pulinchodu', name: 'Pulinchodu', lat: 10.0950475, lng: 76.3467836 },
  { id: 'companypady', name: 'Companypady', lat: 10.0873039, lng: 76.3425681 },
  { id: 'ambattukavu', name: 'Ambattukavu', lat: 10.0794208, lng: 76.3387004 },
  { id: 'muttom', name: 'Muttom', lat: 10.0727253, lng: 76.3337157 },
  { id: 'kalamassery', name: 'Kalamassery', lat: 10.0585393, lng: 76.3221673 },
  { id: 'cusat', name: 'Cochin University (CUSAT)', lat: 10.0466793, lng: 76.3183086 },
  { id: 'pathadipalam', name: 'Pathadipalam', lat: 10.0359805, lng: 76.314485 },
  { id: 'edapally', name: 'Edapally', lat: 10.025487, lng: 76.3079848 },
  { id: 'changampuzha', name: 'Changampuzha Park', lat: 10.0151019, lng: 76.3024538 },
  { id: 'palarivattom', name: 'Palarivattom', lat: 10.00633, lng: 76.3049281 },
  { id: 'jln', name: 'JLN Stadium', lat: 10.0002723, lng: 76.2990841 },
  { id: 'kaloor', name: 'Kaloor', lat: 9.9942991, lng: 76.2916664 },
  { id: 'lissie', name: 'Lissie', lat: 9.9912053, lng: 76.2884381 },
  { id: 'mgroad', name: 'M.G Road', lat: 9.9833224, lng: 76.2824385 },
  { id: 'maharajas', name: 'Maharaja\'s College', lat: 9.9733747, lng: 76.2851082 },
  { id: 'ernakulam_south', name: 'Ernakulam South', lat: 9.9686172, lng: 76.2894579 },
  { id: 'kadavanthra', name: 'Kadavanthra', lat: 9.9666766, lng: 76.2982044 },
  { id: 'elamkulam', name: 'Elamkulam', lat: 9.9672669, lng: 76.3084361 },
  { id: 'vytila', name: 'Vytila', lat: 9.9658, lng: 76.3195 }, // Geocoded
  { id: 'thykkoodam', name: 'Thykkoodam', lat: 9.9601104, lng: 76.3237287 },
  { id: 'petta', name: 'Petta', lat: 9.9524963, lng: 76.3301852 },
  { id: 'vadakkekotta', name: 'Vadakkekotta', lat: 9.9528098, lng: 76.339488 },
  { id: 'sn_junction', name: 'SN Junction', lat: 9.9546771, lng: 76.3460351 },
  { id: 'tripunithura', name: 'Tripunithura Terminal', lat: 9.9505728, lng: 76.3517236 }
].map(s => ({ ...s, hours: '06:00 AM – 10:00 PM' })) // Verified general operating window

// Distinct point for Muttom Depot (Project focus)
export const MUTTOM_DEPOT = {
  id: 'muttom_depot',
  name: 'Muttom Depot',
  lat: 10.072575,
  lng: 76.333727,
  isDepot: true,
  description: 'This is Muttom Yard — where MetGo plans nightly train induction'
}

export const NETWORK_ROUTE = NETWORK_STATIONS.map(s => [s.lat, s.lng])
