/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_HEY_CHAT_VOICE_ENABLED?: string;
  readonly VITE_PERFORMANCE_OBSERVABILITY_ENABLED?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
