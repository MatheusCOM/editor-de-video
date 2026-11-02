import type React from "react";
import type { OverlayProps } from "../overlays";
import { userRegistry } from "./user";

/**
 * Componentes criados a partir de referências (engenharia reversa).
 *
 * Onde criar:
 *   - componente do PLUGIN (vai para todos que instalarem): crie aqui nesta pasta e registre abaixo.
 *   - componente do USUÁRIO: salve em ~/.editor-video/components/<nome>.tsx com `export default`.
 *     O render copia e registra automaticamente com o nome do arquivo.
 *
 * Contrato: React.FC<OverlayProps> — props, brand, safe, duration (s). O frame é local ao overlay
 * (useCurrentFrame() começa em 0 quando o overlay entra).
 * Uso no EDL: {"type": "<nome>", "start": 1, "end": 3, "props": {...}}
 */
export const customRegistry: Record<string, React.FC<OverlayProps>> = {
  ...userRegistry,
};
