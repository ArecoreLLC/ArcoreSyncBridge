import mermaid from 'mermaid';

export function initializeMermaid(darkMode = false) {
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    theme: darkMode ? 'dark' : 'default',
    flowchart: { htmlLabels: false, useMaxWidth: true },
  });
}
