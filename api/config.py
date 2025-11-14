"""
Configuration centralisée pour RobianAPI
Support multi-plateforme (Linux, macOS, Windows)
"""

import os
import platform
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class DatabaseSettings(BaseSettings):
    """Configuration base de données PostgreSQL"""

    # PostgreSQL settings
    postgres_server: str = Field("localhost", env="POSTGRES_SERVER")
    postgres_port: int = Field(5432, env="POSTGRES_PORT")
    postgres_user: str = Field("robian", env="POSTGRES_USER")
    postgres_password: str = Field("robian_secret", env="POSTGRES_PASSWORD")
    postgres_db: str = Field("robian_db", env="POSTGRES_DB")

    # Database URL
    database_url: Optional[str] = Field(None, env="DATABASE_URL")

    # Pool settings
    db_pool_size: int = Field(10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(20, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(30, env="DB_POOL_TIMEOUT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @validator("database_url", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        
        return (
            f"postgresql+asyncpg://"
            f"{values.get('postgres_user')}:"
            f"{values.get('postgres_password')}@"
            f"{values.get('postgres_server')}:"
            f"{values.get('postgres_port')}/"
            f"{values.get('postgres_db')}"
        )


class RedisSettings(BaseSettings):
    """Configuration Redis pour le cache"""

    redis_host: str = Field("localhost", env="REDIS_HOST")
    redis_port: int = Field(6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    redis_db: int = Field(0, env="REDIS_DB")
    redis_url: Optional[str] = Field(None, env="REDIS_URL")

    # Cache settings
    cache_ttl_default: int = Field(300, env="CACHE_TTL_DEFAULT")
    cache_ttl_debates: int = Field(300, env="CACHE_TTL_DEBATES")
    cache_ttl_streaming: int = Field(3600, env="CACHE_TTL_STREAMING")
    cache_ttl_metadata: int = Field(86400, env="CACHE_TTL_METADATA")

    class Config:
        extra = "ignore"
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator(
        "cache_ttl_default",
        "cache_ttl_debates",
        "cache_ttl_streaming",
        "cache_ttl_metadata",
        pre=True
    )
    def clean_ttl_values(cls, v):
        if isinstance(v, str):
            # Supprimer les commentaires et espaces
            v = v.split('#')[0].strip()
            try:
                return int(v)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid TTL value: {v}") from e
        return v
    
    @validator("redis_url", pre=True)
    def assemble_redis_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        
        auth_part = ""
        if values.get("redis_password"):
            auth_part = f":{values.get('redis_password')}@"
        
        return (
            f"redis://{auth_part}"
            f"{values.get('redis_host')}:"
            f"{values.get('redis_port')}/"
            f"{values.get('redis_db')}"
        )

class SecuritySettings(BaseSettings):
    """Configuration sécurité"""

    # JWT settings
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # CORS settings
    backend_cors_origins: str = Field(
        "http://localhost:3000,http://localhost:8080",
        env="BACKEND_CORS_ORIGINS"
    )

    # Rate limiting
    rate_limit_per_minute: int = Field(100, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_burst: int = Field(200, env="RATE_LIMIT_BURST")

    class Config:
        extra = "ignore"
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origins_list(self) -> List[str]:
        """Retourne la liste des origines CORS"""
        if not self.backend_cors_origins:
            return []
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


class PathSettings(BaseSettings):
    """Configuration des chemins - Compatible Linux/macOS/Windows"""

    # Base paths (auto-détection OS)
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent)

    # Data directories
    data_dir: Optional[Path] = Field(None, env="DATA_DIR")
    cache_dir: Optional[Path] = Field(None, env="CACHE_DIR")
    audio_dir: Optional[Path] = Field(None, env="AUDIO_DIR")
    logs_dir: Optional[Path] = Field(None, env="LOGS_DIR")
    downloads_dir: Optional[Path] = Field(None, env="DOWNLOADS_DIR")

    # Temp directory (OS-specific)
    temp_dir: Optional[Path] = Field(None, env="TEMP_DIR")

    class Config:
        extra = "ignore"
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup_platform_paths()
    
    def _setup_platform_paths(self):
        """Configuration automatique des chemins selon l'OS"""
        system = platform.system().lower()
        
        # Répertoire de base des données
        if self.data_dir is None:
            if system == "linux":
                # Linux: /var/lib/robian-api ou ~/.local/share/robian-api
                if os.getuid() == 0:  # root
                    self.data_dir = Path("/var/lib/robian-api")
                else:
                    self.data_dir = Path.home() / ".local/share/robian-api"
            elif system == "darwin":  # macOS
                self.data_dir = Path.home() / "Library/Application Support/robian-api"
            else:  # Windows fallback
                self.data_dir = self.base_dir / "data"
        
        # Répertoire temporaire
        if self.temp_dir is None:
            if system in ["linux", "darwin"]:
                self.temp_dir = Path("/tmp/robian-api")
            else:
                self.temp_dir = self.base_dir / "temp"
        
        # Sous-répertoires
        if self.cache_dir is None:
            self.cache_dir = self.data_dir / "cache"
        if self.audio_dir is None:
            self.audio_dir = self.data_dir / "audio"
        if self.logs_dir is None:
            if system == "linux":
                self.logs_dir = Path("/var/log/robian-api") if os.getuid() == 0 else self.data_dir / "logs"
            else:
                self.logs_dir = self.data_dir / "logs"
        if self.downloads_dir is None:
            self.downloads_dir = self.temp_dir / "downloads"
        
        # Créer les répertoires s'ils n'existent pas
        for path in [self.data_dir, self.cache_dir, self.audio_dir, self.logs_dir, self.downloads_dir, self.temp_dir]:
            path.mkdir(parents=True, exist_ok=True)


class AudioSettings(BaseSettings):
    """Configuration extraction et processing audio"""

    # yt-dlp settings
    ytdlp_format: str = Field("bestaudio/best", env="YTDLP_FORMAT")
    ytdlp_extract_flat: bool = Field(False, env="YTDLP_EXTRACT_FLAT")
    ytdlp_no_playlist: bool = Field(True, env="YTDLP_NO_PLAYLIST")

    # FFmpeg settings
    ffmpeg_binary: Optional[str] = Field(None, env="FFMPEG_BINARY")
    audio_format: str = Field("mp3", env="AUDIO_FORMAT")
    audio_quality: str = Field("192k", env="AUDIO_QUALITY")
    audio_codec: str = Field("libmp3lame", env="AUDIO_CODEC")

    # Processing limits
    max_concurrent_extractions: int = Field(3, env="MAX_CONCURRENT_EXTRACTIONS")
    extraction_timeout: int = Field(1800, env="EXTRACTION_TIMEOUT")  # 30 minutes
    max_file_size_mb: int = Field(500, env="MAX_FILE_SIZE_MB")

    class Config:
        extra = "ignore"
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._detect_ffmpeg()
    
    def _detect_ffmpeg(self):
        """Auto-détection de FFmpeg selon l'OS"""
        if self.ffmpeg_binary is None:
            # Tentative de détection automatique
            import shutil
            ffmpeg_path = shutil.which("ffmpeg")
            if ffmpeg_path:
                self.ffmpeg_binary = ffmpeg_path
            else:
                # Chemins par défaut selon l'OS
                system = platform.system().lower()
                if system == "linux":
                    candidates = ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]
                elif system == "darwin":
                    candidates = ["/usr/local/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg"]
                else:
                    candidates = ["ffmpeg.exe"]
                
                for candidate in candidates:
                    if Path(candidate).exists():
                        self.ffmpeg_binary = candidate
                        break


class MonitoringSettings(BaseSettings):
    """Configuration monitoring et logging"""

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")  # json or text
    log_rotation: bool = Field(True, env="LOG_ROTATION")
    log_max_size: str = Field("10MB", env="LOG_MAX_SIZE")
    log_backup_count: int = Field(5, env="LOG_BACKUP_COUNT")

    # Metrics
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    metrics_port: int = Field(9090, env="METRICS_PORT")

    # Health checks
    health_check_interval: int = Field(30, env="HEALTH_CHECK_INTERVAL")

    # Performance monitoring
    enable_profiling: bool = Field(False, env="ENABLE_PROFILING")

    class Config:
        extra = "ignore"
        env_file = ".env"
        env_file_encoding = "utf-8"


class AppSettings(BaseSettings):
    """Configuration principale de l'application"""

    # App info
    app_name: str = "RobianAPI"
    app_version: str = "1.0.0"
    app_description: str = "API Backend pour l'application RobianAPP"

    # Server settings
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    debug: bool = Field(False, env="DEBUG")
    reload: bool = Field(False, env="RELOAD")

    # Environment
    environment: str = Field("development", env="ENVIRONMENT")

    # Workers (pour production)
    workers: int = Field(1, env="WORKERS")

    # API settings
    api_prefix: str = Field("/api", env="API_PREFIX")
    docs_url: str = Field("/docs", env="DOCS_URL")
    redoc_url: str = Field("/redoc", env="REDOC_URL")
    openapi_url: str = Field("/openapi.json", env="OPENAPI_URL")

    class Config:
        extra = "ignore"
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("workers", pre=True)
    def set_workers_count(cls, v):
        if isinstance(v, str) and v.lower() == "auto":
            import multiprocessing
            return multiprocessing.cpu_count()
        return int(v)


class Settings(BaseSettings):
    """Configuration complète de l'application"""
    
    # Sous-configurations
    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    
    class Config:
        extra = "ignore"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instance globale des settings
settings = Settings()


# Helper functions
def get_platform_info() -> dict:
    """Informations sur la plateforme actuelle"""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }


def is_linux() -> bool:
    """Vérifie si on est sur Linux"""
    return platform.system().lower() == "linux"


def is_macos() -> bool:
    """Vérifie si on est sur macOS"""
    return platform.system().lower() == "darwin"


def is_windows() -> bool:
    """Vérifie si on est sur Windows"""
    return platform.system().lower() == "windows"
