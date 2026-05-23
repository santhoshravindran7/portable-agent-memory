import * as child_process from 'child_process';
import * as vscode from 'vscode';

const PAM_INSTALL_URL = 'git+https://github.com/santhoshravindran7/portable-agent-memory.git@main#subdirectory=sdk/python';
const INSTALL_PROMPT_DISMISSED_KEY = 'pam.installPromptDismissed';

export interface PamStatus {
    total: number;
    episodic: number;
    semantic: number;
    procedural: number;
    working: number;
    identity: number;
}

export interface PamMemory {
    id: string;
    type: string;
    content: string;
    timestamp: string;
    subject?: string;
    predicate?: string;
    object?: string;
    name?: string;
    description?: string;
}

export class PamCli {
    private pamPath: string = 'pam';

    constructor(private readonly context?: vscode.ExtensionContext) {}

    async isInstalled(): Promise<boolean> {
        try {
            await this.exec(['--version']);
            return true;
        } catch {
            return false;
        }
    }

    isInstallPromptDismissed(globalState?: vscode.Memento): boolean {
        const state = globalState ?? this.context?.globalState;
        if (!state) {
            return false;
        }

        return state.get<boolean>(INSTALL_PROMPT_DISMISSED_KEY, false);
    }

    async promptInstall(globalState?: vscode.Memento): Promise<void> {
        const state = globalState ?? this.context?.globalState;
        const action = await vscode.window.showWarningMessage(
            'PAM CLI is not installed. Install it to use Portable Agent Memory.',
            'Install Now',
            'Remind Me Later',
            "Don't Show Again"
        );
        if (action === 'Install Now') {
            const pip = await this.findPip();
            const terminal = vscode.window.createTerminal('PAM Install');
            terminal.show();
            terminal.sendText(`${pip} install "${PAM_INSTALL_URL}"`);
        } else if (action === "Don't Show Again" && state) {
            await state.update(INSTALL_PROMPT_DISMISSED_KEY, true);
        }
    }

    private async findPip(): Promise<string> {
        const candidates = process.platform === 'win32'
            ? ['pip', 'pip3', 'python -m pip', 'python3 -m pip', 'py -m pip']
            : ['pip3', 'pip', 'python3 -m pip', 'python -m pip'];

        for (const pip of candidates) {
            try {
                await this.execRaw(`${pip} --version`);
                return pip;
            } catch {
                continue;
            }
        }
        return 'pip';
    }

    async remember(text: string): Promise<string> {
        return this.exec(['remember', text]);
    }

    async rememberFact(subject: string, predicate: string, object: string): Promise<string> {
        return this.exec(['remember', '--fact', subject, predicate, object]);
    }

    async rememberSkill(name: string, description: string): Promise<string> {
        return this.exec(['remember', '--skill', name, description]);
    }

    async rememberWorking(goals: string[], scratch?: string): Promise<string> {
        const args = ['remember', '--working', ...goals];
        if (scratch) {
            args.push('--scratch', scratch);
        }
        return this.exec(args);
    }

    async rememberPreference(preferences: string[]): Promise<string> {
        return this.exec(['remember', '--preference', ...preferences]);
    }

    async recall(): Promise<PamMemory[]> {
        const output = await this.exec(['recall', '--json']);
        try {
            return JSON.parse(output);
        } catch {
            return [];
        }
    }

    async search(query: string): Promise<PamMemory[]> {
        const output = await this.exec(['recall', '--search', query, '--json']);
        try {
            return JSON.parse(output);
        } catch {
            return [];
        }
    }

    async getStatus(): Promise<PamStatus> {
        const output = await this.exec(['status', '--json']);
        try {
            return JSON.parse(output);
        } catch {
            return { total: 0, episodic: 0, semantic: 0, procedural: 0, working: 0, identity: 0 };
        }
    }

    async exportMemory(path: string): Promise<string> {
        return this.exec(['export', path]);
    }

    async importMemory(path: string): Promise<string> {
        return this.exec(['import', path]);
    }

    async verify(): Promise<string> {
        return this.exec(['verify']);
    }

    async clearAll(): Promise<string> {
        return this.exec(['clear', '--force']);
    }

    private exec(args: string[]): Promise<string> {
        return new Promise((resolve, reject) => {
            child_process.execFile(this.pamPath, args, {
                timeout: 30000,
                maxBuffer: 1024 * 1024,
            }, (error, stdout, stderr) => {
                if (error) {
                    reject(new Error(stderr || error.message));
                } else {
                    resolve(stdout.trim());
                }
            });
        });
    }

    private execRaw(command: string): Promise<string> {
        return new Promise((resolve, reject) => {
            child_process.exec(command, { timeout: 10000 }, (error, stdout) => {
                if (error) {
                    reject(error);
                } else {
                    resolve(stdout.trim());
                }
            });
        });
    }
}
