const vscode = require('vscode');
const { spawn } = require('child_process');
const path = require('path');

let recording = false;
let pythonProcess = null;

function activate(context) {
    
    let startRecording = vscode.commands.registerCommand('voice-commander.startRecording', () => {
        if (recording) return;
        
        recording = true;
        vscode.window.showInformationMessage('Voice recording started (F9 to stop)');
        
        // Start Python recorder
        const pythonPath = 'python3';
        const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        const recorderPath = path.join(workspacePath || '', 'VoiceCommander', 'portable_commander.py');
        
        pythonProcess = spawn(pythonPath, [recorderPath]);
        
        pythonProcess.stdout.on('data', (data) => {
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

function insertTextAtCursor(text) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;
    
    const position = editor.selection.active;
    editor.edit(editBuilder => {
        editBuilder.insert(position, text);
    });
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
}; 