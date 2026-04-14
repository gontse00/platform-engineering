import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap, CircleMarker } from "react-leaflet";
import L from "leaflet";
import type { CaseRecord, ResourceMarker, ResourceTypeFilter } from "../types";
import { DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM } from "../config";

const caseIcon = new L.Icon({
  iconUrl:
    "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const RESOURCE_COLORS: Record<string, string> = {
  hospital: "#2563eb",
  clinic: "#0891b2",
  police: "#16a34a",
  shelter: "#ea580c",
  hotline: "#7c3aed",
  counseling: "#db2777",
  ngo: "#ca8a04",
  legal: "#4f46e5",
  other: "#6b7280",
};

const RESOURCE_LABELS: Record<string, string> = {
  hospital: "Hospital",
  clinic: "Clinic",
  police: "Police",
  shelter: "Shelter",
  hotline: "Hotline",
  counseling: "Counseling",
  ngo: "NGO",
  legal: "Legal Aid",
  other: "Other",
};

function MapRecenter({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  const prevCenter = useRef(center);

  useEffect(() => {
    if (
      center[0] !== prevCenter.current[0] ||
      center[1] !== prevCenter.current[1]
    ) {
      map.flyTo(center, zoom, { duration: 0.8 });
      prevCenter.current = center;
    }
  }, [center, zoom, map]);

  return null;
}

function spreadOverlappingMarkers(cases: CaseRecord[]) {
  const OFFSET = 0.003;
  const seen = new Map<string, number>();

  return cases.map((c) => {
    const lat = c.location!.latitude;
    const lng = c.location!.longitude;
    const key = `${lat.toFixed(5)},${lng.toFixed(5)}`;
    const idx = seen.get(key) ?? 0;
    seen.set(key, idx + 1);

    if (idx === 0) return { lat, lng };

    const angle = (idx * 137.5 * Math.PI) / 180;
    const radius = OFFSET * Math.ceil(idx / 6);
    return {
      lat: lat + radius * Math.cos(angle),
      lng: lng + radius * Math.sin(angle),
    };
  });
}

type Props = {
  cases: CaseRecord[];
  selectedCase: CaseRecord | null;
  onSelectCase: (c: CaseRecord) => void;
  resources: ResourceMarker[];
  showResources: boolean;
  resourceTypeFilters: Set<ResourceTypeFilter>;
};

export default function CaseMap({
  cases,
  selectedCase,
  onSelectCase,
  resources,
  showResources,
  resourceTypeFilters,
}: Props) {
  let center = DEFAULT_MAP_CENTER;
  let zoom = DEFAULT_MAP_ZOOM;

  if (selectedCase?.location && selectedCase.location.consent_to_share) {
    center = [selectedCase.location.latitude, selectedCase.location.longitude];
    zoom = 14;
  }

  const mappableCases = cases.filter((c) => c.location && c.location.consent_to_share);
  const positions = spreadOverlappingMarkers(mappableCases);

  const filteredResources = showResources
    ? resources.filter((r) => resourceTypeFilters.size === 0 || resourceTypeFilters.has(r.type))
    : [];

  return (
    <div className="map-container">
      {mappableCases.length === 0 && !selectedCase?.location ? (
        <div className="map-empty-overlay">
          <p>No cases with location data to display.</p>
          <p className="map-empty-hint">
            Cases will appear here when survivors share their location.
          </p>
        </div>
      ) : null}

      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={true}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapRecenter center={center} zoom={zoom} />

        {mappableCases.map((c, i) => {
          const pos = positions[i];
          return (
            <Marker
              key={c.case_id}
              position={[pos.lat, pos.lng]}
              icon={caseIcon}
              eventHandlers={{ click: () => onSelectCase(c) }}
            >
              <Popup>
                <div className="map-popup">
                  <strong className={`popup-urgency urgency-${c.urgency}`}>
                    {c.urgency.toUpperCase()}
                  </strong>
                  <p>{c.incident_summary_short || "Case"}</p>
                  {c.normalized_location && (
                    <p className="popup-location">{c.normalized_location}</p>
                  )}
                  {c.location!.is_approximate && (
                    <p className="popup-approx">Approximate location</p>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}

        {filteredResources.map((r) => (
          <CircleMarker
            key={r.id}
            center={[r.latitude, r.longitude]}
            radius={7}
            pathOptions={{
              fillColor: RESOURCE_COLORS[r.type] ?? "#6b7280",
              fillOpacity: 0.85,
              color: "#ffffff",
              weight: 2,
            }}
          >
            <Popup>
              <div className="map-popup resource-popup">
                <strong style={{ background: RESOURCE_COLORS[r.type] ?? "#6b7280" }}>
                  {RESOURCE_LABELS[r.type] ?? r.type}
                </strong>
                <p className="resource-name">{r.name}</p>
                {r.phone && <p className="resource-phone">{r.phone}</p>}
                {r.address && <p className="resource-address">{r.address}</p>}
                {r.hours && <p className="resource-hours">{r.hours}</p>}
                <p className="resource-distance">{r.distance_km} km away</p>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>

      {showResources && filteredResources.length > 0 && (
        <div className="map-legend">
          <div className="legend-item">
            <span className="legend-icon legend-case" />
            Cases
          </div>
          {Array.from(new Set(filteredResources.map((r) => r.type))).map((type) => (
            <div key={type} className="legend-item">
              <span
                className="legend-icon legend-resource"
                style={{ background: RESOURCE_COLORS[type] ?? "#6b7280" }}
              />
              {RESOURCE_LABELS[type] ?? type}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}