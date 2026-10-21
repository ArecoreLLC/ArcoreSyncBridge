export interface DiagramSyncDefinition {
  name?: string;
  source_table_name?: string;
  source_table_name_resolved?: string;
  target_list_name?: string;
  sync_mode?: string;
  cdc_enabled?: boolean;
  is_paused?: boolean;
}

// Entity-encode labels so names cannot introduce Mermaid syntax or HTML.
export function mermaidLabel(value: string): string {
  return Array.from(value, (character) => {
    const code = character.codePointAt(0)!;
    return /[a-zA-Z0-9 _.-]/.test(character) ? character : `#${code};`;
  }).join('');
}

export function syncFlowLines(definition: DiagramSyncDefinition, prefix: string): string[] {
  const source = mermaidLabel(definition.source_table_name || definition.source_table_name_resolved || 'Source table');
  const target = mermaidLabel(definition.target_list_name || 'SharePoint list');
  const name = mermaidLabel(definition.name || 'Sync');
  const mode = definition.is_paused ? 'Paused' : definition.cdc_enabled ? 'CDC' : 'Sync';
  const arrow = definition.sync_mode === 'TWO_WAY' ? '<-->' : '-->';
  return [
    `${prefix}_source["${source}"]`,
    `${prefix}_sync["${name} (${mode})"]`,
    `${prefix}_target["${target}"]`,
    `${prefix}_source ${arrow} ${prefix}_sync`,
    `${prefix}_sync ${arrow} ${prefix}_target`,
  ];
}

export function generateSyncFlowMermaid(definition: DiagramSyncDefinition): string {
  return ['flowchart LR', ...syncFlowLines(definition, 'sync')].join('\n');
}
