-- =============================================================================
-- Script d'initialisation PostgreSQL pour RobianAPI
-- Création de la base de données et configuration initiale
-- =============================================================================

-- Extensions PostgreSQL utiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Pour la recherche textuelle
CREATE EXTENSION IF NOT EXISTS "unaccent"; -- Pour ignorer les accents

-- Configuration de performance
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;
ALTER SYSTEM SET log_min_duration_statement = 1000; -- Log queries > 1s

-- Configuration mémoire (ajuster selon la RAM disponible)
-- Ces valeurs sont pour un serveur avec 2GB RAM minimum
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Configuration connexions
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET max_worker_processes = 8;
ALTER SYSTEM SET max_parallel_workers_per_gather = 2;
ALTER SYSTEM SET max_parallel_workers = 8;

-- Configuration logging pour debugging
ALTER SYSTEM SET log_destination = 'stderr';
ALTER SYSTEM SET logging_collector = on;
ALTER SYSTEM SET log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log';
ALTER SYSTEM SET log_rotation_age = '1d';
ALTER SYSTEM SET log_rotation_size = '10MB';
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';
ALTER SYSTEM SET log_checkpoints = on;
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_lock_waits = on;

-- Recharger la configuration
SELECT pg_reload_conf();

-- Informations de version et configuration
SELECT version();
SHOW shared_buffers;
SHOW effective_cache_size;
SHOW max_connections;

-- Messages d'information
DO $$ 
BEGIN 
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'PostgreSQL initialisé pour RobianAPI';
    RAISE NOTICE 'Base de données: %', current_database();
    RAISE NOTICE 'Utilisateur: %', current_user;
    RAISE NOTICE 'Version PostgreSQL: %', version();
    RAISE NOTICE '=============================================================================';
END $$;
