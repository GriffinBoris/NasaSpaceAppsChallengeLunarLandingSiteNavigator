export interface FeaturedSiteInterface {
  name: string;
  description: string;
  latitude: number;
  longitude: number;
}

export interface FeaturedSiteGroupInterface {
  name: string;
  sites: FeaturedSiteInterface[];
}

export const FEATURED_SITE_GROUPS: FeaturedSiteGroupInterface[] = [
  {
    name: "Commercial Lunar Payload Services",
    sites: [
      { name: "Odysseus (IM-1)", description: "2024, Malapert A", latitude: -80.13, longitude: 1.44 },
      { name: "Athena (IM-2)", description: "2025, Mons Mouton", latitude: -84.7906, longitude: 29.1957 },
      { name: "Blue Ghost Mission 1", description: "2025, Mare Crisium", latitude: 18.5623, longitude: 61.8103 },
    ],
  },
  {
    name: "Apollo",
    sites: [
      { name: "Apollo 11", description: "1969, Mare Tranquillitatis", latitude: 0.6741, longitude: 23.473 },
      { name: "Apollo 12", description: "1969, Oceanus Procellarum", latitude: -3.0124, longitude: -23.4216 },
      { name: "Apollo 14", description: "1971, Fra Mauro", latitude: -3.6453, longitude: -17.4714 },
      { name: "Apollo 15", description: "1971, Hadley–Apennine", latitude: 26.1322, longitude: 3.6339 },
      { name: "Apollo 16", description: "1972, Descartes Highlands", latitude: -8.973, longitude: 15.5002 },
      { name: "Apollo 17", description: "1972, Taurus–Littrow", latitude: 20.1908, longitude: 30.7717 },
    ],
  },
  {
    name: "Other national programs",
    sites: [
      { name: "Chandrayaan-3", description: "2023, Shiv Shakti point", latitude: -69.373, longitude: 32.319 },
      { name: "SLIM", description: "2024, near Shioli crater", latitude: -13.316, longitude: 25.251 },
      { name: "Chang'e 3", description: "2013, Mare Imbrium", latitude: 44.12, longitude: -19.51 },
      { name: "Chang'e 4", description: "2019, Von Kármán crater", latitude: -45.4561, longitude: 177.5885 },
      { name: "Chang'e 5", description: "2020, Oceanus Procellarum", latitude: 43.0576, longitude: -51.9161 },
      { name: "Chang'e 6", description: "2024, Apollo crater", latitude: -41.6385, longitude: -153.9852 },
    ],
  },
];
