export const PUBLIC_STATUS_LABELS = {
  queued: "Queued",
  cloning: "Cloning repository",
  scanning: "Scanning files",
  parsing: "Understanding code structure",
  embedding: "Generating embeddings",
  storing: "Building search index",
  ready: "Ready",
  failed: "Indexing failed",
  deleting: "Deleting repository",
};

export const STEP_LABELS = {
  validating_repository: "Validating repository",
  cloning_repository: "Cloning repository",
  discovering_files: "Scanning files",
  parsing_files: "Parsing source files",
  creating_chunks: "Creating code chunks",
  generating_embeddings: "Generating embeddings",
  storing_vectors: "Storing vectors",
  verifying_index: "Verifying index",
  activating_index: "Activating index",
  completed: "Complete",
};

export const ACTIVE_STATUSES = new Set([
  "queued",
  "cloning",
  "scanning",
  "parsing",
  "embedding",
  "storing",
  "deleting",
]);

const TONE_BY_STATUS = {
  queued: "neutral",
  cloning: "info",
  scanning: "info",
  parsing: "info",
  embedding: "info",
  storing: "info",
  ready: "success",
  failed: "danger",
  deleting: "warning",
};

export function isActiveStatus(status) {
  return ACTIVE_STATUSES.has(status);
}

export function isPipelinePending(errorCode) {
  return errorCode === "indexing_pipeline_pending";
}

export function statusTone(status, errorCode) {
  if (isPipelinePending(errorCode)) return "warning";
  return TONE_BY_STATUS[status] ?? "neutral";
}

export function statusLabel(status, errorCode) {
  if (isPipelinePending(errorCode)) return "Cloned — indexing pending";
  return PUBLIC_STATUS_LABELS[status] ?? status;
}

export function stepLabel(step, status) {
  if (step && STEP_LABELS[step]) return STEP_LABELS[step];
  return PUBLIC_STATUS_LABELS[status] ?? "Indexing";
}
