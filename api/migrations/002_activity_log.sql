CREATE TABLE IF NOT EXISTS ActivityLog (
    id TEXT PRIMARY KEY NOT NULL,
    userId TEXT NOT NULL,
    projectId TEXT,
    action TEXT NOT NULL,
    robotId TEXT,
    status TEXT NOT NULL DEFAULT 'started',
    details TEXT,
    createdAt INTEGER NOT NULL
);
