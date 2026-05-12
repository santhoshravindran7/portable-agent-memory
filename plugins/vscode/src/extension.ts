import * as vscode from 'vscode';
import { PamCli } from './pamCli';
import { registerCommands } from './commands';
import { PamSidebarProvider } from './sidebar';
import { PamStatusBar } from './statusBar';

export async function activate(context: vscode.ExtensionContext): Promise<void> {
    const cli = new PamCli();

    // Check if PAM CLI is available
    const installed = await cli.isInstalled();

    // Sidebar tree view
    const sidebarProvider = new PamSidebarProvider(cli);
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('pamMemoryTree', sidebarProvider)
    );

    // Status bar
    const statusBar = new PamStatusBar(cli);
    context.subscriptions.push({ dispose: () => statusBar.dispose() });

    // Register all commands
    registerCommands(context, cli, sidebarProvider, statusBar);

    // Initial data load
    sidebarProvider.refresh();
    statusBar.update();

    if (!installed) {
        cli.promptInstall();
    }
}

export function deactivate(): void {
    // Cleanup handled by disposables
}
