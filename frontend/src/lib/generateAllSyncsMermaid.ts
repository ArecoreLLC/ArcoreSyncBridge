import { type DiagramSyncDefinition, syncFlowLines } from './generateSyncMermaid';

export function generateAllSyncsMermaid(definitions: DiagramSyncDefinition[]): string {
  if (!definitions?.length) return 'flowchart TB\nempty["No sync definitions configured"]';
  return ['flowchart TB', ...definitions.flatMap((definition, index) => syncFlowLines(definition, `sync_${index}`))].join('\n');
}
