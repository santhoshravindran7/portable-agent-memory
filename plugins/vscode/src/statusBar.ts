import * as vscode from 'vscode';
import { PamCli } from './pamCli';

export class PamStatusBar {
    private item: vscode.StatusBarItem;

    constructor(private cli: PamCli) {
        this.item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50);
        this.item.command = 'pam.recall';
        this.item.tooltip = 'Click to recall memories';
        this.item.show();
    }

    async update(): Promise<void> {
        try {
            const status = await this.cli.getStatus();
            this.item.text = `$(database) PAM: ${status.total} entries`;
        } catch {
            this.item.text = '$(database) PAM: --';
        }
    }

    dispose(): void {
        this.item.dispose();
    }
}
