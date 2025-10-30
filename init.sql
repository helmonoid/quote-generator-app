-- Initialize quotes database schema
CREATE TABLE IF NOT EXISTS quotes (
    id SERIAL PRIMARY KEY,
    quote TEXT NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    theme VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster queries by date
CREATE INDEX IF NOT EXISTS idx_generated_at ON quotes(generated_at DESC);
