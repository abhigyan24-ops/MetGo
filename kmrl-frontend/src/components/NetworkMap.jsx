import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Polyline, CircleMarker, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { NETWORK_STATIONS, MUTTOM_DEPOT, NETWORK_ROUTE } from '../data/stationData'
import './NetworkMap.css'

// Fix leaflet icon issues in Vite
import L from 'leaflet'
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

// Fly to selected station or fit bounds to all if none selected
function MapController({ station, allStations }) {
  const map = useMap()
  useEffect(() => {
    if (station) {
      map.flyTo([station.lat, station.lng], 14, { duration: 0.8 })
    } else if (allStations && allStations.length > 0) {
      const bounds = L.latLngBounds(allStations.map(s => [s.lat, s.lng]))
      map.fitBounds(bounds, { padding: [40, 40], duration: 1 })
    }
  }, [station, allStations, map])
  return null
}

const FILTERS = ['All Transit Networks', 'Phase I — Blue Line']

export default function NetworkMap() {
  const [selected, setSelected] = useState(null)
  const [filter, setFilter] = useState('All Transit Networks')
  const [filterOpen, setFilterOpen] = useState(false)

  function handleChipClick(s) {
    setSelected(s)
  }

  // Ensure Muttom Depot is included in the list of chips, positioned next to Muttom Station
  const muttomIndex = NETWORK_STATIONS.findIndex(s => s.id === 'muttom')
  const stationsWithDepot = [
    ...NETWORK_STATIONS.slice(0, muttomIndex + 1),
    MUTTOM_DEPOT,
    ...NETWORK_STATIONS.slice(muttomIndex + 1)
  ]

  return (
    <section id="network-map" className="nm-section">
      <div className="nm-inner">
        {/* Header */}
        <div className="nm-header">
          <h2 className="nm-title">Explore the Network</h2>
          <p className="nm-sub">Click or hover any station marker to view info, fares &amp; timetables.</p>
        </div>

        {/* Main 2-panel layout */}
        <div className="nm-body">
          {/* Left: Map */}
          <div className="nm-map-wrap">
            {/* Filter dropdown */}
            <div className="nm-filter">
              <button className="nm-filter-btn" onClick={() => setFilterOpen(o => !o)}>
                <span className="nm-filter-dot" />
                {filter}
                <span className="nm-filter-chevron">{filterOpen ? '▲' : '▼'}</span>
              </button>
              {filterOpen && (
                <ul className="nm-filter-list">
                  {FILTERS.map(f => (
                    <li
                      key={f}
                      className={f === filter ? 'active' : ''}
                      onClick={() => { setFilter(f); setFilterOpen(false) }}
                    >
                      {f}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <MapContainer
              center={[10.02, 76.31]}
              zoom={12}
              zoomControl={true}
              scrollWheelZoom={false}
              className="nm-leaflet"
            >
              {/* Dark Theme CartoDB tiles for Metro Control Deck aesthetic */}
              <TileLayer
                attribution='&copy; <a href="https://carto.com">CARTO</a>'
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              />

              {/* Route Polyline */}
              <Polyline
                positions={NETWORK_ROUTE}
                pathOptions={{ color: '#009999', weight: 3.5, opacity: 0.9 }}
              />

              {/* Station Markers */}
              {NETWORK_STATIONS.map(s => (
                <CircleMarker
                  key={s.id}
                  center={[s.lat, s.lng]}
                  radius={selected?.id === s.id ? 9 : 6}
                  pathOptions={{
                    color: '#fff',
                    weight: selected?.id === s.id ? 2.5 : 1.5,
                    fillColor: selected?.id === s.id ? '#009999' : '#00b8b8',
                    fillOpacity: 1,
                  }}
                  eventHandlers={{ click: () => setSelected(s) }}
                >
                  <Tooltip direction="top" offset={[0, -6]} opacity={0.95}>{s.name}</Tooltip>
                </CircleMarker>
              ))}

              {/* Muttom Depot Special Marker */}
              <CircleMarker
                key={MUTTOM_DEPOT.id}
                center={[MUTTOM_DEPOT.lat, MUTTOM_DEPOT.lng]}
                radius={selected?.id === MUTTOM_DEPOT.id ? 10 : 7}
                pathOptions={{
                  color: 'var(--color-bg)',
                  weight: selected?.id === MUTTOM_DEPOT.id ? 2.5 : 1.5,
                  fillColor: 'var(--color-pipeline-operate)', // Thematic accent
                  fillOpacity: 1,
                }}
                eventHandlers={{ click: () => setSelected(MUTTOM_DEPOT) }}
              >
                <Tooltip direction="top" offset={[0, -6]} opacity={0.95}>{MUTTOM_DEPOT.name}</Tooltip>
              </CircleMarker>

              <MapController station={selected} allStations={stationsWithDepot} />
            </MapContainer>
          </div>

          {/* Right: Station info card */}
          {selected ? (
            <div className="nm-info-card">
              {/* Banner */}
              <div className={`nm-card-banner ${selected.isDepot ? 'depot-banner' : ''}`}>
                <span className="nm-card-mal">{selected.malayalam || ''}</span>
                <div className="nm-card-logo">
                  <svg width="32" height="20" viewBox="0 0 90 56" fill="none">
                    <path d="M0 28L28 0h34L0 28z" fill="currentColor" opacity="0.8"/>
                    <path d="M90 28L62 56H28L90 28z" fill="currentColor" opacity="0.8"/>
                    <path d="M45 0l45 28-45 28L0 28z" fill="none" stroke="currentColor" strokeWidth="3"/>
                  </svg>
                  <span>{selected.isDepot ? 'YARD' : 'METRO'}</span>
                </div>
                <span className="nm-card-name-banner">{selected.name}</span>
              </div>

              {/* Body */}
              <div className="nm-card-body">
                <h3 className="nm-card-name">{selected.name}</h3>
                <p className="nm-card-mal-sub">{selected.malayalam || ''}</p>

                {selected.isDepot ? (
                  <div className="nm-card-depot-desc">
                    <p><strong>{selected.description}</strong></p>
                  </div>
                ) : (
                  <>
                    <div className="nm-card-row">
                      <span className="nm-card-icon">🕐</span>
                      <span>{selected.hours}</span>
                    </div>
                    {/* Replace Sequence hack with real headway data */}
                    <div className="nm-card-row">
                      <span className="nm-card-icon">⏱️</span>
                      <span>
                        <strong>Peak Headway: </strong>
                        5-7 mins
                      </span>
                    </div>
                    <div className="nm-card-row">
                      <span className="nm-card-icon">⏲️</span>
                      <span>
                        <strong>Off-peak: </strong>
                        10 mins
                      </span>
                    </div>
                  </>
                )}

                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${selected.lat},${selected.lng}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="nm-maps-btn"
                >
                  View on Google Maps
                </a>
              </div>
            </div>
          ) : (
            <div className="nm-info-card empty-state">
              <div className="nm-empty-icon">📍</div>
              <h3>Select a Station</h3>
              <p>Click any marker on the map or select from the list below to view details.</p>
            </div>
          )}
        </div>

        {/* Bottom chip strip */}
        <div className="nm-chip-strip-wrap">
          <div className="nm-chip-strip">
            {stationsWithDepot.map(s => (
              <button
                key={s.id}
                className={`nm-chip ${selected?.id === s.id ? 'active' : ''} ${s.isDepot ? 'depot-chip' : ''}`}
                onClick={() => handleChipClick(s)}
              >
                {s.name}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
