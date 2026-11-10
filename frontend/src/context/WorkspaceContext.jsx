import { createContext, useContext, useState, useCallback } from "react";

const WorkspaceContext = createContext(null);

export function WorkspaceProvider({ children }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [activeCitation, setActiveCitation] = useState(null);
  const [activeConversationId, setActiveConversationId] = useState(null);

  const selectFile = useCallback((filePath, commitSha) => {
    setSelectedFile({ path: filePath, commitSha });
    setActiveCitation(null);
  }, []);

  const selectCitation = useCallback(
    (citation) => {
      setActiveCitation(citation);
      setSelectedFile({
        path: citation.file_path,
        commitSha: citation.commit_sha,
      });
    },
    []
  );

  const clearSelection = useCallback(() => {
    setSelectedFile(null);
    setActiveCitation(null);
  }, []);

  const value = {
    selectedFile,
    selectFile,
    activeCitation,
    selectCitation,
    clearSelection,
    activeConversationId,
    setActiveConversationId,
  };

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace must be used within a WorkspaceProvider");
  }
  return context;
}
