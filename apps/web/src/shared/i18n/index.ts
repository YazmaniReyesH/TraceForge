// Configuración de i18next (es-MX ahora; estructura lista para más idiomas).

import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import { esMX } from "./es-MX";

export const DEFAULT_LANGUAGE = "es-MX";

void i18n.use(initReactI18next).init({
  resources: {
    "es-MX": { translation: esMX },
  },
  lng: DEFAULT_LANGUAGE,
  fallbackLng: DEFAULT_LANGUAGE,
  interpolation: { escapeValue: false }, // React ya escapa
  returnNull: false,
});

export default i18n;
