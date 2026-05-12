import * as vscode from 'vscode';
import { PamMemory } from './pamCli';

export class RecallWebviewPanel {
    public static currentPanel: RecallWebviewPanel | undefined;
    private static readonly viewType = 'pamRecall';

    private readonly panel: vscode.WebviewPanel;
    private disposables: vscode.Disposable[] = [];

    public static createOrShow(extensionUri: vscode.Uri, memories: PamMemory[], searchQuery?: string): void {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        if (RecallWebviewPanel.currentPanel) {
            RecallWebviewPanel.currentPanel.panel.reveal(column);
            RecallWebviewPanel.currentPanel.updateContent(memories, searchQuery);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            RecallWebviewPanel.viewType,
            searchQuery ? `PAM: Search "${searchQuery}"` : 'PAM: Recall',
            column || vscode.ViewColumn.One,
            { enableScripts: false }
        );

        RecallWebviewPanel.currentPanel = new RecallWebviewPanel(panel, memories, searchQuery);
    }

    private constructor(panel: vscode.WebviewPanel, memories: PamMemory[], searchQuery?: string) {
        this.panel = panel;
        this.updateContent(memories, searchQuery);

        this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
    }

    private updateContent(memories: PamMemory[], searchQuery?: string): void {
        this.panel.title = searchQuery ? `PAM: Search "${searchQuery}"` : 'PAM: Recall';
        this.panel.webview.html = this.getHtml(memories, searchQuery);
    }

    private getHtml(memories: PamMemory[], searchQuery?: string): string {
        const typeColors: Record<string, string> = {
            episodic: '#4fc3f7',
            semantic: '#81c784',
            procedural: '#ffb74d',
            working: '#ce93d8',
            identity: '#f06292',
        };

        const memoryCards = memories.map(m => {
            const color = typeColors[m.type] || '#90a4ae';
            const content = m.content
                || (m.subject ? `${m.subject} ${m.predicate} ${m.object}` : '')
                || (m.name ? `${m.name}: ${m.description}` : '')
                || 'No content';
            const timestamp = m.timestamp ? new Date(m.timestamp).toLocaleString() : '';
            return `
                <div class="card" style="border-left: 4px solid ${color};">
                    <div class="card-header">
                        <span class="type-badge" style="background: ${color};">${escapeHtml(m.type)}</span>
                        <span class="timestamp">${escapeHtml(timestamp)}</span>
                    </div>
                    <div class="card-body">${escapeHtml(content)}</div>
                </div>
            `;
        }).join('');

        const header = searchQuery
            ? `<h2>Search results for "${escapeHtml(searchQuery)}" (${memories.length} found)</h2>`
            : `<h2>All Memories (${memories.length})</h2>`;

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PAM Recall</title>
    <style>
        body {
            font-family: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, sans-serif);
            padding: 20px;
            color: var(--vscode-foreground, #ccc);
            background: var(--vscode-editor-background, #1e1e1e);
        }
        h2 {
            margin-bottom: 16px;
            font-weight: 400;
            color: var(--vscode-foreground, #eee);
        }
        .card {
            background: var(--vscode-editor-inactiveSelectionBackground, #2d2d2d);
            border-radius: 6px;
            padding: 12px 16px;
            margin-bottom: 12px;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .type-badge {
            color: #000;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .timestamp {
            font-size: 11px;
            opacity: 0.6;
        }
        .card-body {
            font-size: 13px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-break: break-word;
        }
        .empty {
            text-align: center;
            padding: 40px;
            opacity: 0.5;
        }
    </style>
</head>
<body>
    ${header}
    ${memories.length === 0 ? '<div class="empty">No memories found. Use "PAM: Remember This" to add memories.</div>' : memoryCards}
</body>
</html>`;
    }

    private dispose(): void {
        RecallWebviewPanel.currentPanel = undefined;
        this.panel.dispose();
        while (this.disposables.length) {
            const d = this.disposables.pop();
            if (d) { d.dispose(); }
        }
    }
}

function escapeHtml(text: string): string {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
