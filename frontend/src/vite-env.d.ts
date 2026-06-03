/// <reference types="vite/client" />

declare module "*.png" {
  const src: string;
  export default src;
}

interface ImportMetaEnv {
  readonly VITE_SITE_NAME?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
