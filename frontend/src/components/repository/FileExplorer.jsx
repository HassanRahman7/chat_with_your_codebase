import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight, File, Folder } from "lucide-react";

import { getRepositoryFiles } from "../../features/files/filesApi";
import { useWorkspace } from "../../context/WorkspaceContext";

export function FileExplorer({ repositoryId, className }) {
  const { selectFile, selectedFile, clearSelection } = useWorkspace();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState({});
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
    return expanded[path] !== false; // Default expanded
  }

  function renderTree(treeItems, depth = 0) {
    return treeItems.map((item) => {
      if (item.type === "directory") {
        const isExpanded = isDirectoryExpanded(item.path);
        const children = isExpanded ? item.children || [] : [];
        const isSelected =
          selectedFile?.path === item.path ||
          (selectedFile?.path && selectedFile.path.startsWith(`${item.path}/`));

        return (
          <div
            key={item.path}
            className="flex flex-col gap-1"
          >
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
          <File size={12} className="text-muted" />
          <span className="text-[12px] text-ink truncate">
            {item.name}
          </span>
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
    return (
      <div className="p-4 text-[12px] text-danger">
        {error}
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <div className="p-4 text-[12px] text-muted/80">
        No files available.
      </div>
    );
  }

  return (
    <div
      className={"h-full flex flex-col min-h-[200px] " + (className ?? "")}
    >
      <div className="border-b border-line px-4 py-3">
        <div className="flex items-center gap-1.5">
          <Folder size={14} className="text-accent" />
          <span className="text-[12px] font-semibold text-ink">Files</span>
        </div>
      </div>
      <div className="overflow-y-auto p-2">
        {renderTree(items)}
      </div>
    </div>
  );
}
