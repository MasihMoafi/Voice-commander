"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;
const vscode = require("vscode");
const child_process_1 = require("child_process");
const path = require("path");
let recording = false;
let pythonProcess = null;
function activate(context) {
    let startRecording = vscode.commands.registerCommand('voice-commander.startRecording', () => {
        if (recording)
            return;
        recording = true;
        vscode.window.showInformationMessage('Voice recording started (F9 to stop)');
        // Start Python recorder
        const pythonPath = getPythonPath();
        pythonProcess = (0, child_process_1.spawn)(pythonPath, [getRecorderPath()]);
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
        if (!recording)
            return;
        recording = false;
        vscode.window.showInformationMessage('Voice recording stopped');
        if (pythonProcess) {
            pythonProcess.kill();
            pythonProcess = null;
        }
    });
    context.subscriptions.push(startRecording, stopRecording);
}
exports.activate = activate;
function getPythonPath() {
    return 'python3';
}
function getRecorderPath() {
    const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    return path.join(workspacePath || '', 'VoiceCommander', 'portable_commander.py');
}
function insertTextAtCursor(text) {
    const editor = vscode.window.activeTextEditor;
    if (!editor)
        return;
    const position = editor.selection.active;
    editor.edit(editBuilder => {
        editBuilder.insert(position, text);
    });
}
function deactivate() { }
exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map