import { useEffect, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  File,
  Folder,
  FileCode,
  FileText,
  FileImage,
  FileJson,
  FileLock,
  FileTerminal,
  FileType,
  FileVideo,
  ChevronLeft,
} from "lucide-react";

import { getRepositoryFiles } from "../../features/files/filesApi";
import { useWorkspace } from "../../context/WorkspaceContext";

const ICON_MAP = {
  ".py": FileCode,
  ".js": FileCode,
  ".jsx": FileCode,
  ".ts": FileCode,
  ".tsx": FileCode,
  ".json": FileJson,
  ".md": FileText,
  ".txt": FileText,
  ".html": FileCode,
  ".css": FileCode,
  ".scss": FileCode,
  ".yaml": FileText,
  ".yml": FileText,
  ".toml": FileText,
  ".cfg": FileText,
  ".ini": FileText,
  ".lock": FileLock,
  ".sh": FileTerminal,
  ".sql": FileText,
  ".dockerfile": FileType,
  ".env": FileLock,
  ".gitignore": FileLock,
  ".png": FileImage,
  ".jpg": FileImage,
  ".jpeg": FileImage,
  ".gif": FileImage,
  ".svg": FileImage,
  ".mp4": FileVideo,
  ".mov": FileVideo,
};

function getIconForFile(fileName) {
  const ext = fileName.slice(fileName.lastIndexOf(".")).toLowerCase();
  return ICON_MAP[ext] || File;
}

export function FileExplorer({ repositoryId, className }) {
  const { selectFile, selectedFile } = useWorkspace();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState({});
  const [collapsed, setCollapsed] = useState(false);
  const controllerRef = useRef(null);

  useEffect(() => {
    loadFiles();
    return () => controllerRef.current?.abort();
  }, [repositoryId]);

  async function loadFiles() {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError(null);
    try {
      const data = await getRepositoryFiles(repositoryId, controller.signal);
      setItems(data.items || []);
    } catch (err) {
      if (err?.cancelled) return;
      setError(err.message || "Could not load file tree.");
    } finally {
      setLoading(false);
    }
  }

  function toggleDirectory(path) {
    setExpanded((prev) => ({ ...prev, [path]: !prev[path] }));
  }

  function isDirectoryExpanded(path) {
    return expanded[path] !== false;
  }

  function renderTree(treeItems, depth = 0) {
    return treeItems.map((item) => {
      if (item.type === "directory") {
        const isExpanded = isDirectoryExpanded(item.path);
        const children = isExpanded ? item.children || [] : [];

        return (
          <div key={item.path} className="flex flex-col gap-1">
            <div
              className="flex items-center gap-1.5 rounded-[2px] px-2 py-0.5 cursor-pointer select-none hover:bg-black/[0.04] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              role="button"
              aria-expanded={isExpanded}
              onClick={() => toggleDirectory(item.path)}
              onKeyDown={(e) => {
                if (e.key === "Enter") toggleDirectory(item.path);
              }}
              tabIndex={0}
            >
              {isExpanded ? (
                <ChevronDown size={12} className="text-muted/60" />
              ) : (
                <ChevronRight size={12} className="text-muted/60" />
              )}
              <Folder size={13} className="text-muted" />
              <span className="text-[12px] font-medium text-ink truncate">
                {item.name}
              </span>
            </div>
            {children.length > 0 && (
              <div className="ml-3">
                {renderTree(children, depth + 1)}
              </div>
            )}
          </div>
        );
      }

      const Icon = getIconForFile(item.path);
      const isSelected = selectedFile?.path === item.path;
      return (
        <div
          key={item.path}
          className={
            "flex items-center gap-1.5 rounded-[2px] px-2 py-0.5 cursor-pointer select-none hover:bg-black/[0.04] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent transition-colors" +
            (isSelected
              ? " bg-accent/10 border border-accent/30"
              : "")
          }
          role="button"
          aria-selected={isSelected}
          onClick={() => selectFile(item.path, null)}
          onKeyDown={(e) => {
            if (e.key === "Enter") selectFile(item.path, null);
          }}
          tabIndex={0}
        >
          <Icon size={12} className="text-muted" />
          <span className="text-[12px] text-ink truncate">{item.name}</span>
        </div>
      );
    });
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-[12px] text-muted">
        Loading files…
      </div>
    );
  }

  if (error) {
    return <div className="p-4 text-[12px] text-danger">{error}</div>;
  }

  if (!items || items.length === 0) {
    return (
      <div className="p-4 text-[12px] text-muted/80">No files available.</div>
    );
  }

  return (
    <div
      className={
        "h-full flex flex-col min-h-[200px] shrink-0 border-r border-line bg-white " +
        (className ?? "")
      }
    >
      <div className="flex items-center justify-between border-b border-line px-4 py-3 shrink-0">
        <div className="flex items-center gap-1.5">
          <Folder size={14} className="text-accent" />
          <span className="text-[12px] font-semibold text-ink">Files</span>
        </div>
        <button
          onClick={() => setCollapsed((prev) => !prev)}
          className="p-1.5 rounded-control text-muted hover:bg-black/[0.04] hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label={
            collapsed ? "Expand explorer" : "Collapse explorer"
          }
        >
          {collapsed ? (
            <ChevronRight size={14} className="text-muted" />
          ) : (
            <ChevronLeft size={14} className="text-muted" />
          )}
        </button>
      </div>
      <div className={"overflow-y-auto p-2 " + (collapsed ? "hidden" : "")}>
        {renderTree(items)}
      </div>
    </div>
  );
}
