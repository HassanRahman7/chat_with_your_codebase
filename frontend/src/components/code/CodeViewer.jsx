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
  wordWrap: "bounded",
  minimap: { enabled: false },
  fontSize: 13,
  fontFamily:
    "'JetBrains Mono', ui-monospace, SFMono-Regular, 'Cascadia Code', monospace",
  lineHeight: 1.6,
  padding: { top: 16, bottom: 16, left: 24, right: 24 },
  scrollBeyondLastLine: false,
  automaticLayout: true,
};

export function CodeViewer({ repositoryId, filePath, commitSha }) {
  const { selectCitation, activeCitation } = useWorkspace();
  const editorRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [content, setContent] = useState("");
  const [language, setLanguage] = useState("text");

  const controllerRef = useRef(null);

  useEffect(() => {
    if (!filePath) {
      setContent("");
      setLanguage("text");
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
    } catch (err) {
      if (err?.cancelled) return;
      setError(err.message || "Could not load file content.");
      setContent("");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (activeCitation && editorRef.current) {
      const { start_line: startLine, end_line: endLine } = activeCitation;
      const range = {
        startLineNumber: startLine,
        startColumn: 1,
        endLineNumber: endLine,
        endColumn: Math.max(1, endLine - startLine + 1),
      };
      editorRef.current.setSelection(range);
      editorRef.current.revealRangeInCenter(range, 0.5);
    }
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

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-line flex items-center justify-between bg-background/90 backdrop-blur px-4 py-2 z-10 shrink-0">
        <span className="font-mono text-[11px] text-muted/80 truncate max-w-[60%] block">
          {filePath}
        </span>
        <span className="flex items-center gap-1 px-2 py-0.5 rounded-control border border-line bg-white text-[11px] text-muted">
          {language}
        </span>
      </div>

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
  );
}
