import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";

import { getFileContent } from "../../features/files/filesApi";
import { useWorkspace } from "../../context/WorkspaceContext";
import MonacoEditor from "@monaco-editor/react";

const editorOptions = {
  theme: "vs-dark",
  language: "text",
  lineNumbers: "on",
  readOnly: true,
  wordWrap: "off",
  minimap: { enabled: true },
  fontSize: 14,
  fontFamily:
    "'JetBrains Mono', ui-monospace, SFMono-Regular, 'Cascadia Code', monospace",
  lineHeight: 22,
  padding: { top: 8, bottom: 8, left: 24, right: 24 },
  scrollBeyondLastLine: false,
  automaticLayout: true,
  renderLineHighlight: "line",
  glyphMargin: true,
  folding: true,
  quickSuggestions: false,
  suggestOnTriggerCharacters: false,
  acceptSuggestionOnCommitCharacter: false,
  acceptSuggestionOnEnter: "off",
};

export function CodeViewer({ repositoryId }) {
  const { activeCitation, selectedFile } = useWorkspace();
  const editorRef = useRef(null);
  const decorationIds = useRef([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [content, setContent] = useState("");
  const [language, setLanguage] = useState("text");
  const [modelName, setModelName] = useState("");

  const filePath = selectedFile?.path;

  const controllerRef = useRef(null);

  useEffect(() => {
    if (!filePath) {
      setContent("");
      setLanguage("text");
      setModelName("");
      setError(null);
      setLoading(false);
      return;
    }

    loadFile(filePath);
  }, [filePath, repositoryId]);

  async function loadFile(file) {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError(null);
    try {
      const data = await getFileContent(repositoryId, file, controller.signal);
      setContent(data.content || "");
      setLanguage(data.language || "text");
      setModelName(data.language || "text");
    } catch (err) {
      if (err?.cancelled) return;
      setError(err.message || "Could not load file content.");
      setContent("");
    } finally {
      setLoading(false);
    }
  }

  // Highlight the active citation range using Monaco decorations.
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;

    // Clear previous decorations.
    decorationIds.current = editor.deltaDecorations(decorationIds.current, []);

    if (!activeCitation) return;

    const model = editor.getModel();
    if (!model) return;

    const { start_line: startLine, end_line: endLine } = activeCitation;
    const endColumn = model.getLineLength(endLine) + 1;

    decorationIds.current = editor.deltaDecorations([], [
      {
        range: {
          startLineNumber: startLine,
          startColumn: 1,
          endLineNumber: endLine,
          endColumn,
        },
        options: {
          inlineClassName: "citation-highlight",
          isWholeLine: false,
        },
      },
    ]);

    editor.revealLineInCenter(startLine);
  }, [activeCitation, editorRef.current]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-[12px] text-muted">
        <Loader2 size={16} className="animate-spin mr-2" aria-hidden="true" />
        Loading file…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-[12px] text-danger">
        {error}
      </div>
    );
  }

  if (!filePath) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-[12px] text-muted/80">
        Select a file from the explorer or click a citation to view source code.
      </div>
    );
  }

  const fileName = filePath.split("/").pop() || filePath;

  return (
    <div className="h-full flex flex-col min-w-0">
      {/* Editor toolbar (fixed at top, content scrolls beneath) */}
      <div className="border-b border-line flex items-center justify-between bg-white px-4 py-2 z-10 shrink-0 flex-shrink-0">
        <div className="flex items-center gap-2 px-2 py-0.5 rounded-control border border-line bg-background text-[11px] text-muted font-mono">
          {fileName}
        </div>
        <div className="flex items-center gap-1">
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-control border border-line bg-white text-[11px] text-muted font-mono">
            {language}
          </span>
          <span className="text-[10px] text-muted/60 font-mono">
            {modelName}
          </span>
        </div>
      </div>

      <div className="flex-1 min-h-0 relative">
        <MonacoEditor
          height="100%"
          width="100%"
          language={language}
          value={content}
          theme="vs-dark"
          options={editorOptions}
          onMount={(editor) => {
            editorRef.current = editor;
          }}
        />
      </div>
    </div>
  );
}
