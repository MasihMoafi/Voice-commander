import * as vscode from 'vscode';
import { spawn } from 'child_process';
import * as path from 'path';

let recording = false;
let pythonProcess: any = null;

export function activate(context: vscode.ExtensionContext) {
    
    let startRecording = vscode.commands.registerCommand('voice-commander.startRecording', () => {
        if (recording) return;
        
        recording = true;
        vscode.window.showInformationMessage('Voice recording started (F9 to stop)');
        
        // Start Python recorder
        const pythonPath = getPythonPath();
        pythonProcess = spawn(pythonPath, [getRecorderPath()]);
        
        pythonProcess.stdout.on('data', (data: Buffer) => {
            const text = data.toString().trim();
            if (text && text !== '>>> Recording started. Press F9 to stop.') {
                insertTextAtCursor(text);
            }
        });
        
        pythonProcess.on('close', () => {
            recording = false;
        });
    });

    let stopRecording = vscode.commands.registerCommand('voice-commander.stopRecording', () => {
        if (!recording) return;
        
        recording = false;
        vscode.window.showInformationMessage('Voice recording stopped');
        
        if (pythonProcess) {
            pythonProcess.kill();
            pythonProcess = null;
        }
    });

    context.subscriptions.push(startRecording, stopRecording);
}

function getPythonPath(): string {
    return 'python3';
}

function getRecorderPath(): string {
    const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    return path.join(workspacePath || '', 'VoiceCommander', 'portable_commander.py');
}

function insertTextAtCursor(text: string) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;
    
    const position = editor.selection.active;
    editor.edit(editBuilder => {
        editBuilder.insert(position, text);
    });
}

export function deactivate() {} 