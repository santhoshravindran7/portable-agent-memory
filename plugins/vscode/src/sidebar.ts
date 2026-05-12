import * as vscode from 'vscode';
import { PamCli, PamMemory } from './pamCli';

type MemoryCategory = 'episodic' | 'semantic' | 'procedural' | 'working' | 'identity';

class MemoryCategoryItem extends vscode.TreeItem {
    constructor(
        public readonly category: MemoryCategory,
        public readonly count: number,
        public readonly memories: PamMemory[]
    ) {
        super(
            `${getCategoryLabel(category)} (${count})`,
            count > 0 ? vscode.TreeItemCollapsibleState.Collapsed : vscode.TreeItemCollapsibleState.None
        );
        this.iconPath = new vscode.ThemeIcon(getCategoryIcon(category));
        this.contextValue = 'pamCategory';
    }
}

class MemoryItem extends vscode.TreeItem {
    constructor(public readonly memory: PamMemory) {
        super(getMemoryLabel(memory), vscode.TreeItemCollapsibleState.None);
        this.tooltip = memory.content || `${memory.subject} ${memory.predicate} ${memory.object}`;
        this.description = memory.timestamp ? new Date(memory.timestamp).toLocaleDateString() : '';
        this.iconPath = new vscode.ThemeIcon('circle-filled');
        this.contextValue = 'pamMemory';
    }
}

function getCategoryLabel(category: MemoryCategory): string {
    const labels: Record<MemoryCategory, string> = {
        episodic: 'Episodic',
        semantic: 'Semantic',
        procedural: 'Procedural',
        working: 'Working',
        identity: 'Identity',
    };
    return labels[category];
}

function getCategoryIcon(category: MemoryCategory): string {
    const icons: Record<MemoryCategory, string> = {
        episodic: 'history',
        semantic: 'book',
        procedural: 'tools',
        working: 'pulse',
        identity: 'person',
    };
    return icons[category];
}

function getMemoryLabel(memory: PamMemory): string {
    if (memory.content) {
        return memory.content.length > 60
            ? memory.content.substring(0, 60) + '...'
            : memory.content;
    }
    if (memory.subject && memory.predicate && memory.object) {
        return `${memory.subject} ${memory.predicate} ${memory.object}`;
    }
    if (memory.name) {
        return memory.name;
    }
    return memory.id || 'Unknown';
}

export class PamSidebarProvider implements vscode.TreeDataProvider<MemoryCategoryItem | MemoryItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private memories: PamMemory[] = [];

    constructor(private cli: PamCli) {}

    refresh(): void {
        this.loadMemories();
    }

    private async loadMemories(): Promise<void> {
        try {
            this.memories = await this.cli.recall();
        } catch {
            this.memories = [];
        }
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: MemoryCategoryItem | MemoryItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: MemoryCategoryItem | MemoryItem): (MemoryCategoryItem | MemoryItem)[] {
        if (!element) {
            return this.getCategories();
        }
        if (element instanceof MemoryCategoryItem) {
            return element.memories.map(m => new MemoryItem(m));
        }
        return [];
    }

    private getCategories(): MemoryCategoryItem[] {
        const categories: MemoryCategory[] = ['episodic', 'semantic', 'procedural', 'working', 'identity'];
        return categories.map(cat => {
            const filtered = this.memories.filter(m => m.type === cat);
            return new MemoryCategoryItem(cat, filtered.length, filtered);
        });
    }
}
