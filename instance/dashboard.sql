CREATE TABLE IF NOT EXISTS multi_ingest (
    username text PRIMARY KEY,
    password text NOT NULL,
    email_id text(254) NOT NULL,
    registered_on integer NOT NULL
);
