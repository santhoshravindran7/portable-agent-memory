import * as vscode from 'vscode';
import { PamCli, PamMemory } from './pamCli';
import { RecallWebviewPanel } from './webview';
import { PamSidebarProvider } from './sidebar';
import { PamStatusBar } from './statusBar';

export function registerCommands(
    context: vscode.ExtensionContext,
    cli: PamCli,
    sidebar: PamSidebarProvider,
    statusBar: PamStatusBar
): void {
    const refresh = () => {
        sidebar.refresh();
        statusBar.update();
    };

    context.subscriptions.push(
        vscode.commands.registerCommand('pam.rememberThis', async () => {
            const text = await vscode.window.showInputBox({
                prompt: 'What would you like to remember?',
                placeHolder: 'Enter a memory...',
            });
            if (text) {
                try {
                    await cli.remember(text);
                    vscode.window.showInformationMessage(`PAM: Remembered "${text.substring(0, 50)}..."`);
                    refresh();
                } catch (e: any) {
                    vscode.window.showErrorMessage(`PAM: ${e.message}`);
                }
            }
        }),

        vscode.commands.registerCommand('pam.rememberSelection', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('PAM: No active editor with selection.');
                return;
            }
            const selection = editor.document.getText(editor.selection);
            if (!selection) {
                vscode.window.showWarningMessage('PAM: No text selected.');
                return;
            }
            try {
                await cli.remember(selection);
                vscode.window.showInformationMessage(`PAM: Remembered selection (${selection.length} chars)`);
                refresh();
            } catch (e: any) {
                vscode.window.showErrorMessage(`PAM: ${e.message}`);
            }
        }),

        vscode.commands.registerCommand('pam.rememberFact', async () => {
            const subject = await vscode.window.showInputBox({
                prompt: 'Subject (e.g., "TypeScript")',
                placeHolder: 'Subject',
            });
            if (!subject) { return; }

            const predicate = await vscode.window.showInputBox({
                prompt: 'Predicate (e.g., "is a")',
                placeHolder: 'Predicate',
            });
            if (!predicate) { return; }

            const object = await vscode.window.showInputBox({
                prompt: 'Object (e.g., "programming language")',
                placeHolder: 'Object',
            });
            if (!object) { return; }

            try {
                await cli.rememberFact(subject, predicate, object);
                vscode.window.showInformationMessage(`PAM: Remembered fact: ${subject} ${predicate} ${object}`);
                refresh();
            } catch (e: any) {
                vscode.window.showErrorMessage(`PAM: ${e.message}`);
            }
        }),

        vscode.commands.registerCommand('pam.rememberSkill', async () => {
            const name = await vscode.window.showInputBox({
                prompt: 'Skill name (e.g., "deploy-k8s")',
                placeHolder: 'Skill name',
            });
            if (!name) { return; }

            const description = await vscode.window.showInputBox({
                prompt: 'Skill description',
                placeHolder: 'What does this skill do?',
            });
            if (!description) { return; }

            try {
                await cli.rememberSkill(name, description);
                vscode.window.showInformationMessage(`PAM: Skill saved: ${name}`);
                refresh();
            } catch (e: any) {
                vscode.window.showErrorMessage(`PAM: ${e.message}`);
            }
        }),

        vscode.commands.registerCommand('pam.rememberWorking', async () => {
            const goalsInput = await vscode.window.showInputBox({
                prompt: 'Working memory goals (comma-separated)',
                placeHolder: 'e.g., Fix auth bug, Deploy to staging',
            });
            if (!goalsInput) { return; }

            const scratch = await vscode.window.showInputBox({
                prompt: 'Scratch notes (optional)',
                placeHolder: 'Any scratch notes...',
            });

            const goals = goalsInput.split(',').map(g => g.trim()).filter(g => g.length > 0);
            try {
                await cli.rememberWorking(goals, scratch || undefined);
                vscode.window.showInformationMessage(`PAM: Working memory saved with ${goals.length} goal(s)`);
                refresh();
            } catch (e: any) {
                vscode.window.showErrorMessage(`PAM: ${e.message}`);
            }
        }),

        vscode.commands.registerCommand('pam.rememberPreference', async () => {
            const input = await vscode.window.showInputBox({
                prompt: 'Preferences (key=value, comma-separated)',
                placeHolder: 'e.g., theme=dark, language=TypeScript',
            });
            if (!input) { return; }

            const prefs = input.split(',').map(p => p.trim()).filter(p => p.length > 0);
            try {
                await cli.rememberPreference(prefs);
                vscode.window.showInformationMessage('PAM: Preferences saved');
                refresh();
            } catch (e: any) {
                vscode.window.showErrorMessage(`PAM: ${e.message}`);
            }
        }),

        vscode.commands.registerCommand('pam.recall', async () => {
            try {
                const memories = await cli.recall();
                RecallWebviewPanel.createOrShow(context.extensionUri, memories);
            } catch (e: any) {
                vscode.window.showErrorMessage(`PAM: ${e.message}`);
            }
        }),

        vscode.commands.registerCommand('pam.search', async () => {
            const query = await vscode.window.showInputBox({
                prompt: 'Search memories...',
                placeHolder: 'Enter search query',
            });
            if (query) {
                try {
                    const memories = await cli.search(query);
                    if (memories.length === 0) {
                        vscode.window.showInformationMessage('PAM: No memories found.');
                    } else {
                        RecallWebviewPanel.createOrShow(context.extensionUri, memories, query);
                    }
                } catch (e: any) {
                    vscode.window.showErrorMessage(`PAM: ${e.message}`);
                }
            }
        }),

        vscode.commands.registerCommand('pam.export', async () => {
            const uri = await vscode.window.showSaveDialog({
                defaultUri: vscode.Uri.file('memory.pam'),
                filters: { 'PAM Files': ['pam'], 'All Files': ['*'] },
            });
            if (uri) {
                try {
                    await cli.exportMemory(uri.fsPath);
                    vscode.window.showInformationMessage(`PAM: Exported to ${uri.fsPath}`);
                } catch (e: any) {
                    vscode.window.showErrorMessage(`PAM: ${e.message}`);
                }
            }
        }),

        vscode.commands.registerCommand('pam.import', async () => {
            const uris = await vscode.window.showOpenDialog({
                canSelectMany: false,
                filters: { 'PAM Files': ['pam'], 'All Files': ['*'] },
            });
            if (uris && uris[0]) {
                try {
                    await cli.importMemory(uris[0].fsPath);
                    vscode.window.showInformationMessage(`PAM: Imported from ${uris[0].fsPath}`);
                    refresh();
                } catch (e: any) {
                    vscode.window.showErrorMessage(`PAM: ${e.message}`);
                }
            }
        }),

        vscode.commands.registerCommand('pam.verify', async () => {
            try {
                const result = await cli.verify();
                vscode.window.showInformationMessage(`PAM: ${result}`);
            } catch (e: any) {
                vscode.window.showErrorMessage(`PAM: Verification failed — ${e.message}`);
            }
        }),

        vscode.commands.registerCommand('pam.status', async () => {
            try {
                const status = await cli.getStatus();
                vscode.window.showInformationMessage(
                    `PAM Status: ${status.total} total | Episodic: ${status.episodic} | Semantic: ${status.semantic} | Procedural: ${status.procedural} | Working: ${status.working} | Identity: ${status.identity}`
                );
            } catch (e: any) {
                vscode.window.showErrorMessage(`PAM: ${e.message}`);
            }
        }),

        vscode.commands.registerCommand('pam.clearAll', async () => {
            const confirm = await vscode.window.showWarningMessage(
                'Are you sure you want to clear ALL memories? This cannot be undone.',
                { modal: true },
                'Clear All'
            );
            if (confirm === 'Clear All') {
                try {
                    await cli.clearAll();
                    vscode.window.showInformationMessage('PAM: All memories cleared.');
                    refresh();
                } catch (e: any) {
                    vscode.window.showErrorMessage(`PAM: ${e.message}`);
                }
            }
        }),

        vscode.commands.registerCommand('pam.refresh', () => {
            refresh();
        })
    );
}
